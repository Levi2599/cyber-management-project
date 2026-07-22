import os
import sys

import json
import requests

# המפתח והכתובת נקראים ממשתני סביבה. אין להטמיע מפתח בקוד — הקוד הזה ציבורי.
API_KEY = os.environ.get('N8N_API_KEY')
BASE_URL = os.environ.get('N8N_BASE_URL', 'http://localhost:5678')

if not API_KEY:
    sys.exit('N8N_API_KEY is not set. See .env.example.')

workflow_id = os.environ.get('N8N_WORKFLOW_ID', 'dualCodeAuditor01')
url = f'{BASE_URL}/api/v1/workflows/{workflow_id}'
headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

# Load the backup workflow
with open('workflow-claudeDualCodeAuditor01-backup.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

nodes = wf['nodes']
connections = wf['connections']

# Find and update 'Red Team Agent' text parameter to use code_to_analyze
for n in nodes:
    if n['name'] == 'Red Team Agent':
        n['parameters']['text'] = "=Here is the source code to analyze: {{ $json.code_to_analyze }}. Please execute your Red Team analysis."
        print("Updated Red Team Agent text parameter.")
    elif n['name'] == 'Edit Fields':
        assignments = n['parameters']['assignments']['assignments']
        for a in assignments:
            if a['name'] == 'original_code':
                a['value'] = "={{ $json.code_to_analyze }}"
            elif a['name'] == 'full_report':
                a['value'] = "=# דוח ביקורת קוד כפול\n\nExecutive Summary\n\n## CVSS וניתוח ווקטור התקיפה\n{{ $node[\"Red Team Agent\"].json.output.match(/CVSS:3\\.1\\/[A-Z:\\/]+/) }}\n\n{{ $node[\"Red Team Agent\"].json.output }}\n\n---\n\n{{ $node[\"Blue Team Agent\"].json.output }}"
        print("Updated Edit Fields assignments.")

# Let's define the new nodes
new_nodes = [
    {
        "parameters": {
            "httpMethod": "POST",
            "path": "github-webhook",
            "responseMode": "onReceived",
            "options": {}
        },
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [
            -600,
            100
        ],
        "id": "1a111111-1111-1111-1111-111111111110",
        "name": "GitHub Webhook"
    },
    {
        "parameters": {
            "url": "=https://api.github.com/repos/{{ $json.body.repository.full_name }}/pulls/{{ $json.body.number }}",
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [
                    {
                        "name": "Accept",
                        "value": "application/vnd.github.v3.diff"
                    },
                    {
                        "name": "User-Agent",
                        "value": "n8n-dual-code-auditor"
                    }
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [
            -400,
            100
        ],
        "id": "1a111111-1111-1111-1111-111111111111",
        "name": "Get PR Diff"
    },
    {
        "parameters": {
            "jsCode": "const diffText = items[0].json.data || items[0].json.response || items[0].json;\nreturn [{\n  json: {\n    code_to_analyze: typeof diffText === 'string' ? diffText : JSON.stringify(diffText),\n    source: 'github',\n    repo_owner: $('GitHub Webhook').item.json.body.repository.owner.login,\n    repo_name: $('GitHub Webhook').item.json.body.repository.name,\n    pr_number: $('GitHub Webhook').item.json.body.number,\n    branch: $('GitHub Webhook').item.json.body.pull_request.head.ref,\n    file_path: (typeof diffText === 'string' ? (diffText.match(/\\+\\+\\+ b\\/(.+)/) || [])[1] : '') || 'main.py'\n  }\n}];"
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [
            -200,
            100
        ],
        "id": "1a111111-1111-1111-1111-111111111112",
        "name": "Parse Diff"
    },
    {
        "parameters": {
            "assignments": {
                "assignments": [
                    {
                        "id": "sa1",
                        "name": "code_to_analyze",
                        "value": "={{ $json.code_to_analyze }}",
                        "type": "string"
                    },
                    {
                        "id": "sa2",
                        "name": "source",
                        "value": "={{ $json.source }}",
                        "type": "string"
                    },
                    {
                        "id": "sa3",
                        "name": "repo_owner",
                        "value": "={{ $json.repo_owner }}",
                        "type": "string"
                    },
                    {
                        "id": "sa4",
                        "name": "repo_name",
                        "value": "={{ $json.repo_name }}",
                        "type": "string"
                    },
                    {
                        "id": "sa5",
                        "name": "pr_number",
                        "value": "={{ $json.pr_number }}",
                        "type": "number"
                    },
                    {
                        "id": "sa6",
                        "name": "branch",
                        "value": "={{ $json.branch }}",
                        "type": "string"
                    },
                    {
                        "id": "sa7",
                        "name": "file_path",
                        "value": "={{ $json.file_path }}",
                        "type": "string"
                    }
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [
            0,
            100
        ],
        "id": "1a111111-1111-1111-1111-111111111113",
        "name": "Set GitHub Input"
    },
    {
        "parameters": {
            "assignments": {
                "assignments": [
                    {
                        "id": "sc1",
                        "name": "code_to_analyze",
                        "value": "={{ $json.chatInput }}",
                        "type": "string"
                    },
                    {
                        "id": "sc2",
                        "name": "source",
                        "value": "chat",
                        "type": "string"
                    },
                    {
                        "id": "sc3",
                        "name": "repo_owner",
                        "value": "",
                        "type": "string"
                    },
                    {
                        "id": "sc4",
                        "name": "repo_name",
                        "value": "",
                        "type": "string"
                    },
                    {
                        "id": "sc5",
                        "name": "pr_number",
                        "value": 0,
                        "type": "number"
                    },
                    {
                        "id": "sc6",
                        "name": "branch",
                        "value": "",
                        "type": "string"
                    },
                    {
                        "id": "sc7",
                        "name": "file_path",
                        "value": "",
                        "type": "string"
                    }
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [
            -150,
            304
        ],
        "id": "1a111111-1111-1111-1111-111111111114",
        "name": "Set Chat Input"
    },
    {
        "parameters": {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "type": "string",
                    "value": ""
                },
                "conditions": [
                    {
                        "id": "cond1",
                        "leftValue": "={{ $json.source }}",
                        "rightValue": "github",
                        "operator": {
                            "type": "string",
                            "operation": "equals"
                        }
                    }
                ],
                "combinator": "and"
            },
            "options": {}
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [
            980,
            304
        ],
        "id": "1a111111-1111-1111-1111-111111111115",
        "name": "If GitHub Source"
    },
    {
        "parameters": {
            "authentication": "oAuth2",
            "resource": "issueComment",
            "operation": "create",
            "owner": {
                "__rl": True,
                "value": "={{ $json.repo_owner }}",
                "mode": "id"
            },
            "repository": {
                "__rl": True,
                "value": "={{ $json.repo_name }}",
                "mode": "id"
            },
            "issueId": "={{ $json.pr_number }}",
            "body": "={{ $json.full_report }}"
        },
        "type": "n8n-nodes-base.github",
        "typeVersion": 1.1,
        "position": [
            1200,
            200
        ],
        "id": "1a111111-1111-1111-1111-111111111116",
        "name": "GitHub PR Comment"
    },
    {
        "parameters": {
            "authentication": "oAuth2",
            "resource": "file",
            "operation": "edit",
            "owner": {
                "__rl": True,
                "value": "={{ $json.repo_owner }}",
                "mode": "id"
            },
            "repository": {
                "__rl": True,
                "value": "={{ $json.repo_name }}",
                "mode": "id"
            },
            "filePath": "={{ $json.file_path }}",
            "fileContent": "={{ $json.fixed_code }}",
            "branch": "={{ $json.branch }}",
            "commitMessage": "Secure fix for vulnerability (Auto-healed by Blue Team)"
        },
        "type": "n8n-nodes-base.github",
        "typeVersion": 1.1,
        "position": [
            1420,
            200
        ],
        "id": "1a111111-1111-1111-1111-111111111117",
        "name": "GitHub Push Commit"
    }
]

nodes.extend(new_nodes)

# Connect nodes
connections["Chat Trigger"] = {
    "main": [
        [
            {
                "node": "Set Chat Input",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

connections["Set Chat Input"] = {
    "main": [
        [
            {
                "node": "Red Team Agent",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

connections["GitHub Webhook"] = {
    "main": [
        [
            {
                "node": "Get PR Diff",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

connections["Get PR Diff"] = {
    "main": [
        [
            {
                "node": "Parse Diff",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

connections["Parse Diff"] = {
    "main": [
        [
            {
                "node": "Set GitHub Input",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

connections["Set GitHub Input"] = {
    "main": [
        [
            {
                "node": "Red Team Agent",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

connections["Google Drive"] = {
    "main": [
        [
            {
                "node": "If GitHub Source",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

connections["If GitHub Source"] = {
    "main": [
        [
            {
                "node": "GitHub PR Comment",
                "type": "main",
                "index": 0
            }
        ],
        []
    ]
}

connections["GitHub PR Comment"] = {
    "main": [
        [
            {
                "node": "GitHub Push Commit",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# Clean body for n8n API, sending only name, nodes, connections, settings
payload = {
    "name": wf.get("name"),
    "nodes": nodes,
    "connections": connections,
    "settings": {}
}

try:
    response = requests.put(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Workflow updated successfully in n8n!")
        with open('dual_code_auditor_wf_updated.json', 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print("Updated workflow JSON saved locally.")
    else:
        print("Failed to update:")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
