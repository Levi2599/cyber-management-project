import json

path = r"c:\Users\amit2\OneDrive\Desktop\לימודים\שנה ג\סמסטר ב\מבוא לסייבר בניהול\workflow-backup-2026-07-18-pre-github-integration.json"

try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        for i, item in enumerate(data):
            print(f"Index {i}: {item.get('name')}")
except Exception as e:
    print(f"Error: {e}")
