# PRD — מערכת "מבקר הקוד הכפול" (Dual Code Auditor)
**סוג מסמך:** Product Requirements Document | **פרויקט גמר — קורס מבוא לסייבר בניהול**

---

## 1. תקציר מנהלים

"מבקר הקוד הכפול" הוא מערכת Multi-Agent אוטונומית ב-n8n המדמה תהליך התקפה-הגנה בזמן אמת על קוד תוכנה: סוכן **Red Team** מנתח קוד שסופק ומאתר בו חולשות אבטחה, וסוכן **Blue Team** מתקן את הקוד באופן אקטיבי ("Self-Healing") בהתבסס על ממצאי הסוכן הראשון. המערכת מתועדת אוטומטית כיומן ניהול סיכונים מתמשך.

המערכת בנויה סביב מודל **Actor vs. Critic** (סוכן מבצע מול סוכן מבקר), הפותר בעיה מוכרת של מודל שפה בודד: נטייה להזיות (Hallucinations) ולהתראות שווא (False Positives), שעליהן אנליסט סייבר ממוצע מבזבז כ-70% מזמנו. במקום שהמערכת רק תעיר למפתח מה לתקן, היא מיישמת "הגנה במהירות מכונה" — מזהה, מנתחת ומתקנת בעצמה, עוד לפני שהפגיעות מגיעה לסביבת הייצור.

---

## 2. ארכיטקטורה — שכבת מעבדה (מומשה) ושכבת ייצור (מתוכננת)

הפיתוח מתבצע בשתי שכבות מכוונות: תחילה "מעבדה סטרילית" לבחינת תקשורת הסוכנים בסביבה מבוקרת, ולאחריה מעבר לאינטגרציית CI/CD מלאה מול GitHub. גישה זו נבחרה במפורש כדי למנוע תרחיש של דחיפת קוד שבור לסביבת פיתוח אמיתית לפני שהלוגיקה אומתה.

### שכבה A — מעבדת הבדיקה (ממומש)

```
Chat Trigger ("When chat message received")
   │  קלט ידני: קוד לבדיקה מודבק בצ'אט
   ▼
Red Team Agent  ──(Model)── Groq Chat Model (llama-3.3-70b-versatile)
   │  Prompt: "Here is the source code to analyze: {{ $json.chatInput }}.
   │  Please execute your Red Team analysis."
   │  System Message: איתור חולשות (OWASP Top 10), הפקת CVSS 3.1 מלא + PoC מדויק
   ▼
Blue Team Agent ──(Model)── Groq Chat Model (llama-3.3-70b-versatile)
   │  Prompt: {{ $node["Red Team Agent"].json.output }}
   │  System Message: Self-Healing — שכתוב הקוד לגרסה בטוחה מול ה-PoC שהוצג
   ▼
Edit Fields (Set)
   │  original_code, vulnerability_report, cvss_vector_string (חילוץ regex),
   │  fixed_code
   ▼
Google Drive (Create From Text, Append=true)
   קובץ: Cyber_Security_Log.txt — מבנה Markdown:
   # כותרת → Executive Summary → ## CVSS וניתוח וקטור → דוח מלא → קוד מתוקן
```

**תרחיש בדיקה:**
```python
def get_user_data(username):
    # Vulnerable SQL query
    query = "SELECT * FROM users WHERE username = '" + username + "';"
    cursor.execute(query)
    return cursor.fetchall()
```
קלט זה (חולשת SQL Injection קלאסית) משמש לאימות שהצוות האדום מזהה את הפגיעות ומפיק וקטור CVSS תקין, ושהצוות הכחול משכתב אותה לקוד מאובטח (למשל שימוש ב-Parameterized Queries).

### שכבה B — סביבת הייצור (מתוכננת, השלב הבא)

זהה לשכבה A, בשינויים הבאים:
- **Trigger:** GitHub Webhook (אירועי Push / Pull Request) במקום Chat Trigger.
- **שלב נוסף בתחילת התהליך:** Code Extraction — HTTP Request שמושך את קובץ ה-Diff מהריפו.
- **Action בסוף התהליך:** GitHub Node מורחב הדוחף Commit חדש / מעדכן את ה-Pull Request עם קוד הצוות הכחול, וממתין לאישור מפתח (Merge) — במקום להסתפק בתגובת טקסט פסיבית בלבד.

---

## 3. הנמקה ארכיטקטונית

