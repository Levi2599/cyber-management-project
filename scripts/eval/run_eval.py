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

CVSS_RE = re.compile(r"CVSS:3\.1/(?:[A-Z]{1,2}:[A-Z]/?)+")
NO_VULN_RE = re.compile(r"NO_VULNERABILITIES_FOUND", re.IGNORECASE)


def call_chat(base_url: str, code: str, timeout: int):
    """שולח קטע קוד ל-endpoint הסריקה ומחזיר (טקסט הדוח, משך בשניות)."""
    url = base_url.rstrip("/") + "/webhook/scan-code"
    payload = json.dumps({"code": code}).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read().decode("utf-8", errors="replace")
    elapsed = time.time() - started

    try:
        data = json.loads(raw)
        text = data.get("report_markdown") or data.get("output") or raw
    except json.JSONDecodeError:
        text = raw
    return text, elapsed


def classify(text: str) -> bool:
    """True = המערכת טוענת שיש חולשה."""
    if NO_VULN_RE.search(text):
        return False
    # אם דווח וקטור CVSS, זו הצהרה חד-משמעית על חולשה.
    if CVSS_RE.search(text):
        return True
    # אין וקטור ואין הצהרת "נקי" — נחשב כדיווח על חולשה רק אם הוזכרה
    # מפורשות מילת מפתח של ממצא. אחרת נחשיב כלא-מסווג (ראו main).
    return bool(re.search(r"vulnerab|חולשה|פגיעות|injection|CWE-", text, re.IGNORECASE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("N8N_BASE_URL", "http://35.193.190.149:5678"))
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--limit", type=int, default=0, help="הרץ רק N מקרים ראשונים (לבדיקה מהירה)")
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
        try:
            text, elapsed = call_chat(args.base_url, case["code"], args.timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"ERROR: {exc}")
            errors += 1
            records.append({
                "id": case["id"], "label": case["label"], "error": str(exc),
                "predicted_vulnerable": None, "elapsed_sec": None, "cvss_vector": None,
            })
            continue

        predicted = classify(text)
        cvss = CVSS_RE.search(text)
        records.append({
            "id": case["id"],
            "label": case["label"],
            "vuln_type": case.get("vuln_type"),
            "owasp": case.get("owasp"),
            "predicted_vulnerable": predicted,
            "cvss_vector": cvss.group(0) if cvss else None,
            "elapsed_sec": round(elapsed, 2),
            "response_chars": len(text),
        })
        print(f"{'VULN' if predicted else 'CLEAN'}  {elapsed:.1f}s")

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
        "model": "Groq llama-3.3-70b-versatile",
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
