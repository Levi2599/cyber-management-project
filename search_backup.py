import json

path = r"c:\Users\amit2\OneDrive\Desktop\לימודים\שנה ג\סמסטר ב\מבוא לסייבר בניהול\workflow-backup-2026-07-18-pre-github-integration.json"

try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        for i, item in enumerate(data):
            name = item.get('name', '')
            if 'Dual' in name or 'Auditor' in name or 'Code' in name:
                print(f"Index {i}: {name} (nodes: {len(item.get('nodes', []))})")
except Exception as e:
    print(f"Error: {e}")