**מדוע שני סוכנים ולא אחד?** סוכן AI בודד שמנתח וגם מתקן קוד עלול לטעות בביטחון-יתר וליצור המלצות שגויות. חלוקת התפקידים ל"תוקף" (מזהה ומוכיח פריצה בפועל) ו"מגן" (מאמת את הממצא ורק אז מתקן) יוצרת מנגנון בקרה הדדית שמפחית משמעותית התראות שווא.

**מדוע לא סוכן AI שלישי שמנהל את השניים האחרים?** תזמור התהליך (Orchestration) מבוצע על ידי n8n עצמו — חיבורי הצמתים קובעים באופן נוקשה את זרימת המידע מהקלט, דרך שני הסוכנים, ועד לתיעוד. הוספת "סוכן מפקח" הייתה מייצרת סיכון מיותר להזיות ובזבוז משאבי אינפרנס (טוקנים) ללא תועלת אמיתית; ניתוב לוגי (למשל לפי חומרת CVSS) מתבצע ביעילות בצמתים טכניים זולים (If/Switch) ולא ב-AI.

**מדוע Google Drive עם Append ולא קובץ חדש בכל הרצה?** תיעוד מרוכז ורציף הוא הבסיס לניהול סיכונים ארגוני — קובץ יחיד המצטבר עם הזמן מאפשר מעקב היסטורי אחר חולשות וכיסוי תיקונים, במקום ריבוי קבצים שיוצר "רעש" ניהולי.

---

## 4. System Prompts

**Red Team Agent:**
> "אתה מומחה סייבר התקפי ואנליסט Red Team בכיר. תפקידך לבצע ניתוח מעמיק לקוד שסופק ולאתר חולשות אבטחה (כגון SQL Injection, XSS, Broken Auth). לכל חולשה, עליך להפיק דוח הכולל: תיאור טכני של הפגיעות; הוכחת היתכנות (PoC) המדגימה ניצול מעשי; מדדי CVSS 3.1 מלאים (Exploitability Metrics + Impact Metrics); CVSS Vector String מלא."

**Blue Team Agent:**
> "אתה ארכיטקט אבטחה מצוות ה-Blue Team. תפקידך לבצע ריפוי (Self-Healing) לקוד הפגיע. עליך לעבור על דוח הסוכן האדום ולהתייחס ספציפית למדדי ה-CVSS שנמצאו. הפלט שלך חייב לכלול: את גרסת הקוד המתוקנת במלואה; הסבר מפורט על התיקונים שבוצעו וכיצד הם חוסמים את הפריצה שהודגמה, תוך שמירה על עקרונות ה-CIA (סודיות, אמינות וזמינות)."

---

## 5. מתודולוגיית ניקוד CVSS 3.1

הסוכן האדום מחויב לחשב עבור כל חולשה:

**Exploitability Metrics (מדד המאמץ):**
- Attack Vector (AV) — Network / Adjacent / Local / Physical
- Attack Complexity (AC) — Low / High
- Privileges Required (PR) — None / Low / High
- User Interaction (UI) — None / Required

**Impact Metrics (מדד הנזק, לפי מודל CIA):**
- Confidentiality (C), Integrity (I), Availability (A) — כל אחד None / Low / High

**פלט חובה:** מחרוזת Vector מלאה בפורמט `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:L/A:N`, המשמשת כ"תעודת זהות" של החולשה וניתנת להזנה חוזרת במחשבון CVSS חיצוני לצורך אימות על ידי איש אבטחה אנושי.

---

## 6. דרישות קדם והתקנה

- Node.js v24.14.0, הרצת n8n מקומית (`npm install n8n -g` ואז `n8n start`).
- Groq API Key, מוגדר כ-Credential מסוג Groq API ב-n8n; מודל: `llama-3.3-70b-versatile`.
- Google Drive OAuth — פרויקט ב-Google Cloud Console עם Google Drive API מופעל, מסך הסכמה מסוג External עם המשתמש כ-Test User, ו-Redirect URI: `http://localhost:5678/rest/oauth2-credential/callback`.
- (לשכבת הייצור) הרשאות GitHub App/Webhook עם גישת Push+Pull Request על הריפו הרלוונטי.

---

## 7. קריטריוני קבלה — כולל תוצאות בדיקה בפועל

