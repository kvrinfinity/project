from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
import database

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = sqlite3.connect('LoginData.db')
        user = conn.execute("SELECT * FROM USERS WHERE email=? AND password=?", (email, password)).fetchone()
        conn.close()
        if user:
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/membership')
def membership():
    return render_template('membership.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/signup')
def signUp():
    return render_template('signup.html')

@app.route('/add_user', methods=['POST'])
def add_user():
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('email')
    password = request.form.get('password')

    connection = sqlite3.connect('LoginData.db')
    cursor = connection.cursor()

    ans = cursor.execute("SELECT * from USERS where email=? AND password=?", (email, password)).fetchall()
    if len(ans) > 0:
        connection.close()
        return render_template('signUp.html', msg="User already exists")
    else:
        cursor.execute("INSERT INTO USERS(first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
                       (fname, lname, email, password))
        connection.commit()
        connection.close()
        return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
