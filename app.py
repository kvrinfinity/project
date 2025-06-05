from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import database  # import your database module
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/signUp')
def signUp():

    return render_template('signUp.html')

@app.route('/home')
def home():
    fname = request.args.get('fname')
    lname = request.args.get('lname')
    email = request.args.get('email')

    return render_template('home.html', fname=fname, lname=lname, email=email)

@app.route('/login_validation' ,methods=['POST'])
def login_validation():
    email = request.form.get('email')
    password = request.form.get('password')

    connection = sqlite3.connect('LoginData.db')
    cursor = connection.cursor()

    user = cursor.execute("SELECT * FROM USERS WHERE email=? and password=?",(email,password)).fetchall()
    connection.close()

    if(len(user)>0):
        return redirect(f'/home?fname={user[0][0]}&lname={user[0][1]}&email={user[0][2]}')
    else:
        return redirect('/login')
    
@app.route('/add_user', methods=['POST'])
def add_user():
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('email')
    password = request.form.get('password')

    connection = sqlite3.connect('LoginData.db')
    cursor = connection.cursor()

    ans = cursor.execute("SELECT * from USERS where email=? AND password=?",(email,password)).fetchall()
    if(len(ans)>0):
        connection.close()
        return render_template('signUp.html',msg="user already exists")
    else:
        cursor.execute("INSERT INTO USERS(first_name,last_name,email,password)values(?,?,?,?)",(fname,lname,email,password))
        connection.commit()
        connection.close()
        return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
