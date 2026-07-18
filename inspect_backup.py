import json

path = r"c:\Users\amit2\OneDrive\Desktop\לימודים\שנה ג\סמסטר ב\מבוא לסייבר בניהול\workflow-backup-2026-07-18-pre-github-integration.json"

try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        print(f"Data is a list of {len(data)} items.")
        for i, item in enumerate(data):
            print(f"\nItem {i}:")
            print(f"  Name: {item.get('name')}")
            print(f"  Active: {item.get('active')}")
            print(f"  Node count: {len(item.get('nodes', []))}")
            print("  Node Names and Types:")
            for n in item.get('nodes', [])[:15]:
                print(f"   - {n.get('name')} ({n.get('type')})")
            if len(item.get('nodes', [])) > 15:
                print("   - ...")
    else:
        print("Data is a dict.")
        print(f"Name: {data.get('name')}")
        print(f"Active: {data.get('active')}")
        print(f"Node count: {len(data.get('nodes', []))}")
except Exception as e:
    print(f"Error: {e}")
