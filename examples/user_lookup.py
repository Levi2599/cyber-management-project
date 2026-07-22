"""
Deliberately vulnerable sample used to demonstrate the Dual Code Auditor.

This file exists so the auditor has something to find. Do not copy this
pattern into real code — the query below is built by string concatenation
and is trivially injectable.
"""

import sqlite3


def get_user(uid):
    """Look up a single user by id."""
    conn = sqlite3.connect("app.db")
    query = "SELECT * FROM users WHERE id = " + uid
    return conn.execute(query).fetchall()