הארכיטקטורה (שכבה A) נבנתה והורצה בפועל ב-n8n מקומי, פעמיים ברצף, עם קלט הבדיקה הרשמי (הפונקציה עם SQL Injection):

| # | קריטריון | סטטוס |
|---|---|---|
| 1 | חיבורי Groq ו-Google Drive פעילים ותקינים | ✅ Groq יציב; Google Drive **לסירוגין** (ראה #6) |
| 2 | הזנת קוד עם חולשת SQL Injection → Red Team מזהה ומפיק CVSS Vector תקין | ✅ **אומת בפועל** — הופק `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:L/A:N` ודוח PoC מלא בעברית |
| 3 | Blue Team מפיק קוד מתוקן + הסבר תיקון מלא | ✅ **אומת בפועל** — הוחזר קוד Python עם `cursor.execute(query, (username,))` (Parameterized Query) + הסבר |
| 4 | הדוח מתווסף (Append) לקובץ לוג יחיד ב-Drive מבלי לדרוס תיעוד קודם | ✅ אומת בהרצה אחת; ראה סעיף 8 לגבי יציבות |
| 5 | מעבר לשכבת הייצור: GitHub Webhook + דחיפת תיקון אקטיבית ל-PR | ⛔ ממתין לפיתוח |
| 6 | אימות הרצה מלאה מקצה-לקצה מול חשבון Google Drive אמיתי | ⚠ **לא יציב** — הצליח בהרצה אחת, נכשל בשתיים אחרות עם שגיאת "authorization grant invalid/expired/revoked" זהה בכל פעם |

---

## 8. בעיות ידועות ופתרונות

1. **חיבור שגוי בין מודל השפה לסוכן:** יש לוודא שצומת ה-Groq Chat Model מחובר לנקודת החיבור הייעודית בתחתית צומת ה-AI Agent (מסומנת בכוכבית, `Chat Model*`) ולא לנקודת חיבור צדדית רגילה — חיבור שגוי גורם לכשל שנראה כמו בעיית API Key אך למעשה הוא בעיית חיווט.
2. **שדה Prompt (User Message) חייב להיות במצב Expression, לא Fixed:** אם ה-`{{ }}` אינו מוגדר כביטוי (fx), n8n שולח למודל את הטקסט המילולי "{{ $json.chatInput }}" במקום את הערך בפועל, והסוכן ינתח את התבנית עצמה (למשל יזהה "XSS בתבנית") במקום את הקוד האמיתי. **תוקן ואומת בפועל** בגרסה שהורצה.
3. **חוסר עקביות ב-OAuth Token של Google Drive:** בבדיקות בפועל, אותו workflow עם אותם credentials הצליח לכתוב ל-Drive בהרצה אחת ונכשל בשתי הרצות אחרות (סמוכות בזמן) עם שגיאת הרשאה זהה. ייתכן ותוקף ה-refresh token פג/מתחדש בצורה לא אמינה. **פתרון מומלץ:** להיכנס ל-Settings → Credentials → Google Drive account וללחוץ Reconnect/Sign in with Google מחדש לפני הרצה קריטית (למשל הגשה).
4. **חסימת מסך הסכמת Google OAuth בהתקנה ראשונית:** לעיתים Google דורשת אימות אמצעי תשלום גם עבור שימוש בשכבה החינמית. פתרון חלופי במקרה של חסימה מתמשכת: החלפת צומת Google Drive בצמתי `Convert to File` + `Read/Write Files from Disk` (Write) לשמירת הדוח מקומית במקום בענן.
5. **עבודה משותפת של כמה משתמשים על אותו Workflow** אינה נתמכת בסביבת n8n המקומית (Local, localhost:5678); נדרשת בדיקה נפרדת אם יש צורך בכך מול גרסת הענן של n8n.

---

## 9. המשך מתוכנן

1. מימוש שכבת הייצור: החלפת ה-Chat Trigger בטריגר GitHub Webhook, הוספת שלב Code Extraction (Diff), ושדרוג פעולת הסיום לדחיפת Commit/עדכון PR בפועל.
2. אימות הרצה מלאה מול חשבון Google Drive אמיתי ווידוא תקינות הקובץ המתועד.
3. הכנת הסבר עסקי-ניהולי (למשל לרמת CFO/CEO) לחומרת חולשות שנמצאות, במונחי מודל CIA ועלות נזק צפויה — לצורך הצגת הפרויקט מעבר להיבט הטכני בלבד.
