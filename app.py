from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
import database
import random

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

def get_refcode():
    code = random.randint(10000, 99999)
    reff_code = 'kvr'+str(code)
    return reff_code

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
        reff_code = get_refcode()
        check_reff = cursor.execute("SELECT * FROM USERS WHERE ref_code = ?", (reff_code,)).fetchall()

        while len(check_reff) > 0:
            reff_code = get_refcode()
            check_reff = cursor.execute("SELECT * FROM USERS WHERE ref_code = ?", (reff_code,)).fetchall()
        
        print(reff_code)
        # Now insert the new user
        cursor.execute("""
            INSERT INTO USERS(fname, lname, email, password, ref_code) 
            VALUES (?, ?, ?, ?, ?)
            """, (fname, lname, email, password, reff_code,))
        ans = cursor.execute('select fname,ref_code from USERS where fname=?',(fname,)).fetchall()
        print(ans)
        connection.commit()
        connection.close()
        return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
