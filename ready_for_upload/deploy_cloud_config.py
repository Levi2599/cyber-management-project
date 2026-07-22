"""
deploy_cloud_config.py — מעדכן את כתובת שרת ה-n8n בדף התצוגה ודוחף לגיט.

הדף מרכז את כל כתובות השרת בשדה אחד (CONFIG.BASE_URL), ולכן הסקריפט מחליף
שדה יחיד. אם ההחלפה לא מצאה את השדה — הסקריפט נעצר עם שגיאה ואינו דוחף כלום.
כישלון שקט שמסתיים ב-push הוא בדיוק מה שאסור שיקרה כאן.

שימוש:
    python deploy_cloud_config.py https://n8n.example.com
"""

import os
import re
import subprocess
import sys

TARGETS = ["index.html", os.path.join("ready_for_upload", "index.html")]
BASE_URL_RE = re.compile(r'(BASE_URL:\s*")(https?://[^"]+)(")')


def update_file(path: str, base_url: str) -> bool:
    """מחזיר True אם הקובץ עודכן. זורק חריגה אם המבנה לא נמצא."""
    if not os.path.exists(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content, count = BASE_URL_RE.subn(
        lambda m: m.group(1) + base_url + m.group(3), content
    )
    if count == 0:
        raise SystemExit(
            f"ERROR: לא נמצא שדה CONFIG.BASE_URL בקובץ {path}.\n"
            "ייתכן שמבנה הדף השתנה. לא בוצע שום שינוי ולא בוצע push."
        )
    if count > 1:
        raise SystemExit(
            f"ERROR: נמצאו {count} מופעים של BASE_URL בקובץ {path}. "
            "צפוי מופע אחד בלבד. לא בוצע שום שינוי."
        )

    if new_content == content:
        print(f"  {path}: כבר מעודכן, אין שינוי")
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"  {path}: עודכן")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    base_url = sys.argv[1].strip().rstrip("/")
    if not re.match(r"^https?://", base_url):
        raise SystemExit("ERROR: הכתובת חייבת להתחיל ב-http:// או ב-https://")

    if base_url.startswith("http://"):
        print(
            "אזהרה: כתובת HTTP. אם הדף מוגש ב-HTTPS, הדפדפן יחסום את הבקשות "
            "(Mixed Content) והמערכת לא תעבוד מהאתר.\n"
        )

    print(f"מעדכן BASE_URL ל-{base_url}:")
    changed = [p for p in TARGETS if update_file(p, base_url)]

    if not changed:
        print("\nלא היה מה לעדכן. לא בוצע commit.")
        return

    print("\nמבצע commit ו-push...")
    subprocess.run(["git", "add"] + changed, check=True)
    res = subprocess.run(
        ["git", "commit", "-m", f"Point site at n8n endpoint {base_url}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(res.stdout or res.stderr)

    res = subprocess.run(
        ["git", "push", "origin", "master"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(res.stdout or res.stderr)
    if res.returncode != 0:
        raise SystemExit("ERROR: ה-push נכשל. ראו את הפלט למעלה.")

    print("\n--- הושלם ---")
    print(f"שרת n8n: {base_url}")
    print("יש לוודא שהאתר החי אכן התעדכן לפני שמסתמכים על כך.")


if __name__ == "__main__":
    main()
