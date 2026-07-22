import sqlite3

def get_user(uid):
    conn = sqlite3.connect("app.db")
    query = "SELECT * FROM users WHERE id = ?"
    result = conn.execute(query, (uid,)).fetchall()
    conn.close()
    return result