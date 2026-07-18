import requests
import json

workflow_id = 'claudeDualCodeAuditor01'
url = f'http://localhost:5678/api/v1/workflows/{workflow_id}'
headers = {
    'X-N8N-API-KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMWYwMWIxNy0wZTM0LTQ2ZGQtOTBiZi1hM2MyYjFhYzFhYmEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjUzZWRkNDAtYWM3OS00ZGQ5LTgxMGYtNWNjOGJjN2I4NjBiIiwiaWF0IjoxNzgyODk5ODUxfQ.IXsYTYgMsXbonaKX7QhOE-KUHHcEZ7uPq8mcn6-jP7c'
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        with open('dual_code_auditor_wf.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Workflow saved to dual_code_auditor_wf.json")
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
