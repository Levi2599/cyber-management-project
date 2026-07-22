"""
run_eval.py — הערכה כמותית אמיתית של מבקר הקוד הכפול.

מריץ את כל מקרי הבדיקה המתויגים שב-dataset.json דרך ה-webhook החי של n8n,
משווה את תשובת המערכת לתווית האמת, ומחשב את המדדים.

המדדים שנמדדים בפועל:
  * קצב זיהוי (Recall)     — כמה מהקבצים הפגיעים סומנו כפגיעים.
  * התראות שווא (FPR)      — כמה מהקבצים הבטוחים סומנו בטעות כפגיעים.
  * דיוק (Precision)       — מתוך מה שסומן כפגיע, כמה באמת היה פגיע.
  * זמן ריצה ממוצע.
  * שיעור הפקת וקטור CVSS תקין.

הפלט נכתב ל-results.json, ו-generate_report.py קורא אותו. אם הקובץ לא קיים,
הדוח מציין במפורש שההערכה טרם הורצה — ולא ממציא מספרים.

הרצה:
    python scripts/eval/run_eval.py --base-url http://35.193.190.149:5678
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(HERE, "dataset.json")
RESULTS_PATH = os.path.join(HERE, "results.json")
WORKFLOW_PATH = os.path.join(HERE, "..", "..", "dual_code_auditor_wf_updated.json")


def primary_model() -> str:
    """
    קורא את שם המודל מתוך ה-workflow עצמו.

    הערך הזה נכתב ל-results.json ומשם לדוח. אילו היה מוקלד ידנית, שינוי מודל
    בוורקפלו היה משאיר בדוח שם מודל שגוי — כלומר דיווח על מדידה שלא נעשתה.
    """
    try:
        with open(WORKFLOW_PATH, encoding="utf-8") as f:
            wf = json.load(f)
        for node in wf["nodes"]:
            if node.get("type", "").endswith("lmChatGroq") and "Fallback" not in node["name"]:
                return "Groq " + node["parameters"]["model"]
    except (OSError, KeyError, ValueError):
        pass
    return "unknown"

CVSS_RE = re.compile(r"CVSS:3\.1/(?:[A-Z]{1,2}:[A-Z]/?)+")
NO_VULN_RE = re.compile(r"NO_VULNERABILITIES_FOUND", re.IGNORECASE)


class ScanFailed(Exception):
    """הבקשה לא החזירה דוח שמיש. חייבת להיספר ככשל — לעולם לא כתוצאה."""


def call_chat(base_url: str, code: str, timeout: int):
    """
    שולח קטע קוד ל-endpoint הסריקה ומחזיר (dict התשובה, משך בשניות).

    תשובה ריקה או שאינה JSON פירושה שהזרימה נפלה — לרוב מפני שספק המודל
    החזיר שגיאת מכסה. במקרה כזה נזרקת ScanFailed. זה קריטי: גרסה קודמת של
    הקובץ סיווגה תשובה ריקה כ"לא נמצאה חולשה", וכך הפכה כשלי תשתית
    ל"מדידה" שנראית תקינה. כשל חייב להיראות ככשל.
    """
    url = base_url.rstrip("/") + "/webhook/scan-code"
    payload = json.dumps({"code": code}).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read().decode("utf-8", errors="replace")
    elapsed = time.time() - started

    if not raw.strip():
        raise ScanFailed("empty response body (the workflow stopped before responding)")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ScanFailed("response was not JSON: %s" % raw[:120])
    if not data.get("report_markdown"):
        raise ScanFailed("response contained no report_markdown")
    return data, elapsed


def classify(data: dict) -> bool:
    """
    True = המערכת טוענת שיש חולשה.

    מסתמך על השדות המובנים שהמערכת עצמה חישבה בצומת Build Report, ולא על
    ניחוש מילות מפתח בטקסט חופשי של מודל שפה.
    """
    if data.get("no_vulnerabilities_found") is True:
        return False
    if data.get("cvss_vector_string"):
        return True
    text = data.get("report_markdown", "")
    if NO_VULN_RE.search(text):
        return False
    return bool(re.search(r"vulnerab|חולשה|פגיעות|injection|CWE-", text, re.IGNORECASE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("N8N_BASE_URL", "http://35.193.190.149:5678"))
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--limit", type=int, default=0, help="הרץ רק N מקרים ראשונים (לבדיקה מהירה)")
    ap.add_argument("--delay", type=float, default=12.0,
                    help="השהיה בשניות בין מקרים, כדי לא לשחוק את מכסת ספק המודל")
    ap.add_argument("--retries", type=int, default=3, help="ניסיונות חוזרים לכל מקרה")
    args = ap.parse_args()

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    cases = dataset["cases"]
    if args.limit:
        cases = cases[: args.limit]

    records = []
    errors = 0

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']} ({case['label']}) ...", end=" ", flush=True)

        data = elapsed = None
        last_err = None
        # ספק המודל מגביל בקשות לדקה. ריצה רצופה שוחקת את המכסה, ולכן כל
        # ניסיון כושל מקבל המתנה גדלה לפני ניסיון חוזר.
        for attempt in range(args.retries + 1):
            try:
                data, elapsed = call_chat(args.base_url, case["code"], args.timeout)
                break
            except (ScanFailed, urllib.error.URLError, TimeoutError, OSError) as exc:
                last_err = exc
                data = None
                if attempt < args.retries:
                    backoff = args.delay * (2 ** attempt)
                    print(f"retry in {backoff:.0f}s...", end=" ", flush=True)
                    time.sleep(backoff)

        if data is None:
            print(f"FAILED: {last_err}")
            errors += 1
            records.append({
                "id": case["id"], "label": case["label"], "error": str(last_err),
                "predicted_vulnerable": None, "elapsed_sec": None, "cvss_vector": None,
                "response_chars": 0,
            })
            time.sleep(args.delay)
            continue

        predicted = classify(data)
        report = data.get("report_markdown", "")
        records.append({
            "id": case["id"],
            "label": case["label"],
            "vuln_type": case.get("vuln_type"),
            "owasp": case.get("owasp"),
            "predicted_vulnerable": predicted,
            "cvss_vector": data.get("cvss_vector_string") or None,
            "elapsed_sec": round(elapsed, 2),
            "response_chars": len(report),
        })
        print(f"{'VULN' if predicted else 'CLEAN'}  {elapsed:.1f}s")
        time.sleep(args.delay)

    ok = [r for r in records if r.get("predicted_vulnerable") is not None]
    vuln_cases = [r for r in ok if r["label"] == "vulnerable"]
    safe_cases = [r for r in ok if r["label"] == "safe"]

    tp = sum(1 for r in vuln_cases if r["predicted_vulnerable"])
    fn = len(vuln_cases) - tp
    fp = sum(1 for r in safe_cases if r["predicted_vulnerable"])
    tn = len(safe_cases) - fp

    def pct(num, den):
        return round(100.0 * num / den, 1) if den else None

    times = [r["elapsed_sec"] for r in ok if r["elapsed_sec"] is not None]
    with_cvss = [r for r in vuln_cases if r["cvss_vector"]]

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": args.base_url,
        "model": primary_model(),
        "architecture": "Dual Agent (Red Team + Blue Team)",
        "total_cases": len(cases),
        "completed_cases": len(ok),
        "failed_calls": errors,
        "vulnerable_cases": len(vuln_cases),
        "safe_cases": len(safe_cases),
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "true_negatives": tn,
        "detection_rate_pct": pct(tp, len(vuln_cases)),
        "false_positive_rate_pct": pct(fp, len(safe_cases)),
        "precision_pct": pct(tp, tp + fp),
        "cvss_vector_emitted_pct": pct(len(with_cvss), len(vuln_cases)),
        "avg_runtime_sec": round(statistics.mean(times), 1) if times else None,
        "median_runtime_sec": round(statistics.median(times), 1) if times else None,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "records": records}, f, ensure_ascii=False, indent=2)

    # אם חלק ניכר מהמקרים נכשל, האחוזים מחושבים על מדגם חלקי ומוטה ואין
    # לדווח עליהם. מסמנים את התוצאה כפסולה כדי שמחולל הדוח לא יציג אותה.
    summary["valid"] = errors == 0 and len(ok) == len(cases)
    if not summary["valid"]:
        summary["invalid_reason"] = (
            "%d of %d scans failed; rates would be computed on a partial sample"
            % (errors, len(cases))
        )

    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"\nnnnwritten to {RESULTS_PATH}".replace("nnn", ""))

    if errors:
        print(f"\nWARNING: {errors} calls failed. המספרים מבוססים רק על ההרצות שהצליחו.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
