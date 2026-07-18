import shutil

src = r"c:\Users\amit2\OneDrive\Desktop\לימודים\שנה ג\סמסטר ב\מבוא לסייבר בניהול\dual_code_auditor_wf.json"
dest = r"c:\Users\amit2\OneDrive\Desktop\לימודים\שנה ג\סמסטר ב\מבוא לסייבר בניהול\workflow-claudeDualCodeAuditor01-backup.json"

try:
    shutil.copy(src, dest)
    print(f"Backed up to {dest}")
except Exception as e:
    print(f"Error backing up: {e}")
