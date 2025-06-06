import sqlite3

conn = sqlite3.connect('LoginData.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS USERS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fname varchar(100),
    lname varchar(100),
    email TEXT UNIQUE,
    password TEXT,
    ref_code varchar(8)
)
""")

ans = cursor.execute('SELECT * FROM USERS').fetchone()
print(ans)
conn.commit()
conn.close()
