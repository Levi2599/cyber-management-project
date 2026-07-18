import requests
import json

url = 'http://localhost:5678/api/v1/workflows'
headers = {
    'X-N8N-API-KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMWYwMWIxNy0wZTM0LTQ2ZGQtOTBiZi1hM2MyYjFhYzFhYmEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjUzZWRkNDAtYWM3OS00ZGQ5LTgxMGYtNWNjOGJjN2I4NjBiIiwiaWF0IjoxNzgyODk5ODUxfQ.IXsYTYgMsXbonaKX7QhOE-KUHHcEZ7uPq8mcn6-jP7c'
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        for wf in data.get('data', []):
            print(f"ID: {wf.get('id')}, Name: {wf.get('name')}, Active: {wf.get('active')}")
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
