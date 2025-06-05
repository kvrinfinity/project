import sqlite3

conn = sqlite3.connect('LoginData.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS USERS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT
)
""")
conn.commit()
conn.close()
