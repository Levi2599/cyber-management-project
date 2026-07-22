"""
make_charts.py — מייצר את התרשימים לדוח מתוך נתונים אמיתיים בלבד.

מקורות הנתונים:
  * scripts/eval/dataset.json  — הרכב מקרי הבדיקה המתויגים (קיים תמיד).
  * scripts/eval/results.json  — תוצאות ההרצה בפועל (קיים רק אחרי run_eval.py).

אם results.json חסר, תרשימי הביצועים פשוט לא נוצרים, והדוח מציין שההערכה
טרם הורצה. אין כאן שום ערך שנוצר ידנית.

תוויות התרשימים באנגלית במכוון: matplotlib אינו מבצע bidi/shaping לעברית,
ותוויות עבריות היו מוצגות הפוכות. ההסברים בעברית מופיעים בגוף הדוח.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_DIR = os.path.join(HERE, "eval")
OUT_DIR = os.path.join(HERE, "figures")

NAVY = "#1A5276"
RED = "#C0392B"
BLUE = "#2E86C1"
GREEN = "#1E8449"
GREY = "#909497"


def _style(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title, fontsize=11, color=NAVY, fontweight="bold", pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)


def chart_dataset_composition(dataset, out_path):
    """התפלגות סוגי החולשות בקורפוס הבדיקה."""
    counts = {}
    for c in dataset["cases"]:
        if c["label"] != "vulnerable":
            continue
        key = c["owasp"].split(" ", 1)[0] if c.get("owasp") else "N/A"
        counts[key] = counts.get(key, 0) + 1

    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(6.2, 3.0), dpi=200)
    bars = ax.barh(labels[::-1], values[::-1], color=BLUE, height=0.6)
    for b, v in zip(bars, values[::-1]):
        ax.text(v + 0.06, b.get_y() + b.get_height() / 2, str(v),
                va="center", fontsize=8, color=NAVY)
    ax.set_xlim(0, max(values) + 1)
    ax.set_xticks(range(0, max(values) + 2))
    _style(ax, "Test corpus: vulnerable cases by OWASP Top 10 category",
           xlabel="Number of test cases")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def chart_label_balance(dataset, out_path):
    """יחס פגיע/בטוח — קיומם של מקרים בטוחים הוא תנאי למדידת התראות שווא."""
    vuln = sum(1 for c in dataset["cases"] if c["label"] == "vulnerable")
    safe = sum(1 for c in dataset["cases"] if c["label"] == "safe")

    fig, ax = plt.subplots(figsize=(3.6, 3.0), dpi=200)
    ax.pie([vuln, safe],
           labels=["Vulnerable\n(%d)" % vuln, "Safe\n(%d)" % safe],
           colors=[RED, GREEN], autopct="%1.0f%%",
           textprops={"fontsize": 8}, startangle=120,
           wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax.set_title("Corpus balance", fontsize=11, color=NAVY, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def chart_confusion(summary, out_path):
    """מטריצת בלבול מתוצאות ההרצה בפועל."""
    fig, ax = plt.subplots(figsize=(5.6, 3.0), dpi=200)
    labels = ["True\nPositives", "False\nNegatives", "False\nPositives", "True\nNegatives"]
    values = [summary["true_positives"], summary["false_negatives"],
              summary["false_positives"], summary["true_negatives"]]
    colors = [GREEN, RED, RED, GREEN]
    bars = ax.bar(labels, values, color=colors, width=0.55)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.08, str(v),
                ha="center", fontsize=9, color=NAVY, fontweight="bold")
    ax.set_ylim(0, max(values) + 1.5)
    _style(ax, "Measured classification outcomes", ylabel="Cases")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def chart_runtime(records, out_path):
    """התפלגות זמני ריצה בפועל."""
    times = [r["elapsed_sec"] for r in records if r.get("elapsed_sec")]
    if len(times) < 3:
        return False

    fig, ax = plt.subplots(figsize=(5.6, 3.0), dpi=200)
    ax.hist(times, bins=min(10, len(times)), color=BLUE, edgecolor="white")
    mean = sum(times) / len(times)
    ax.axvline(mean, color=RED, linestyle="--", linewidth=1.4,
               label="mean = %.1fs" % mean)
    ax.legend(fontsize=8, frameon=False)
    _style(ax, "End-to-end runtime per scan (Red + Blue agent)",
           xlabel="Seconds", ylabel="Scans")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def chart_run_comparison(runs, out_path):
    """שלוש ההרצות זו לצד זו — התפתחות המדדים אחרי כל שינוי בהנחיה."""
    labels = [name for name, _ in runs]
    metrics = [("Detection", "detection_rate_pct", GREEN),
               ("False positives", "false_positive_rate_pct", RED),
               ("Precision", "precision_pct", BLUE)]

    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=200)
    width = 0.26
    xs = range(len(runs))
    for i, (label, key, color) in enumerate(metrics):
        vals = [s[key] for _, s in runs]
        pos = [x + (i - 1) * width for x in xs]
        bars = ax.bar(pos, vals, width=width, color=color, label=label)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.5, "%g" % v,
                    ha="center", fontsize=7, color=NAVY)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 112)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower center",
              bbox_to_anchor=(0.5, -0.30))
    _style(ax, "Effect of each prompt revision on the same corpus",
           ylabel="Percent")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def chart_per_case(records, dataset, out_path):
    """תוצאה לכל מקרה בדיקה — איפה בדיוק המערכת צדקה ואיפה טעתה."""
    by_id = {c["id"]: c for c in dataset["cases"]}
    ids, colors, notes = [], [], []
    for r in records:
        if r.get("predicted_vulnerable") is None:
            continue
        want = by_id[r["id"]]["label"] == "vulnerable"
        got = r["predicted_vulnerable"]
        ids.append(r["id"])
        if want and got:
            colors.append(GREEN); notes.append("")
        elif not want and not got:
            colors.append(BLUE); notes.append("")
        elif not want and got:
            colors.append(RED); notes.append("FP")
        else:
            colors.append("#E67E22"); notes.append("FN")

    fig, ax = plt.subplots(figsize=(6.6, 2.3), dpi=200)
    bars = ax.bar(ids, [1] * len(ids), color=colors, width=0.75)
    for b, n in zip(bars, notes):
        if n:
            ax.text(b.get_x() + b.get_width() / 2, 1.06, n, ha="center",
                    fontsize=7, fontweight="bold", color=NAVY)
    ax.set_ylim(0, 1.3)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=7, rotation=90)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_title("Per-case outcome  (green = vulnerability found, "
                 "blue = correctly clean, red = false positive)",
                 fontsize=9, color=NAVY, fontweight="bold", pad=10)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(EVAL_DIR, "dataset.json"), encoding="utf-8") as f:
        dataset = json.load(f)

    produced = []

    p = os.path.join(OUT_DIR, "fig1_corpus_owasp.png")
    chart_dataset_composition(dataset, p)
    produced.append(p)

    p = os.path.join(OUT_DIR, "fig2_corpus_balance.png")
    chart_label_balance(dataset, p)
    produced.append(p)

    results_path = os.path.join(EVAL_DIR, "results.json")
    if os.path.exists(results_path):
        with open(results_path, encoding="utf-8") as f:
            results = json.load(f)
        if results["summary"]["completed_cases"] > 0:
            p = os.path.join(OUT_DIR, "fig3_confusion.png")
            chart_confusion(results["summary"], p)
            produced.append(p)
            p = os.path.join(OUT_DIR, "fig4_runtime.png")
            if chart_runtime(results["records"], p):
                produced.append(p)

            p = os.path.join(OUT_DIR, "fig6_per_case.png")
            chart_per_case(results["records"], dataset, p)
            produced.append(p)

            # השוואה בין ההרצות, אם נשמרו הרצות קודמות
            runs = []
            for fname, label in (("results_baseline.json", "Run 1"),
                                 ("results_v2.json", "Run 2")):
                fpath = os.path.join(EVAL_DIR, fname)
                if os.path.exists(fpath):
                    with open(fpath, encoding="utf-8") as f:
                        prev = json.load(f)["summary"]
                    if prev.get("valid") is not False:
                        runs.append((label, prev))
            if runs:
                runs.append(("Run %d" % (len(runs) + 1), results["summary"]))
                p = os.path.join(OUT_DIR, "fig5_run_comparison.png")
                chart_run_comparison(runs, p)
                produced.append(p)
    else:
        print("NOTE: results.json not found — performance charts skipped.")
        print("      Run: python scripts/eval/run_eval.py")

    for p in produced:
        print("wrote", os.path.relpath(p, os.path.dirname(HERE)))


if __name__ == "__main__":
    main()
