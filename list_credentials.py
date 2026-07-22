import os
import sys

import requests
import json

# המפתח והכתובת נקראים ממשתני סביבה. אין להטמיע מפתח בקוד — הקוד הזה ציבורי.
API_KEY = os.environ.get('N8N_API_KEY')
BASE_URL = os.environ.get('N8N_BASE_URL', 'http://localhost:5678')

if not API_KEY:
    sys.exit('N8N_API_KEY is not set. See .env.example.')

url = f'{BASE_URL}/api/v1/credentials'
headers = {
    'X-N8N-API-KEY': API_KEY
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        for cred in data.get('data', []):
            print(f"ID: {cred.get('id')}, Name: {cred.get('name')}, Type: {cred.get('type')}")
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
