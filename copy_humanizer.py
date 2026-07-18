import shutil
from pathlib import Path

src_dir = Path(r"C:\Users\amit2\.gemini\config\skills\humanizer")
dest_dir = Path(r"c:\Users\amit2\OneDrive\Desktop\לימודים\שנה ג\סמסטר ב\מבוא לסייבר בניהול\.agents\skills\humanizer")

dest_dir.mkdir(parents=True, exist_ok=True)

files_to_copy = ["AGENTS.md", "LICENSE", "README.md", "SKILL.md"]

for f_name in files_to_copy:
    src_file = src_dir / f_name
    dest_file = dest_dir / f_name
    if src_file.exists():
        shutil.copy(src_file, dest_file)
        print(f"Copied {f_name} to {dest_file}")
    else:
        print(f"Source file not found: {src_file}")

print("Copy completed.")
