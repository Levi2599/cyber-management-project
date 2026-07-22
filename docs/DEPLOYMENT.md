# מבקר הקוד הכפול — Dual Code Auditor

מערכת מרובת-סוכנים ב-n8n שמזהה חולשות אבטחה בקוד ומייצרת עבורן תיקון.
סוכן Red Team מנתח ומפיק וקטור CVSS 3.1, סוכן Blue Team מחזיר גרסה מאובטחת.

---

## מה יש בתיקייה

| קובץ | תפקיד |
|---|---|
| `index.html` | דף התצוגה. **זה הקובץ שנפרס לאתר.** |
| `dual_code_auditor_wf_updated.json` | ה-workflow המלא לייבוא ל-n8n (23 צמתים) |
| `דוח סיכום עבודת גמר - מבקר הקוד הכפול.docx` / `.md` | דוח הסיכום |
| `PRD - מבקר הקוד הכפול.md` | מסמך אפיון |
| `deploy_cloud_config.py` | עדכון כתובות השרת בדף ופריסה ל-Git |

בתיקיית `scripts/` שבשורש המאגר:

| קובץ | תפקיד |
|---|---|
| `eval/dataset.json` | קורפוס בדיקה מתויג — 20 קטעי קוד (12 פגיעים, 8 בטוחים) |
| `eval/run_eval.py` | מריץ את הקורפוס מול המערכת ומחשב מדדים אמיתיים |
| `eval/test_code_nodes.js` | בדיקות יחידה לצמתי ה-Code של ה-workflow |
| `make_charts.py` | מייצר את תרשימי הדוח מנתונים אמיתיים |
| `generate_report.py` | מפיק את הדוח (DOCX + MD) |

---

## שינוי כתובת השרת

**נקודת השינוי היחידה בדף היא בלוק `CONFIG` בראש ה-`<script>` ב-`index.html`:**

```js
const CONFIG = {
  BASE_URL: "http://35.193.190.149:5678",
  SCAN_WEBHOOK_PATH: "/webhook/scan-code",
  GITHUB_WEBHOOK_PATH: "/webhook/github-webhook",
  HEALTH_PATH: "/healthz",
  SCAN_TIMEOUT_MS: 180000
};
```

לשינוי כתובת השרת יש לעדכן את `BASE_URL` בלבד. אין כתובות שרת מפוזרות בשאר הקובץ.

### ⚠️ HTTP מול HTTPS — קריטי

אם הדף מוגש ב-**HTTPS** (למשל מ-Google Cloud Storage או GitHub Pages) ו-`BASE_URL`
הוא **HTTP**, הדפדפן יחסום כל בקשה לשרת (Mixed Content). זו חסימה של הדפדפן, לא תקלה
בשרת, ואי אפשר לעקוף אותה מצד הדף.

הדף מזהה את המצב הזה מראש ומציג הסבר במקום להיכשל בשקט — אבל הפתרון האמיתי הוא לתת
ל-n8n כתובת HTTPS. שתי דרכים:

1. **Reverse proxy עם תעודה** (Caddy / Nginx + Let's Encrypt) — דורש פתיחת פורטים 80 ו-443 ב-firewall.
2. **Cloudflare Tunnel** — לא דורש פתיחת פורטים כלל, החיבור יוצא מהשרת החוצה.

---

## הרמת השרת מאפס

```bash
# על ה-VM
bash setup_n8n.sh      # מתקין Docker עדכני + מרים n8n עם volume קבוע
bash import_wf.sh      # מייבא את ה-workflow
bash restart_n8n.sh    # מפעיל מחדש עם כל משתני הסביבה
```

### משתני סביבה חיוניים

| משתנה | ערך | למה |
|---|---|---|
| `NODE_FUNCTION_ALLOW_BUILTIN` | `crypto` | בלעדיו צומת `Verify Request` נכשל — ה-sandbox חוסם את המודול, ואימות HMAC לא יכול לרוץ |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | `false` | מאפשר לצומת לקרוא את `GITHUB_WEBHOOK_SECRET` |
| `GITHUB_WEBHOOK_SECRET` | סוד אקראי | הסוד המשותף לאימות חתימת GitHub. נשמר ב-`/etc/n8n-webhook-secret` |

**שתי הגדרות אלה אינן ברירת מחדל.** בלעדיהן שכבת האבטחה שבורה בשקט.

---

## הגדרות שחייבות להתבצע ידנית ב-n8n

אלה דורשות הזנת מפתחות וסיסמאות ולכן חייבות להיעשות דרך ממשק ה-n8n:

1. **חשבון owner** — אימייל וסיסמה במסך ההתקנה הראשון.
2. **קרדנצ'ל Groq** — Settings → Credentials → Groq API. לאחר מכן לבחור אותו
   בשני צמתי המודל (`Red Team Groq Chat Model`, `Blue Team Groq Chat Model`).
3. **קרדנצ'ל GitHub (OAuth2)** — נדרש רק לפרסום הערות ולדחיפת Commit.
   לבחור אותו בצמתי `GitHub PR Comment` ו-`GitHub Push Commit`.
4. **הפעלת ה-workflow** — מתג Active בפינה הימנית העליונה.

בלי סעיף 2 הסוכנים לא ירוצו, והמערכת תחזיר תשובה ריקה.

---

## חיבור ה-webhook ל-GitHub

במאגר: Settings → Webhooks → Add webhook

| שדה | ערך |
|---|---|
| Payload URL | `<BASE_URL>/webhook/github-webhook` |
| Content type | `application/json` |
| Secret | התוכן של `/etc/n8n-webhook-secret` שעל השרת |
| Events | Pull requests |

ה-Secret חייב להיות זהה בשני הצדדים, אחרת כל בקשה תיפסל ב-HMAC.

---

## בדיקות

```bash
node scripts/eval/test_code_nodes.js      # בדיקות יחידה לצמתי ה-Code
python scripts/eval/run_eval.py           # הערכה כמותית מלאה (דורש קרדנצ'ל Groq פעיל)
python scripts/make_charts.py             # תרשימים
python scripts/generate_report.py         # הפקת הדוח
```

`run_eval.py` כותב את `scripts/eval/results.json`. `generate_report.py` קורא את הקובץ
הזה — אם הוא קיים, הדוח מציג טבלת ביצועים אמיתית; אם לא, הדוח מציין במפורש שההערכה
טרם הורצה. **הדוח לעולם אינו ממציא מספרים.**

---

## אימות ידני של שכבת האבטחה

```bash
# מאגר שאינו ברשימת ההיתר -> חייב להחזיר 403
curl -i -X POST -H "Content-Type: application/json" \
  -d '{"number":1,"repository":{"name":"x","full_name":"attacker/x","owner":{"login":"attacker"}}}' \
  http://<HOST>:5678/webhook/github-webhook

# חתימה מזויפת -> חייב להחזיר 403
curl -i -X POST -H "Content-Type: application/json" \
  -H "x-hub-signature-256: sha256=deadbeef" \
  -d '{"number":1,"repository":{"name":"cyber-management-project","full_name":"Levi2599/cyber-management-project","owner":{"login":"Levi2599"}}}' \
  http://<HOST>:5678/webhook/github-webhook
```

שתי הבקשות חייבות להידחות **לפני** שהמערכת מבצעת קריאה כלשהי למודל שפה.
