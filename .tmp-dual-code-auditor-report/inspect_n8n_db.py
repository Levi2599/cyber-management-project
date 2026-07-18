import sqlite3
import json

database = r"C:\Users\amit2\.n8n\database.sqlite"
connection = sqlite3.connect(database)
tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%credential%'")]
print(tables)
for table in tables:
    print(table, connection.execute(f'PRAGMA table_info("{table}")').fetchall())

print("credential metadata")
for row in connection.execute("SELECT id, name, type, createdAt, updatedAt FROM credentials_entity ORDER BY type, name"):
    print(row)

execution_tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%execution%'")]
print("execution tables", execution_tables)
for table in execution_tables:
    print(table, connection.execute(f'PRAGMA table_info("{table}")').fetchall())

print("target workflow executions")
for row in connection.execute("SELECT id, finished, mode, startedAt, stoppedAt, status FROM execution_entity WHERE workflowId = ? ORDER BY id DESC", ("claudeDualCodeAuditor01",)):
    print(row)

print("latest execution error summary")
for execution_id, payload in connection.execute("SELECT executionId, data FROM execution_data WHERE executionId IN (1008, 989, 988) ORDER BY executionId DESC"):
    data = json.loads(payload)
    if isinstance(data, list):
        data = data[0] if data else {}
    if isinstance(data, str):
        data = json.loads(data)
    result = data.get("resultData", {}) if isinstance(data, dict) else {}
    if isinstance(result, str):
        result = json.loads(result)
    error = result.get("error", {}) if isinstance(result, dict) else {}
    print(execution_id, {key: error.get(key) for key in ("message", "description", "node") if error.get(key)})
