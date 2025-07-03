from collections import defaultdict
import datetime
from email.mime.application import MIMEApplication
import re
from time import time
from flask import Flask, Response, abort, get_flashed_messages, make_response, render_template, request, redirect, url_for, session, flash, jsonify
import os
import bcrypt
import random
import gridfs
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from gridfs import GridFS
from bson.objectid import ObjectId
from flask import send_file
import io
import smtplib
import random
from email.mime.text import MIMEText
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart

def generate_otp():
    return str(random.randint(1000, 9999))

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_otp_email(to_email, otp):
    subject = "Your One-Time Password (OTP) - KVR Infinity"

    sender_email = "nishankamath@gmail.com"
    sender_password = "hxui wjwz adsz vycn"

    logo_url = "https://kvrinfinity.in/static/images/logo.png"  # Your hosted logo

    html = f"""
    <html>
      <body style="margin:0;padding:0;background-color:#800000;font-family:Segoe UI, sans-serif;">
        <div style="display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px;">
          <div style="background-color:#fff;max-width:400px;width:100%;border-radius:10px;padding:30px;text-align:center;box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            
            <img src="{logo_url}" alt="KVR Infinity Logo" style="height:50px;margin-bottom:20px;" />
            <h2 style="color:#800000;margin-bottom:10px;">One Time Password</h2>
            <p style="color:#555;margin:0 0 20px;">Use the OTP below to verify your email address:</p>

            <div style="font-size:36px;font-weight:bold;color:#800000;margin:20px 0;">{otp}</div>

            <p style="font-size:13px;color:#e74c3c;margin-bottom:30px;">Valid for 10 minutes only</p>

            <p style="font-size:12px;color:#999;margin:0;">
              If you didn't request this, you can ignore it.<br>
              Need help? <a href="https://kvrinfinity.in/contact">Contact Us</a>
            </p>

            <hr style="margin:20px 0;border:none;border-top:1px solid #eee;" />

            <p style="font-size:11px;color:#bbb;margin:0;">
              &copy; 2025 KVR Infinity
            </p>
          </div>
        </div>
      </body>
    </html>
    """

    # Compose and send email
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = to_email
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        print(f"Mail sent to {to_email} with OTP {otp}")
    except Exception as e:
        print("Error sending email:", e)


app = Flask(__name__)
app.secret_key = os.urandom(24)



# MongoDB Setup
uri = "mongodb+srv://praveen:tHXsIKjbFLMuwki4@cluster0.ct1utq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client['company']
courses_col = db['courses']
results_col = db['final_exam_results']
bundles_col = db["bundles"]
users_col = db['users']
fitness_tests_col = db['fitness_test']
blogs_col = db['blogs']
membership_col = db["membership"]
admin_col = db["admin"]
contact_collection = db["contact-info"]
book_stalls = db['book_stalls']

fs = GridFS(db)

@app.route('/')
def index():
    # ✅ Fetch all fitness tests
    fitness_tests = list(fitness_tests_col.find())

    # Add image URL for each fitness test
    for test in fitness_tests:
        if 'image_id' in test:
            test['image_url'] = f"/image_fitness/{test['image_id']}"
        else:
            test['image_url'] = "/static/default-test.png"

    # ✅ Pass fitness tests to index.html
    return render_template('index.html', fitness_tests=fitness_tests)


def delete_expired_memberships():
    result = membership_col.delete_many({
        "valid_till": {"$lt": datetime.now()}
    })
    print(f"🧹 Deleted {result.deleted_count} expired memberships.")

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy-policy.html')

@app.route('/terms-and-conditions')
def terms_and_conditions():
    return render_template('terms-and-conditions.html')

@app.route('/cookies-policy')
def cookies_policy():
    return render_template('cookies-policy.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    delete_expired_memberships()

    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')

        # ✅ 1. Admin login
        admin_user = admin_col.find_one({"email": email})
        if admin_user and 'password' in admin_user:
            if bcrypt.checkpw(password.encode(), admin_user['password']):
                session['user_email'] = email
                role = admin_user.get('dept')

                if role == 'Administration Department':
                    session['admin_log'] = True
                    return redirect(url_for('admin'))
                elif role == 'Digital Marketing':
                    return redirect(url_for('write_blog'))
                elif role == 'Sales Department':
                    return redirect(url_for('sales_admin_dashboard'))

        # ✅ 2. Regular user login
        user = db.users.find_one({"email": email})
        if user and bcrypt.checkpw(password.encode(), user['password']):
            session['user_email'] = email
            membership = membership_col.find_one({"user_email": email})
            if not membership or membership['valid_till'] < datetime.now():
                return redirect(url_for('membership'))
            return redirect(url_for('home'))

        # ✅ 3. Book stall login
        stall = book_stalls.find_one({"email": email})
        if stall and bcrypt.checkpw(password.encode(), stall['password']):
            session['user_email'] = email
            session['stall_id'] = str(stall['_id'])
            return redirect(url_for('stall_dashboard'))

        # ❌ Invalid login
        return render_template('login.html', msg='Invalid credentials')

    return render_template('login.html')



@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        session['user_email'] = email

        # 1️⃣ Check in users collection
        user = db.users.find_one({'email': email})
        if user:
            session['otp_target'] = 'user'
            session['user_name'] = f"{user.get('fname', '')} {user.get('lname', '')}"

        else:
            # 2️⃣ Check in admin collection
            admin = admin_col.find_one({'email': email})
            if admin:
                session['otp_target'] = 'admin'
                session['user_name'] = admin.get('name', 'Admin User')
            else:
                # 3️⃣ Check in book stalls collection
                stall = book_stalls.find_one({'email': email})
                if stall:
                    session['otp_target'] = 'stall'
                    session['user_name'] = stall.get('stall_name', 'Book Stall')
                else:
                    return render_template('forgot_password.html', msg="Email not found in our records.")

        # ✅ Common OTP setup
        otp = generate_otp()
        session['otp'] = otp
        session['otp_mode'] = 'reset'
        session['reset_email'] = email

        send_otp_email(email, otp)  # You already have this function
        return render_template('otp_validation.html')

    return render_template('forgot_password.html')


@app.route('/resend_otp', methods=['GET'])
def resend_otp():
    if 'reset_email' not in session or 'otp_mode' not in session:
        flash("Session expired. Please try again.", "warning")
        return redirect(url_for('forgot_password'))

    email = session['reset_email']
    otp = generate_otp()
    session['otp'] = otp  # Replace old OTP with new one

    send_otp_email(email, otp)

    flash("A new OTP has been sent to your email.", "info")
    return render_template('otp_validation.html')


@app.route('/signup')
def signUp():
    return render_template('signup.html')

@app.route('/membership')
def membership():
    return render_template('membership.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        data = {
            "fullname": request.form.get('fullname'),
            "company": request.form.get('company'),
            "email": request.form.get('email'),
            "phone": request.form.get('phone'),
            "address": request.form.get('address'),
            "message": request.form.get('message')
        }
        print(data)
        contact_collection.insert_one(data)
        flash("Thank you! Your message has been received.", "success")
        return redirect('/contact')

    return render_template('contactus.html')

@app.route('/contact_admin')
def contact_admin():
    if not session.get('admin_log'):
        return redirect(url_for('login'))
    contacts = contact_collection.find()
    return render_template('contact_admin.html', contacts=contacts)

@app.route('/delete_contact/<id>')
def delete_contact(id):
    contact_collection.delete_one({'_id': ObjectId(id)})
    flash('Contact entry deleted successfully!', 'success')
    return redirect('/contact_admin')

@app.route('/payment_success', methods=['POST'])
def payment_success():
    try:
        # ✅ FIXED: Get request data first
        data = request.get_json()
        print("🔔 /payment_success hit with:", data)

        user_email = data.get('user_email', 'guest@kvr.com')
        user_name = data.get('user_name', 'Guest')
        payment_id = data.get('razorpay_payment_id')
        referral_code = data.get('ref_code')

        # 🧾 Amount paid (from session or fallback)
        base_price = 10000
        amount_paid = session.get('amount_paid', base_price)

        # 👤 User info
        user_data = users_col.find_one({"email": user_email})
        user_whatsapp = user_data.get("whatsapp", "Not Provided") if user_data else "Not Provided"

        # 🗓 Dates
        payment_date = datetime.now()
        valid_till = payment_date + timedelta(days=365)
        receipt_id = f"KVR-{payment_date.strftime('%Y%m%d-%H%M%S')}"
        file_name = f"receipt_{receipt_id}.pdf"

        # 🧾 Generate & save PDF receipt
        generate_receipt(
            member_name=user_name,
            email=user_email,
            phone=user_whatsapp,
            amount=amount_paid,
            receipt_id=receipt_id,
            transaction_date=payment_date.strftime('%Y/%m/%d'),
            valid_through=valid_till.strftime('%Y/%m/%d')
        )

        fs = gridfs.GridFS(db)
        with open(file_name, 'rb') as f:
            receipt_file_id = fs.put(f, filename=file_name)

        # 💾 Store membership info
        membership_col.insert_one({
            "user_email": user_email,
            "user_name": user_name,
            "payment_date": payment_date,
            "receipt_id": receipt_id,
            "valid_till": valid_till,
            "receipt_file_id": receipt_file_id
        })

        # 🎁 Reward referral
        if referral_code:
            ref_user = users_col.find_one({'ref_code': referral_code})
            if ref_user:
                users_col.update_one({'_id': ref_user['_id']}, {'$inc': {'wallet_balance': 1000}})
                print(f"✅ ₹1000 added to user: {ref_user['email']}")
            else:
                ref_stall = book_stalls.find_one({'referral_code': referral_code})
                if ref_stall:
                    if 'wallet_balance' not in ref_stall:
                        book_stalls.update_one({'_id': ref_stall['_id']}, {'$set': {'wallet_balance': 1000}})
                    else:
                        book_stalls.update_one({'_id': ref_stall['_id']}, {'$inc': {'wallet_balance': 1000}})
                    print(f"✅ ₹1000 added to book stall: {ref_stall['stall_name']}")

        # 📧 Send receipt email
        subject = "Payment Successful - KVR Infinity Membership"
        body = f"""Hello {user_name},

✅ Thank you for purchasing the KVR Infinity Membership!

🧾 Receipt ID: {receipt_id}  
📅 Membership Valid Till: {valid_till.strftime('%d-%m-%Y')}  
💰 Amount Paid: ₹{amount_paid}  
📱 WhatsApp: {user_whatsapp}

Your receipt is attached.

For any help, contact us at sales@kvrinfinity.in.

Regards,  
Team KVR Infinity
"""

        sender_email = "nishankamath@gmail.com"
        sender_password = "hxui wjwz adsz vycn"

        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = user_email
        message.attach(MIMEText(body, 'plain'))

        with open(file_name, 'rb') as f:
            part = MIMEApplication(f.read(), _subtype='pdf')
            part.add_header('Content-Disposition', 'attachment', filename=file_name)
            message.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, user_email, message.as_string())

        print(f"✅ Email sent to {user_email}")
        os.remove(file_name)

        return jsonify({"status": "success", "redirect": "/login"})

    except Exception as e:
        print("❌ Error in /payment_success:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/blogs')
def display_blogs():
    blogs = list(blogs_col.find())
    for blog in blogs:
        blog['_id'] = str(blog['_id'])
        blog['image_url'] = f"/blog-image/{blog['image_id']}"
    return render_template('blogs.html', blogs=blogs)

@app.route('/blog-image/<image_id>')
def blog_image(image_id):
    image = fs.get(ObjectId(image_id))
    return app.response_class(image.read(), mimetype=image.content_type)

@app.route('/write-blog', methods=['GET', 'POST'])
def write_blog():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['intro']
        author = request.form['author']
        linkedin = request.form['linkedin']
        image_file = request.files.get('image')

        # Collect subheadings and paragraphs
        subheadings = request.form.getlist('subheadings[]')
        paragraphs = request.form.getlist('paragraphs[]')
        sections = [{'subheading': sh, 'paragraph': para} for sh, para in zip(subheadings, paragraphs)]

        image_id = None
        if image_file and image_file.filename:
            image_id = fs.put(
                image_file,
                filename=secure_filename(image_file.filename),
                content_type=image_file.content_type
            )

        # Prepare blog document
        blog_data = {
            'title': title,
            'intro': content,
            'author': author,
            'linkedin': linkedin,
            'image_id': image_id,
            'sections': sections,
            'created_at': datetime.utcnow()
        }

        blogs_col.insert_one(blog_data)
        flash("✅ Blog posted successfully!", "success")
        return redirect(url_for('write_blog'))

    # GET request — load all blogs
    blogs = list(blogs_col.find().sort("created_at", -1))
    for blog in blogs:
        blog['_id'] = str(blog['_id'])

    return render_template('write_blog.html', blogs=blogs)


@app.route('/edit-blog/<blog_id>', methods=['GET', 'POST'])
def edit_blog(blog_id):
    blog = blogs_col.find_one({"_id": ObjectId(blog_id)})

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['intro']
        author = request.form['author']
        linkedin = request.form['linkedin']
        subheadings = request.form.getlist('subheadings[]')
        paragraphs = request.form.getlist('paragraphs[]')

        sections = [{'subheading': sh, 'paragraph': para} for sh, para in zip(subheadings, paragraphs)]

        update_data = {
            'title': title,
            'intro': content,
            'author': author,
            'linkedin': linkedin,
            'sections': sections,
        }

        blogs_col.update_one({"_id": ObjectId(blog_id)}, {"$set": update_data})
        flash("✅ Blog updated!", "success")
        return redirect(url_for('write_blog'))

    blog['_id'] = str(blog['_id'])
    return render_template('edit_blog.html', blog=blog)


@app.route('/delete-blog/<blog_id>')
def delete_blog(blog_id):
    blog = blogs_col.find_one({"_id": ObjectId(blog_id)})
    if blog and blog.get("image_id"):
        fs.delete(ObjectId(blog['image_id']))
    blogs_col.delete_one({"_id": ObjectId(blog_id)})
    flash("🗑️ Blog deleted successfully", "success")
    return redirect(url_for('write_blog'))


@app.route('/blog/<blog_id>')
def blog_detail(blog_id):
    blog = blogs_col.find_one({'_id': ObjectId(blog_id)})
    if blog:
        blog['_id'] = str(blog['_id'])
        blog['image_url'] = f"/blog-image/{blog['image_id']}"
        return render_template('blog_detail.html', blog=blog)
    else:
        return "Blog not found", 404


from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
def generate_receipt(member_name, email, phone, amount, receipt_id, transaction_date, valid_through):
    file_name = f"receipt_{receipt_id}.pdf"
    doc = SimpleDocTemplate(file_name, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Custom Styles
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=14, spaceAfter=12, alignment=1)
    label_style = styles['Normal']
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')

    # Company Info
    elements.append(Paragraph("KVR Infinity", header_style))
    elements.append(Paragraph("1st Floor, KH - Connects, JP Nagar 4th Phase, Bengaluru, India – 560078", label_style))
    elements.append(Paragraph("CIN: U72900AP2019PTC113696 | GSTIN: 37AAFCI5145J1ZD", label_style))
    elements.append(Paragraph("Phone: 918106147247 | Email: sales@kvrinfinity.in", label_style))
    elements.append(Spacer(1, 20))

    # Title
    elements.append(Paragraph("PAYMENT RECEIPT", header_style))

    # Receipt Metadata
    elements.append(Paragraph(f"<b>Receipt No:</b> {receipt_id}", label_style))
    elements.append(Paragraph(f"<b>Receipt Date:</b> {datetime.now().strftime('%Y/%m/%d')}", label_style))
    elements.append(Paragraph(f"<b>Transaction Date:</b> {transaction_date}", label_style))
    elements.append(Paragraph(f"<b>Transaction Amount:</b> Rs. {amount:,.2f}", label_style))
    elements.append(Paragraph(f"<b>Valid Through:</b> {valid_through}", label_style))
    elements.append(Spacer(1, 12))

    # Bill To
    elements.append(Paragraph(f"<b>Bill to:</b> {member_name}", label_style))
    elements.append(Paragraph(phone, label_style))
    elements.append(Paragraph(email, label_style))
    elements.append(Spacer(1, 12))

    # Item Table
    data = [
        ["Item & Description", "Amount"],
        ["KVR Infinity Membership", f"Rs. {amount:,.2f}"]
    ]
    table = Table(data, colWidths=[350, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#850014")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOX', (0, 0), (-1, -1), 1, colors.gray),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Notes
    elements.append(Paragraph("This is a computer generated pay receipt and does not require a signature.", styles['Italic']))
    elements.append(Paragraph("The total amount is inclusive of 18% GST.", styles['Italic']))

    doc.build(elements)
    print(f"✅ Receipt saved as: {file_name}")

@app.route('/admin/add-referral', methods=['GET', 'POST'])
def add_referral_code():
    search_term = ""
    query = {}

    if request.method == 'POST':
        if 'search' in request.form:
            search_term = request.form['search'].strip()
            if search_term:
                query = {
                    "$or": [
                        {"stall_name": {"$regex": search_term, "$options": "i"}},
                        {"location": {"$regex": search_term, "$options": "i"}}
                    ]
                }
        else:
            # 📥 Collect form data
            stall_name = request.form['stall_name']
            location = request.form['location']
            referral_code = request.form['referral_code']
            email = request.form.get('email')
            password = request.form.get('password')
            whatsapp = request.form.get('whatsapp')
            account_holder = request.form.get('account_holder')
            account_number = request.form.get('account_number')
            bank_name = request.form.get('bank_name')
            branch = request.form.get('branch')
            ifsc = request.form.get('ifsc')
            upi = request.form.get('upi')

            # 🛑 Validate required fields
            if not email or not password or not whatsapp:
                flash("Email, Password, and WhatsApp are required!", "danger")
                return redirect(url_for('add_referral_code'))

            # 🔍 Check for uniqueness
            if book_stalls.find_one({"referral_code": referral_code}):
                flash("Referral code already exists!", "danger")
            elif book_stalls.find_one({"email": email}):
                flash("Email already in use!", "danger")
            else:
                # 🔐 Hash password
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                book_stalls.insert_one({
                    "stall_name": stall_name,
                    "location": location,
                    "referral_code": referral_code,
                    "email": email,
                    "password": hashed_password,
                    "whatsapp": whatsapp,
                    "created_at": datetime.utcnow(),
                    "wallet_balance": 0,
                    "account_holder": account_holder,
                    "account_number": account_number,
                    "bank_name": bank_name,
                    "branch": branch,
                    "ifsc": ifsc,
                    "upi": upi
                })
                flash("Stall and login credentials added successfully!", "success")

            return redirect(url_for('add_referral_code'))

    stalls_list = list(book_stalls.find(query).sort("created_at", -1))
    if not search_term:
        stalls_list = stalls_list[:5]

    return render_template("add_referral.html", stalls=stalls_list, search=search_term)

@app.route('/admin/edit-stall', methods=['GET', 'POST'])
def edit_stall():
    if request.method == 'POST':
        stall_id = request.form['stall_id']
        updated_data = {
            "stall_name": request.form['stall_name'],
            "location": request.form['location'],
            "referral_code": request.form['referral_code'],
            "email": request.form['email'],
            "whatsapp": request.form['whatsapp'],
            "account_holder": request.form.get('account_holder'),
            "account_number": request.form.get('account_number'),
            "bank_name": request.form.get('bank_name'),
            "branch": request.form.get('branch'),
            "ifsc": request.form.get('ifsc'),
            "upi": request.form.get('upi')
        }
        try:
            book_stalls.update_one({"_id": ObjectId(stall_id)}, {"$set": updated_data})
            flash("Stall updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating stall: {e}", "danger")
        return redirect(url_for('add_referral_code'))

    else:
        stall_id = request.args.get('stall_id')
        if not stall_id:
            flash("Missing stall ID", "danger")
            return redirect(url_for('add_referral_code'))

        stall = book_stalls.find_one({"_id": ObjectId(stall_id)})
        if not stall:
            flash("Stall not found", "danger")
            return redirect(url_for('add_referral_code'))

        return render_template("edit_stall.html", stall=stall)


@app.route('/home')
def home():
    if not session.get('user_email'):
        return redirect(url_for('login'))
    # Fetch top 6 courses with enrollment and chapter count
    top_courses = list(courses_col.aggregate([
        {
            "$addFields": {
                "enrollments_count": {
                    "$size": { "$ifNull": ["$enrolled_users", []] }
                },
                "chapters_count": {
                    "$size": { "$ifNull": ["$chapters", []] }
                }
            }
        },
        { "$sort": { "enrollments_count": -1 } },
        { "$limit": 6 }
    ]))

    # Add image URL for each course
    for course in top_courses:
        if 'course_image_id' in course:
            course['image_url'] = f"/image/{course['course_image_id']}"
        else:
            course['image_url'] = "/static/default.jpg"

    # Fetch all bundles
    bundles = list(bundles_col.find())

    # Add image URL and course count for each bundle
    for bundle in bundles:
        bundle['course_ids'] = bundle.get('course_ids', [])
        bundle['course_count'] = len(bundle['course_ids'])
        if 'image_id' in bundle:
            bundle['image_url'] = f"/image/{bundle['image_id']}"
        else:
            bundle['image_url'] = "/static/default-bundle.png"

    # ✅ Fetch all fitness tests
    fitness_tests = list(fitness_tests_col.find())

    # Add image URL for each fitness test
    for test in fitness_tests:
        if 'image_id' in test:
            test['image_url'] = f"/image_fitness/{test['image_id']}"
        else:
            test['image_url'] = "/static/default-test.png"

    # Return home.html with all 3 data types
    return render_template('home.html', top_courses=top_courses, bundles=bundles, fitness_tests=fitness_tests)


def update_bundle_progress(user_email, course_id, completed_chapters_list):
    user = users_col.find_one({'email': user_email})
    if not user:
        return

    for bundle_id in user.get('enrolled_bundles', []):
        bundle = bundles_col.find_one({'_id': ObjectId(bundle_id)})
        if not bundle or course_id not in bundle.get('course_ids', []):
            continue

        bundle_id_str = str(bundle_id)
        progress = user.get('bundle_progress', {})
        bprog = progress.get(bundle_id_str, {'completed_courses': 0, 'courses_done': {}})

        course_id_str = str(course_id)

        # If course not yet tracked or chapters have increased
        previous_chapters = set(bprog['courses_done'].get(course_id_str, []))
        new_chapters = set(completed_chapters_list)

        if new_chapters != previous_chapters:
            bprog['courses_done'][course_id_str] = list(new_chapters)

            if len(new_chapters) == courses_col.find_one({'_id': course_id}).get('chapters', []).__len__():
                bprog['completed_courses'] = len(bprog['courses_done'])

            progress[bundle_id_str] = bprog
            users_col.update_one({'email': user_email}, {'$set': {'bundle_progress': progress}})


@app.route('/enroll_bundle/<bundle_id>', methods=['POST'])
def enroll_bundle(bundle_id):
    user_email = session.get('user_email')
    if not user_email:
        flash("Login to enroll", "error")
        return redirect(url_for('login'))

    user = users_col.find_one({'email': user_email})
    if user:
        if 'enrolled_bundles' not in user:
            user['enrolled_bundles'] = []
        if bundle_id not in user['enrolled_bundles']:
            user['enrolled_bundles'].append(bundle_id)

            # Setup progress tracking
            progress = user.get('bundle_progress', {})
            progress[bundle_id] = {
                'completed_courses': 0,
                'courses_done': {}
            }

            users_col.update_one({'email': user_email}, {
                '$set': {
                    'enrolled_bundles': user['enrolled_bundles'],
                    'bundle_progress': progress
                }
            })
            flash("Enrolled in bundle!", "success")
    return redirect(url_for('bundle_detail', bundle_id=bundle_id))

@app.route('/bundle/<bundle_id>')
def bundle_detail(bundle_id):
    try:
        bundle_obj_id = ObjectId(bundle_id)
    except:
        flash("Invalid bundle ID", "error")
        return redirect(url_for('home'))

    # 🧩 Fetch bundle
    bundle = bundles_col.find_one({'_id': bundle_obj_id})
    if not bundle:
        flash("Bundle not found", "error")
        return redirect(url_for('home'))

    # 📦 Add image fallback
    bundle['image_url'] = f"/image/{bundle.get('image_id')}" if bundle.get('image_id') else "/static/default-bundle.png"
    
    # 🎓 Fetch courses in bundle
    course_ids = bundle.get('course_ids', [])
    course_object_ids = [ObjectId(cid) for cid in course_ids if ObjectId.is_valid(cid)]
    courses = list(courses_col.find({'_id': {'$in': course_object_ids}}))

    # 🧠 User info
    user_email = session.get('user_email')
    user_enrolled = False
    progress = {}

    if user_email:
        user = users_col.find_one({'email': user_email})
        if user:
            enrolled_bundles = user.get('enrolled_bundles', [])
            bundle_progress = user.get('bundle_progress', {})
            user_enrolled = str(bundle_id) in enrolled_bundles
            progress = bundle_progress.get(str(bundle_id), {
                'completed_courses': 0,
                'courses_done': {}
            })

    # 🧮 Process each course
    for course in courses:
        course['image_url'] = f"/image/{course.get('course_image_id')}" if course.get('course_image_id') else "/static/default.jpg"
        chapters = course.get('chapters', [])
        course['chapters_count'] = len(chapters)

        # 🧾 Fix enrollment count key
        course['enrollment_count'] = len(course.get('enrolled_users', [])) if isinstance(course.get('enrolled_users'), list) else 0

        # ✅ Progress logic
        course_id_str = str(course['_id'])
        completed_chapter_list = progress.get('courses_done', {}).get(course_id_str, [])
        completed_chapters = len(completed_chapter_list)
        course['completed_chapters'] = completed_chapters

        course['progress_percent'] = int((completed_chapters / course['chapters_count']) * 100) if course['chapters_count'] > 0 else 0

    return render_template(
        'bundle_detail.html',
        bundle=bundle,
        courses=courses,
        user_enrolled=user_enrolled,
        progress=progress
    )
@app.route('/about')
def about():
    return render_template('about.html')

def get_refcode():
    while True:
        code = random.randint(10000, 99999)
        reff_code = 'kvr' + str(code)
        if not db.users.find_one({'ref_code': reff_code}):
            return reff_code

@app.route('/add_user', methods=['POST'])
def add_user():
    fname = request.form.get('fname', '').strip()
    lname = request.form.get('lname', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password')
    whatsapp = request.form.get('whatsapp', '').strip()

    # Basic input validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return render_template('signup.html', msg="Invalid email format")

    if db.users.find_one({'email': email}):
        return render_template('signup.html', msg="User already exists")

    # Securely hash the password
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    ref_code = get_refcode()
    otp = generate_otp()

    session['temp_user'] = {
        'fname': fname,
        'lname': lname,
        'email': email,
        'password': hashed_password,
        'ref_code': ref_code,
        'whatsapp': whatsapp
    }
    session['otp'] = otp
    session['user_name'] = f"{fname} {lname}"
    session['user_email'] = email
    session['otp_mode'] = 'signup'

    send_otp_email(email, otp)
    return render_template('otp_validation.html')


@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    entered_otp = request.form.get('otp')
    actual_otp = session.get('otp')
    mode = session.get('otp_mode')

    if entered_otp != actual_otp:
        return render_template('otp_validation.html', msg="Incorrect OTP")

    # ✅ Signup Flow
    if mode == 'signup':
        user_data = session.get('temp_user')
        if not user_data:
            return redirect(url_for('signUp'))

        db.users.insert_one({
            'fname': user_data['fname'],
            'lname': user_data['lname'],
            'email': user_data['email'],
            'password': user_data['password'],
            'ref_code': user_data['ref_code'],
            'whatsapp': user_data['whatsapp'],
            'enrolled_courses': []
        })

        # Clear signup session data
        session['user_email'] = user_data['email']
        session.pop('otp', None)
        session.pop('otp_mode', None)
        session.pop('temp_user', None)

        return redirect(url_for('membership'))

    # ✅ Forgot Password Flow for user/admin/stall
    elif mode == 'reset':
        session['reset_verified'] = True
        # Do NOT clear otp_target or reset_email yet
        session.pop('otp', None)
        session.pop('otp_mode', None)

        return redirect(url_for('reset_password'))

    return redirect(url_for('login'))

from flask import Flask, render_template, request, redirect, url_for, session
import bcrypt

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Block unauthorized access
    if not session.get('reset_verified') or not session.get('reset_email'):
        return redirect(url_for('forgot_password'))

    email = session.get('reset_email')
    target = session.get('otp_target', 'user')  # default to user

    if request.method == 'POST':
        new_password = request.form.get('new_password')

        if not new_password:
            return render_template('reset_password.html', error="Password cannot be empty")

        # Hash the new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        # 🔄 Update password in the correct collection
        if target == 'user':
            db.users.update_one({'email': email}, {'$set': {'password': hashed_password}})
        elif target == 'admin':
            admin_col.update_one({'email': email}, {'$set': {'password': hashed_password}})
        elif target == 'stall':
            book_stalls.update_one({'email': email}, {'$set': {'password': hashed_password}})
        else:
            return render_template('reset_password.html', error="Invalid user type.")

        # ✅ Clear session flags
        session.pop('reset_verified', None)
        session.pop('reset_email', None)
        session.pop('otp_target', None)

        flash("Password reset successful. You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')



    
@app.route('/apply_referral', methods=['POST'])
def apply_referral():
    data = request.get_json()
    ref_code = data.get('ref_code')
    just_validate = data.get('just_validate', False)

    
    base_price = 10000
    discount = 0
    amount_paid = base_price 

    # ✅ Check for hardcoded referral code (40% OFF)
    if ref_code == 'kvr1122':
        discount = 40
        session['amount_paid'] = int(base_price - (base_price * (discount / 100)))
        return jsonify({'valid': True, 'discount': 40})
    if ref_code == 'kvr1111':
        discount = 99
        session['amount_paid'] = int(base_price - (base_price * (discount / 100)))
        return jsonify({'valid': True, 'discount': 99.99})

    # ✅ Check if referral code exists in database (70% OFF)
    user = db.users.find_one({'ref_code': ref_code})
    book_stall = book_stalls.find_one({'referral_code':ref_code})
    if user or book_stall:
        discount = 70
        session['amount_paid'] = int(base_price - (base_price * (discount / 100)))
        return jsonify({'valid': True, 'discount': 70})

    # ❌ Invalid referral code
    return jsonify({'valid': False})

    


from flask import Flask, render_template, request, redirect, flash, session
from bson import ObjectId
from werkzeug.utils import secure_filename

from flask import request, redirect, render_template, flash, Response, abort
from bson import ObjectId
from werkzeug.utils import secure_filename

@app.route('/download_users_csv')
def download_users_csv():
    if not session.get('admin_log'):
        return redirect(url_for('index'))
    from flask import Response
    import csv
    from datetime import datetime

    users = list(users_col.find())
    memberships = {m['user_email']: m for m in membership_col.find()}

    # CSV Header
    header = ['Name', 'Email', 'WhatsApp Number', 'Payment Date', 'Valid Till']

    def generate():
        yield ','.join(header) + '\n'
        for user in users:
            name = f"{user.get('fname', '')} {user.get('lname', '')}"
            email = user.get('email', '')
            whatsapp = user.get('whatsapp', '')

            membership = memberships.get(email, {})
            payment_date = membership.get('payment_date')
            valid_till = membership.get('valid_till')

            # Format dates
            payment_str = payment_date.strftime("%Y-%m-%d") if payment_date else ''
            valid_str = valid_till.strftime("%Y-%m-%d") if valid_till else ''

            row = [name, email, whatsapp, payment_str, valid_str]
            yield ','.join(row) + '\n'

    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=users_membership_data.csv'
    })


verifications_col = db["verifications"]
withdrawals_col = db["withdrawals"]


@app.route('/request_withdrawal', methods=['GET'])
def request_withdrawal_page():
    if 'user_email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for('login'))

    user_email = session['user_email']

    # Check in users collection (regular user)
    user = users_col.find_one({"email": user_email})

    if user:
        # Regular user must be verified
        if user.get('is_verified', False):
            wallet_balance = user.get('wallet_balance', 0)
            return render_template('withdraw.html', wallet_balance=wallet_balance, user=user)
        else:
            flash("Please verify your bank details before requesting a withdrawal.", "info")
            return redirect(url_for('submit_verification_page'))

    # Check in book_stalls collection (stall owner)
    stall = book_stalls.find_one({"email": user_email})
    if stall:
        wallet_balance = stall.get('wallet_balance', 0)
        return render_template('withdraw.html', wallet_balance=wallet_balance, user=stall)

    # If email not found in any collection
    flash("User not found.", "error")
    return redirect(url_for('login'))


@app.route('/submit-verification', methods=['GET', 'POST'])
def submit_verification_page():
    if 'user_email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for('login'))

    user_email = session['user_email']

    if request.method == 'POST':
        existing_verification = verifications_col.find_one({"email": user_email, "status": "pending"})
        if existing_verification:
            flash("You already have a pending verification request. Please wait for it to be approved.", "info")
            return redirect(url_for('user_dashboard'))

        verification_data = {
            "email": user_email,
            "adhar_number": request.form['aadhar_number'],
            "pancard_number": request.form['pan_number'],
            "bank_name": request.form['bank_name'],
            "branch": request.form['branch'],
            "ifsc": request.form['ifsc'],
            "account_number": request.form['account_number'],
            "account_holder": request.form['account_holder'],
            "upi": request.form.get('upi', ''),
            "status": "pending",
            "submitted_at": datetime.utcnow()
        }

        verifications_col.insert_one(verification_data)

        flash("✅ Verification submitted! You'll be approved within 72 hours.", "success")
        return redirect(url_for('user_dashboard'))

    return render_template('verify.html')



@app.route('/process_withdrawal', methods=['POST'])
def process_withdrawal():
    if 'user_email' not in session:
        flash("Please log in to complete this action.", "error")
        return redirect(url_for('login'))

    user_email = session['user_email']
    user = users_col.find_one({"email": user_email})
    stall = book_stalls.find_one({"email": user_email})

    user_type = 'user' if user else 'stall' if stall else None
    doc = user if user else stall

    if not doc:
        flash("User not found.", "error")
        return redirect(url_for('login'))

    try:
        amount = int(request.form['amount'])
    except ValueError:
        flash("Invalid amount. Please enter a number.", "error")
        return redirect(url_for('request_withdrawal_page'))

    if amount <= 0 or amount < 1000:
        flash("Withdrawal amount must be at least ₹1000.", "error")
        return redirect(url_for('request_withdrawal_page'))

    current_balance = float(doc.get('wallet_balance', 0))

    if amount > current_balance:
        flash(f"❌ Not enough balance. Available: ₹{current_balance}", "error")
        return redirect(url_for('request_withdrawal_page'))

    existing_pending = withdrawals_col.find_one({
        "email": user_email,
        "status": "pending"
    })
    if existing_pending:
        flash("You already have a pending withdrawal request.", "info")
        return redirect(url_for('request_withdrawal_page'))

    withdrawals_col.insert_one({
        'email': user_email,
        'amount': amount,
        'status': 'pending',
        'requested_at': datetime.utcnow(),
        'user_type': user_type
    })

    flash("✅ Withdrawal request submitted successfully!", "success")
    return redirect(url_for('user_dashboard' if user else 'stall_dashboard'))


from bson.objectid import ObjectId

@app.route('/approve-verification', methods=['POST'])
def approve_verification():
    if not session.get('admin_log'):
        return redirect(url_for('index'))
    verification_id = request.form.get('verification_id')
    
    if not verification_id:
        flash("Verification ID not provided.", "error")
        return redirect(url_for('verifications'))

    verification = verifications_col.find_one({"_id": ObjectId(verification_id)})
    
    if not verification:
        flash("Verification record not found.", "error")
        return redirect(url_for('verifications'))

    email = verification['email']

    # Update user and verification status
    users_col.update_one({"email": email}, {"$set": {"is_verified": True}})
    verifications_col.update_one(
        {"_id": ObjectId(verification_id)},
        {"$set": {"status": "approved"}}
    )

    flash(f"{email} has been verified.", "success")
    return redirect(url_for('verifications'))



@app.route('/approve-withdrawal/<withdrawal_id>', methods=['POST'])
def approve_withdrawal(withdrawal_id):
    if not session.get('admin_log'):
        return redirect(url_for('index'))

    withdrawal = withdrawals_col.find_one({"_id": ObjectId(withdrawal_id)})
    if not withdrawal or withdrawal.get("status") != "pending":
        flash("Invalid or already processed withdrawal request.", "error")
        return redirect(url_for('admin'))

    email = withdrawal['email']
    user = users_col.find_one({"email": email})
    stall = book_stalls.find_one({"email": email})
    doc = user if user else stall

    if not doc:
        flash("User not found.", "error")
        return redirect(url_for('admin'))

    amount = withdrawal['amount']
    current_balance = float(doc.get('wallet_balance', 0))

    if current_balance < amount:
        flash("Insufficient wallet balance.", "error")
        return redirect(url_for('admin'))

    # Deduct from correct collection
    collection = users_col if user else book_stalls
    collection.update_one({"email": email}, {"$inc": {"wallet_balance": -amount}})

    withdrawals_col.update_one(
        {"_id": ObjectId(withdrawal_id)},
        {
            "$set": {
                "status": "approved",
                "approved_at": datetime.utcnow(),
                "approved_by": session.get('admin_email', 'admin')
            }
        }
    )

    flash(f"✅ Withdrawal of ₹{amount} approved for {email}.", "success")
    return redirect(url_for('verifications'))


from flask import request, redirect, url_for, flash, session
from bson import ObjectId
from datetime import datetime

@app.route('/process_withdrawal_admin', methods=['POST'])
def process_withdrawal_admin():
    if not session.get('admin_log'):
        return redirect(url_for('index'))
    withdrawal_id = request.form.get('withdrawal_id')

    if not withdrawal_id:
        flash("Withdrawal ID is missing.", "error")
        return redirect(url_for('verifications'))

    try:
        withdrawal = withdrawals_col.find_one({"_id": ObjectId(withdrawal_id)})
    except Exception as e:
        print("❌ Error finding withdrawal:", e)
        flash("Invalid withdrawal ID.", "error")
        return redirect(url_for('verifications'))

    if not withdrawal:
        flash("Withdrawal not found.", "error")
        return redirect(url_for('verifications'))

    if withdrawal.get("status") != "pending":
        flash("Withdrawal already processed.", "error")
        return redirect(url_for('verifications'))

    email = withdrawal.get('email')
    if not email:
        flash("Email not found in withdrawal record.", "error")
        return redirect(url_for('verifications'))

    user = users_col.find_one({"email": email})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('verifications'))

    try:
        current_balance = float(user.get('wallet_balance', 0))
        amount = float(withdrawal.get('amount', 0))
    except Exception as e:
        print("⚠️ Error converting balance/amount:", e)
        flash("Invalid balance or amount data.", "error")
        return redirect(url_for('verifications'))

    if current_balance < amount:
        flash("Insufficient wallet balance.", "error")
        return redirect(url_for('verifications'))

    # Deduct balance
    result1 = users_col.update_one(
        {"email": email},
        {"$inc": {"wallet_balance": -amount}}
    )

    # Update withdrawal
    result2 = withdrawals_col.update_one(
        {"_id": ObjectId(withdrawal_id)},
        {
            "$set": {
                "status": "approved",
                "approved_at": datetime.utcnow(),
                "approved_by": session.get('admin_email', 'admin')
            }
        }
    )

    # Print result (debugging)
    print(f"✅ Deducted ₹{amount} from {email}: matched={result1.matched_count}, modified={result1.modified_count}")
    print(f"🟢 Withdrawal update: matched={result2.matched_count}, modified={result2.modified_count}")

    flash(f"✅ Withdrawal of ₹{amount} approved for {email}.", "success")
    return redirect(url_for('verifications'))

from bson import ObjectId
from datetime import datetime
from flask import request, session, redirect, url_for, flash

@app.route('/process_withdrawal_stall_admin', methods=['POST'])
def process_withdrawal_stall_admin():
    if not session.get('admin_log'):
        return redirect(url_for('index'))

    withdrawal_id = request.form.get('withdrawal_id')

    if not withdrawal_id:
        flash("Withdrawal ID is missing.", "error")
        return redirect(url_for('verifications'))

    try:
        withdrawal = withdrawals_col.find_one({"_id": ObjectId(withdrawal_id)})
    except Exception as e:
        print("❌ Error finding withdrawal:", e)
        flash("Invalid withdrawal ID.", "error")
        return redirect(url_for('verifications'))

    if not withdrawal:
        flash("Withdrawal not found.", "error")
        return redirect(url_for('verifications'))

    if withdrawal.get("status") != "pending":
        flash("Withdrawal already processed.", "error")
        return redirect(url_for('verifications'))

    if withdrawal.get("user_type") != "stall":
        flash("Invalid user type for this route.", "error")
        return redirect(url_for('verifications'))

    email = withdrawal.get('email')
    if not email:
        flash("Email not found in withdrawal record.", "error")
        return redirect(url_for('verifications'))

    stall_user = book_stalls.find_one({"email": email})
    if not stall_user:
        flash("Book stall user not found.", "error")
        return redirect(url_for('verifications'))

    try:
        current_balance = float(stall_user.get('wallet_balance', 0))
        amount = float(withdrawal.get('amount', 0))
    except Exception as e:
        print("⚠️ Error converting balance/amount:", e)
        flash("Invalid balance or amount data.", "error")
        return redirect(url_for('verifications'))

    if current_balance < amount:
        flash("Insufficient wallet balance.", "error")
        return redirect(url_for('verifications'))

    # ✅ FIX: Deduct balance using $set, not $inc (handles string balance)
    new_balance = current_balance - amount
    result1 = book_stalls.update_one(
        {"email": email},
        {"$set": {"wallet_balance": new_balance}}
    )

    # Update withdrawal status
    result2 = withdrawals_col.update_one(
        {"_id": ObjectId(withdrawal_id)},
        {
            "$set": {
                "status": "approved",
                "approved_at": datetime.utcnow(),
                "approved_by": session.get('admin_email', 'admin')
            }
        }
    )

    # Debug output
    print(f"✅ Deducted ₹{amount} from stall {email}: matched={result1.matched_count}, modified={result1.modified_count}")
    print(f"🟢 Withdrawal update: matched={result2.matched_count}, modified={result2.modified_count}")

    flash(f"✅ Book Stall withdrawal of ₹{amount} approved for {email}.", "success")
    return redirect(url_for('verifications'))

from datetime import datetime

@app.route('/sales_admin', methods=['GET', 'POST'])
def sales_admin_dashboard():
    users = list(users_col.find())
    verifications = {v['email']: v for v in verifications_col.find()}
    memberships = {m['user_email']: m for m in membership_col.find()}
    raw_withdrawals = list(withdrawals_col.find())

    withdrawals_list = []
    for wd in raw_withdrawals:
        approved_at_dt = wd.get("approved_at")
        withdrawals_list.append({
            "email": wd.get("email", "N/A"),
            "amount": wd.get("amount", "N/A"),
            "status": wd.get("status", "N/A"),
            "requested_at": datetime.fromtimestamp(wd.get("requested_at").timestamp()).strftime('%Y-%m-%d %H:%M') if wd.get("requested_at") else "N/A",
            "approved_at": datetime.fromtimestamp(approved_at_dt.timestamp()).strftime('%Y-%m-%d %H:%M') if approved_at_dt else "N/A",
            "approved_by": wd.get("approved_by", "N/A"),
            "approved_at_raw": approved_at_dt if approved_at_dt else datetime.min  # used for sorting
        })

    # Sort by latest approved_at
    withdrawals_list.sort(key=lambda x: x['approved_at_raw'], reverse=True)

    results = []
    for user in users:
        email = user['email']
        verification = verifications.get(email, {})
        membership = memberships.get(email, {})

        results.append({
            "fname": user.get('fname'),
            "lname": user.get('lname'),
            "email": email,
            "whatsapp": user.get('whatsapp', 'N/A'),
            "valid_till": membership.get('valid_till', '').strftime('%Y-%m-%d') if membership.get('valid_till') else 'N/A',
            "adhar": verification.get('adhar_number', 'N/A'),
            "pan": verification.get('pancard_number', 'N/A'),
            "bank": f"{verification.get('bank_name', '')} - {verification.get('branch', '')}",
            "upi": verification.get('upi', 'N/A'),
            "status": verification.get('status', 'N/A')
        })

    return render_template('sales_admin.html', users=results, withdrawals=withdrawals_list)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_log'):
        flash("Unauthorized access")
        return redirect(url_for('login'))
    if request.method == 'POST':
        # ---------- BUNDLE CREATION ----------
        if 'bundle_name' in request.form:
            bundle_name = request.form['bundle_name']
            bundle_description = request.form.get('bundle_description', '')
            selected_course_ids = request.form.getlist('selected_courses')
            course_object_ids = [ObjectId(cid) for cid in selected_course_ids if cid]

            image_file = request.files.get('bundle_image')
            if image_file and image_file.filename:
                image_id = fs.put(image_file, filename=secure_filename(image_file.filename), content_type=image_file.content_type)
            else:
                flash("Bundle image is required.", "error")
                return redirect('')

            bundles_col.insert_one({
                'bundle_name': bundle_name,
                'description': bundle_description,
                'course_ids': course_object_ids,
                'image_id': image_id,
            })

            flash('Bundle created successfully!', 'success')
            return redirect('/admin')

        # ---------- COURSE CREATION ----------
        elif 'course_name' in request.form:
            course_name = request.form['course_name']
            main_section = request.form['main_section']
            description = request.form.getlist('description[]')

            image_file = request.files.get('course_image')
            if not image_file or not image_file.filename:
                flash("Course image is required.", "error")
                return redirect('/admin')

            image_id = fs.put(image_file, filename=secure_filename(image_file.filename), content_type=image_file.content_type)

            chapters = []
            for i, chapter_name in enumerate(request.form.getlist('chapter_name[]')):
                v_ts = request.form.getlist(f'video_title_{i}[]')
                v_fs = request.files.getlist(f'video_file_{i}[]')
                videos = []
                for t, vf in zip(v_ts, v_fs):
                    if t and vf.filename:
                        fid = fs.put(vf, filename=secure_filename(vf.filename))
                        videos.append({'title': t, 'file_id': fid})

                qs = request.form.getlist(f'quiz_question_{i}[]')
                qa = request.form.getlist(f'quiz_option_a_{i}[]')
                qb = request.form.getlist(f'quiz_option_b_{i}[]')
                qc = request.form.getlist(f'quiz_option_c_{i}[]')
                qd = request.form.getlist(f'quiz_option_d_{i}[]')
                qans = request.form.getlist(f'quiz_answer_{i}[]')

                quiz = [
                    {'question': qu, 'options': {'a': a, 'b': b, 'c': c, 'd': d}, 'answer': ans}
                    for qu, a, b, c, d, ans in zip(qs, qa, qb, qc, qd, qans) if qu
                ]

                chapters.append({'chapter_name': chapter_name, 'videos': videos, 'quiz': quiz})

            fqs = request.form.getlist('final_question[]')
            fa = request.form.getlist('final_option_a[]')
            fb = request.form.getlist('final_option_b[]')
            fc = request.form.getlist('final_option_c[]')
            fd = request.form.getlist('final_option_d[]')
            fans = request.form.getlist('final_answer[]')

            final_exam = [
                {'question': qu, 'options': {'a': a, 'b': b, 'c': c, 'd': d}, 'answer': ans}
                for qu, a, b, c, d, ans in zip(fqs, fa, fb, fc, fd, fans) if qu
            ]

            courses_col.insert_one({
                'course_name': course_name,
                'main_section': main_section,
                'description': description,
                'course_image_id': image_id,
                'chapters': chapters,
                'final_exam': final_exam
            })

            flash('Course added successfully!', 'success')
            return redirect('/admin')

        # ---------- FITNESS TEST CREATION ----------
        elif 'test_name' in request.form:
            test_name = request.form['test_name']
            test_image = request.files.get('test_image')
            test_video = request.files.get('fitness_video')

            image_id = None
            video_id = None

            if test_image and test_image.filename:
                image_id = fs.put(
                    test_image,
                    filename=secure_filename(test_image.filename),
                    content_type=test_image.content_type
                )

            if test_video and test_video.filename:
                video_id = fs.put(
                    test_video,
                    filename=secure_filename(test_video.filename),
                    content_type=test_video.content_type
                )

            ft_questions = request.form.getlist('ft_question[]')
            ft_a = request.form.getlist('ft_option_a[]')
            ft_b = request.form.getlist('ft_option_b[]')
            ft_c = request.form.getlist('ft_option_c[]')
            ft_d = request.form.getlist('ft_option_d[]')
            ft_ans = request.form.getlist('ft_answer[]')
            ft_company = request.form.getlist('ft_company[]')

            questions = []
            for q, a, b, c, d, ans, comp in zip(ft_questions, ft_a, ft_b, ft_c, ft_d, ft_ans, ft_company):
                if q and ans:
                    questions.append({
                        'question': q,
                        'options': {'a': a, 'b': b, 'c': c, 'd': d},
                        'answer': ans,
                        'company': comp
                    })

            if not questions:
                flash("No valid questions provided.", "error")
                return redirect('/admin')

            result = fitness_tests_col.insert_one({
                'test_name': test_name,
                'image_id': image_id,
                'video_id': video_id,
                'questions': questions
            })

            print(f"✅ Fitness test inserted with ID: {result.inserted_id}")
            flash("Fitness test created successfully!", "success")
            return redirect('/admin')

    # ---------- GET REQUEST ----------
    all_courses = list(courses_col.find())
    all_bundles = list(bundles_col.find())
    all_fitness_tests = list(fitness_tests_col.find())

    for bundle in all_bundles:
        bundle['image_url'] = f"/image/{bundle['image_id']}" if 'image_id' in bundle else "/static/default.jpg"

    for test in all_fitness_tests:
        test['image_url'] = f"/image/{test['image_id']}" if 'image_id' in test else "/static/default.jpg"

    grouped_courses = defaultdict(list)
    for course in all_courses:
        grouped_courses[course['main_section']].append(course)

    return render_template(
        'admin.html',
        grouped_courses=grouped_courses,
        courses=all_courses,
        bundles=all_bundles,
        fitness_tests=all_fitness_tests
    )

@app.route('/admin-management', methods=['GET', 'POST'])
def admin_management():
    if request.method == 'POST':
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        new_employee = {
            "fname": request.form['fname'],
            "lname": request.form['lname'],
            "email": request.form['email'],
            "dept": request.form['dept'],
            "joined_at": request.form['joined_at'],
            "password": hashed_password  # 🛡️ store hashed
        }

        admin_col.insert_one(new_employee)
        return redirect(url_for('admin_management'))

    employees = list(admin_col.find())
    return render_template("admin_management.html", employees=employees)


# Delete employee
@app.route('/admin-delete/<string:emp_id>')
def admin_delete(emp_id):
    from bson.objectid import ObjectId
    admin_col.delete_one({"_id": ObjectId(emp_id)})
    return redirect(url_for('admin_management'))

# Edit employee (GET = show form, POST = update record)
@app.route('/admin-edit/<string:emp_id>', methods=['GET', 'POST'])
def admin_edit(emp_id):
    from bson.objectid import ObjectId
    emp = admin_col.find_one({"_id": ObjectId(emp_id)})

    if request.method == 'POST':
        updated = {
            "fname": request.form['fname'],
            "lname": request.form['lname'],
            "email": request.form['email'],
            "dept": request.form['dept'],
            "joined_at": request.form['joined_at']
        }

        password = request.form.get('password')
        if password:  # ✅ Only update if password is entered
            import bcrypt
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            updated['password'] = hashed_password

        admin_col.update_one({"_id": ObjectId(emp_id)}, {"$set": updated})
        return redirect(url_for('admin_management'))

    return render_template("admin_edit.html", emp=emp)

@app.route('/edit_course/<course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    course = courses_col.find_one({'_id': ObjectId(course_id)})
    if not course:
        flash("Course not found", "error")
        return redirect('/admin')

    if request.method == 'POST':
        course_name = request.form['course_name']
        main_section = request.form['main_section']
        description = request.form.getlist('description[]')

        # Update image if new one provided
        image_file = request.files.get('course_image')
        image_id = course['course_image_id']
        if image_file and image_file.filename:
            image_id = fs.put(image_file, filename=secure_filename(image_file.filename))

        # Process chapters
        chapters = []
        chapter_names = request.form.getlist('chapter_name[]')

        for i, chapter_name in enumerate(chapter_names):
            videos = []
            video_titles = request.form.getlist(f'video_title_{i}[]')
            video_files = request.files.getlist(f'video_file_{i}[]')
            video_ids = request.form.getlist(f'video_file_id_{i}[]')

            for title, file, vid in zip(video_titles, video_files, video_ids):
                if title:
                    if file and file.filename:
                        fid = fs.put(file, filename=secure_filename(file.filename))
                    else:
                        fid = ObjectId(vid) if vid else None
                    if fid:
                        videos.append({'title': title, 'file_id': fid})

            # Quiz
            qs = request.form.getlist(f'quiz_question_{i}[]')
            qa = request.form.getlist(f'quiz_option_a_{i}[]')
            qb = request.form.getlist(f'quiz_option_b_{i}[]')
            qc = request.form.getlist(f'quiz_option_c_{i}[]')
            qd = request.form.getlist(f'quiz_option_d_{i}[]')
            qans = request.form.getlist(f'quiz_answer_{i}[]')

            quiz = [
                {'question': qu, 'options': {'a': a, 'b': b, 'c': c, 'd': d}, 'answer': ans}
                for qu, a, b, c, d, ans in zip(qs, qa, qb, qc, qd, qans) if qu
            ]

            chapters.append({'chapter_name': chapter_name, 'videos': videos, 'quiz': quiz})

        # Final Exam
        final_exam = [
            {'question': qu, 'options': {'a': a, 'b': b, 'c': c, 'd': d}, 'answer': ans}
            for qu, a, b, c, d, ans in zip(
                request.form.getlist('final_question[]'),
                request.form.getlist('final_option_a[]'),
                request.form.getlist('final_option_b[]'),
                request.form.getlist('final_option_c[]'),
                request.form.getlist('final_option_d[]'),
                request.form.getlist('final_answer[]')
            ) if qu
        ]

        courses_col.update_one(
            {'_id': ObjectId(course_id)},
            {'$set': {
                'course_name': course_name,
                'main_section': main_section,
                'description': description,
                'course_image_id': image_id,
                'chapters': chapters,
                'final_exam': final_exam
            }}
        )

        flash("Course updated successfully!", "success")
        return redirect('/admin')

    return render_template("edit_course.html", course=course)


@app.route('/create-fitness-test', methods=['GET', 'POST'])
def create_fitness_test():
    if request.method == 'POST':
        test_name = request.form['test_name']
        test_image = request.files.get('test_image')
        test_video = request.files.get('fitness_video')

        image_id = video_id = None

        if test_image and test_image.filename:
            image_id = fs.put(
                test_image,
                filename=secure_filename(test_image.filename),
                content_type=test_image.content_type
            )

        if test_video and test_video.filename:
            video_id = fs.put(
                test_video,
                filename=secure_filename(test_video.filename),
                content_type=test_video.content_type
            )

        questions = []
        total_questions = len(request.form.getlist('ft_answer[]'))

        for i in range(total_questions):
            q_text = request.form.getlist('ft_question[]')[i]
            q_img = request.files.getlist('ft_question_image[]')[i]

            question = {}
            if q_text:
                question['text'] = q_text
            if q_img and q_img.filename:
                q_img_id = fs.put(
                    q_img,
                    filename=secure_filename(q_img.filename),
                    content_type=q_img.content_type
                )
                question['image_id'] = q_img_id

            options = {}
            for opt in ['a', 'b', 'c', 'd']:
                opt_text = request.form.getlist(f'ft_option_{opt}[]')[i]
                opt_file = request.files.getlist(f'ft_option_{opt}_img[]')[i]

                option = {}
                if opt_text:
                    option['text'] = opt_text
                if opt_file and opt_file.filename:
                    opt_img_id = fs.put(
                        opt_file,
                        filename=secure_filename(opt_file.filename),
                        content_type=opt_file.content_type
                    )
                    option['image_id'] = opt_img_id

                options[opt] = option

            questions.append({
                'question': question,
                'options': options,
                'answer': request.form.getlist('ft_answer[]')[i],
                'company': request.form.getlist('ft_company[]')[i]
            })

        if not questions:
            flash("No valid questions provided.", "error")
            return redirect('/create-fitness-test')

        fitness_tests_col.insert_one({
            'test_name': test_name,
            'image_id': image_id,
            'video_id': video_id,
            'questions': questions,
            'created_at': datetime.utcnow()
        })

        flash("✅ Fitness test created successfully!", "success")
        return redirect('/create-fitness-test')

    # ========== Display existing tests ==========
    tests = list(fitness_tests_col.find())
    for test in tests:
        test['_id'] = str(test['_id'])
        test['question_count'] = len(test.get('questions', []))

    return render_template('create_fitest.html', tests=tests)



@app.route('/verifications')
def verifications():
    # Get pending user verification requests
    pending_verifications = list(verifications_col.find({"status": "pending"}))
    for v in pending_verifications:
        v['_id'] = str(v['_id'])

    # Get approved user verifications only (not for book stalls)
    approved_verifications = {
        v['email'].strip().lower(): v
        for v in verifications_col.find({"status": "approved"})
    }

    # Lists for withdrawals
    pending_user_withdrawals = []
    pending_stall_withdrawals = []

    for w in withdrawals_col.find({"status": "pending"}):
        email = w['email'].strip().lower()
        user_type = w.get('user_type')

        withdrawal_data = {
            '_id': str(w['_id']),
            'user_email': email,
            'amount': w.get('amount', 0)
        }

        if user_type == 'stall':
            stall = book_stalls.find_one({"email": email})
            withdrawal_data.update({
                'account_holder': stall.get('account_holder', 'N/A') if stall else 'N/A',
                'account_number': stall.get('account_number', 'N/A') if stall else 'N/A',
                'bank_name': stall.get('bank_name', 'N/A') if stall else 'N/A',
                'branch': stall.get('branch', 'N/A') if stall else 'N/A',
                'ifsc': stall.get('ifsc', 'N/A') if stall else 'N/A',
                'upi': stall.get('upi', 'N/A') if stall else 'N/A',
                'email': email
            })
            pending_stall_withdrawals.append(withdrawal_data)
        else:
            verification = approved_verifications.get(email)
            withdrawal_data.update({
                'account_holder': verification.get('account_holder', 'N/A') if verification else 'N/A',
                'account_number': verification.get('account_number', 'N/A') if verification else 'N/A',
                'bank_name': verification.get('bank_name', 'N/A') if verification else 'N/A',
                'branch': verification.get('branch', 'N/A') if verification else 'N/A',
                'ifsc': verification.get('ifsc', 'N/A') if verification else 'N/A',
                'upi': verification.get('upi', 'N/A') if verification else 'N/A',
                'email': email
            })
            pending_user_withdrawals.append(withdrawal_data)

    return render_template(
        'verifications.html',
        pending_verifications=pending_verifications,
        pending_user_withdrawals=pending_user_withdrawals,
        pending_stall_withdrawals=pending_stall_withdrawals
    )



@app.route('/delete_fitness_test/<test_id>', methods=['POST'])
def delete_fitness_test(test_id):
    try:
        fitness_tests_col.delete_one({'_id': ObjectId(test_id)})
        flash("Fitness test deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting fitness test: {str(e)}", "error")
    return redirect('/create_fitness_test')

@app.route('/image_fitness/<image_id>')
def get_fitness_test_image(image_id):
    image = fs.get(ObjectId(image_id))
    return send_file(image, mimetype=image.content_type)


@app.route('/take_fitness_test/<test_id>')
def take_fitness_test(test_id):
    test = fitness_tests_col.find_one({'_id': ObjectId(test_id)})
    if not test:
        flash("Test not found", "error")
        return redirect('/home')
    return render_template('take_fitness_test.html', test=test)


@app.route('/submit_fitness_test/<test_id>', methods=['POST'])
def submit_fitness_test(test_id):
    test = fitness_tests_col.find_one({'_id': ObjectId(test_id)})

    if not test:
        return "Test not found", 404

    total_questions = int(request.form.get('total_questions', 0))
    user_answers = []
    score = 0

    for i in range(total_questions):
        user_answer = request.form.get(f'q{i}', '').strip().lower()
        correct_answer = test['questions'][i]['answer'].strip().lower()
        user_answers.append(user_answer)

        if user_answer == correct_answer:
            score += 1

    percentage = (score / total_questions) * 100
    is_pass = percentage >= 80

    return render_template(
        'take_fitness_test.html',
        test=test,
        score=score,
        total=total_questions,
        user_answers=user_answers,
        is_pass=is_pass,
        percentage=percentage
    )
@app.route('/delete_bundle', methods=['POST'])
def delete_bundle():
    bundle_id = request.form.get('bundle_id')
    if not bundle_id:
        flash("Bundle ID not provided.", "error")
        return redirect('/admin')

    bundles_col.delete_one({'_id': ObjectId(bundle_id)})
    flash("Bundle deleted successfully.", "success")
    return redirect('/admin')

@app.route('/edit_bundle/<bundle_id>', methods=['GET', 'POST'])
def edit_bundle(bundle_id):
    bundle = bundles_col.find_one({'_id': ObjectId(bundle_id)})
    if not bundle:
        flash("Bundle not found", "error")
        return redirect('/admin')

    if request.method == 'POST':
        name = request.form['bundle_name']
        description = request.form['bundle_description']
        selected_course_ids = request.form.getlist('selected_courses')
        course_object_ids = [ObjectId(cid) for cid in selected_course_ids if cid]

        image_file = request.files.get('bundle_image')
        image_id = bundle.get('image_id')

        if image_file and image_file.filename:
            image_id = fs.put(
                image_file,
                filename=secure_filename(image_file.filename),
                content_type=image_file.content_type
            )

        bundles_col.update_one(
            {'_id': ObjectId(bundle_id)},
            {'$set': {
                'bundle_name': name,
                'description': description,
                'course_ids': course_object_ids,
                'image_id': image_id
            }}
        )
        flash("Bundle updated successfully!", "success")
        return redirect('/admin')

    all_courses = list(courses_col.find())
    return render_template("edit_bundle.html", bundle=bundle, courses=all_courses)


from bson import ObjectId

@app.route('/career')
def career():
    return render_template('careers.html')

@app.route('/image/<image_id>')
def serve_image(image_id):
    try:
        file = fs.get(ObjectId(image_id))  # GridFS file
        return send_file(
            io.BytesIO(file.read()), 
            mimetype=file.content_type, 
            as_attachment=False, 
            download_name=file.filename
        )
    except Exception as e:
        print("Image load error:", e)
        return Response("Image not found", status=404)

@app.route('/delete_course', methods=['POST'])
def delete_course():
    course_id = request.form['course_id']
    courses_col.delete_one({'_id': ObjectId(course_id)})
    flash('Course deleted successfully!', 'success')
    return redirect('/admin')

@app.route('/fitness_test_video/<video_id>')
def get_fitness_test_video(video_id):
    try:
        video = fs.get(ObjectId(video_id))
        return Response(video.read(), mimetype=video.content_type)
    except:
        abort(404)

@app.route('/courses')
def courses():
    all_courses = list(courses_col.find({}))

    for course in all_courses:
        course['_id'] = str(course['_id'])  # Convert _id to string

        # Convert image id too (for /image/<id> route)
        if 'course_image_id' in course:
            course['course_image_id'] = str(course['course_image_id'])
            course['image_url'] = f"/image/{course['course_image_id']}"
        else:
            course['image_url'] = "/static/default.jpg"

    grouped_courses = defaultdict(list)
    for course in all_courses:
        key = course.get('main_section', 'Other')
        grouped_courses[key].append(course)

    return render_template("courses.html", grouped_courses=dict(grouped_courses))


@app.route('/image/<image_id>')
def image(image_id):
    try:
        gridout = fs.get(ObjectId(image_id))
        return Response(gridout.read(), mimetype='image/jpeg')
    except:
        return "Image not found", 404

@app.route('/course_detail/<course_id>')
def course_detail(course_id):
    user_email = session.get('user_email')
    if not user_email:
        flash("Please login to view course details.", "error")
        return redirect(url_for('login'))

    try:
        course_obj_id = ObjectId(course_id)
    except Exception:
        flash("Invalid course ID.", "error")
        return redirect(url_for('home'))

    course = db['courses'].find_one({'_id': course_obj_id})
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for('home'))

    user = db['users'].find_one({'email': user_email})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('login'))

    # Ensure enrollment
    enrolled_courses = user.get('enrolled_courses', [])
    if course_obj_id not in enrolled_courses:
        db['users'].update_one(
            {'email': user_email},
            {'$addToSet': {'enrolled_courses': course_obj_id}}
        )
        db['courses'].update_one(
            {'_id': course_obj_id},
            {
                '$addToSet': {'enrolled_users': user_email},
                '$inc': {'enrollment_count': 1}
            }
        )

    db['enrollments'].update_one(
        {'user_email': user_email, 'course_id': course_obj_id},
        {'$setOnInsert': {
            'video_progress': {},
            'quiz_progress': {},
            'final_exam_progress': {},
            'course_completed': False
        }},
        upsert=True
    )

    enrollment = db['enrollments'].find_one({
        'user_email': user_email,
        'course_id': course_obj_id
    })

    video_progress = enrollment.get('video_progress', {})
    quiz_progress = enrollment.get('quiz_progress', {})
    final_exam_progress = enrollment.get('final_exam_progress', {})

    total_videos = 0
    completed_videos = 0
    all_quizzes_passed = True

    for chapter in course.get('chapters', []):
        chapter_videos = chapter.get('videos', [])
        chapter_total_videos = len(chapter_videos)
        chapter_completed_videos = 0

        for video in chapter_videos:
            total_videos += 1
            file_id = str(video.get('file_id'))
            progress = video_progress.get(file_id, 0)
            video['completed'] = progress >= 90
            if video['completed']:
                completed_videos += 1
                chapter_completed_videos += 1
            else:
                all_quizzes_passed = False  # Cannot pass quiz if a video is incomplete

        # Unlock quiz only if all videos in chapter are completed
        quiz_info = quiz_progress.get(chapter.get('chapter_name', ''), {})
        chapter['quiz_completed'] = quiz_info.get('passed', False)
        chapter['quiz_score'] = quiz_info.get('score', 0)
        chapter['quiz_total'] = quiz_info.get('total', 0)
        chapter['quiz_unlocked'] = (chapter_total_videos > 0 and chapter_completed_videos == chapter_total_videos)

        if not chapter['quiz_completed']:
            all_quizzes_passed = False

    # Final Exam unlock logic
    if 'final_exam' in course:
        course['final_exam_completed'] = final_exam_progress.get('passed', False)
        course['final_exam_score'] = final_exam_progress.get('score', 0)
        course['final_exam_total'] = final_exam_progress.get('total', 0)

        course['final_exam_unlocked'] = (
            completed_videos == total_videos and all_quizzes_passed
        )
    else:
        course['final_exam_completed'] = False
        course['final_exam_unlocked'] = False

    course['video_completion_percent'] = int((completed_videos / total_videos) * 100) if total_videos else 0

    check_course_completion(user_email, course_id)

    return render_template('course_detail.html', course=course)


from flask import Response, request, abort
from bson import ObjectId

@app.route("/video/<video_id>")
def stream_video(video_id):
    try:
        gridout = fs.get(ObjectId(video_id))
        file_size = gridout.length

        range_header = request.headers.get('Range', None)
        if range_header:
            # Parse the byte range from header
            range_match = range_header.strip().split("=")[-1]
            start_str, end_str = range_match.split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1

            if end >= file_size:
                end = file_size - 1

            chunk_size = end - start + 1
            gridout.seek(start)
            data = gridout.read(chunk_size)

            # 206 Partial Content
            rv = Response(data, 206, mimetype="video/mp4")
            rv.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
            rv.headers.add("Accept-Ranges", "bytes")
            rv.headers.add("Content-Length", str(chunk_size))
        else:
            # No Range header → serve whole file
            data = gridout.read()
            rv = Response(data, 200, mimetype="video/mp4")
            rv.headers.add("Content-Length", str(file_size))

        return rv

    except Exception as e:
        print("❌ Error streaming video:", e)
        return "Video not found", 404


@app.route('/enroll/<course_id>', methods=['POST'])
def enroll_course(course_id):
    user_email = session.get('user_email')
    if not user_email:
        flash("Please login to enroll in a course.", "error")
        return redirect(url_for('login'))

    user = db.users.find_one({"email": user_email})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('login'))

    enrolled_courses = user.get('enrolled_courses', [])
    course_obj_id = ObjectId(course_id)

    if course_obj_id not in enrolled_courses:
        enrolled_courses.append(course_obj_id)
        db.users.update_one({"email": user_email}, {"$set": {"enrolled_courses": enrolled_courses}})

        # ✅ Increment the enrollment count
        db.courses.update_one(
            {"_id": course_obj_id},
            {"$inc": {"enrollment_count": 1}}
        )

        flash("Successfully enrolled in the course!", "success")
    else:
        flash("Already enrolled in this course.", "info")

    return redirect(url_for('course_detail', course_id=course_id))



@app.route('/update_progress', methods=['POST'])
def update_progress():
    data = request.get_json()
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Unauthorized'}), 401

    course_id = ObjectId(data['course_id'])
    video_id = str(data['video_id'])
    watched_percent = data.get('watched_percent', 0)

    enrollment = db.enrollments.find_one({'user_email': user_email, 'course_id': course_id})
    if not enrollment:
        return jsonify({'error': 'Enrollment not found'}), 404

    # --- Update progress
    video_progress = enrollment.get('video_progress', {})
    video_progress[video_id] = max(video_progress.get(video_id, 0), watched_percent)

    db.enrollments.update_one(
        {'user_email': user_email, 'course_id': course_id},
        {'$set': {'video_progress': video_progress}}
    )

    course = db.courses.find_one({'_id': course_id})
    chapters = course.get('chapters', [])

    quiz_unlocks = []
    final_exam_unlocked = False

    # --- Check each chapter to unlock quiz
    for chapter in chapters:
        chapter_name = chapter['chapter_name']
        all_videos_completed = True

        for video in chapter.get('videos', []):
            vid_id = str(video['file_id'])
            if video_progress.get(vid_id, 0) < 90:
                all_videos_completed = False
                break

        if all_videos_completed:
            # Unlock quiz if not already in quiz_progress
            enrollment = db.enrollments.find_one({'user_email': user_email, 'course_id': course_id})
            quiz_progress = enrollment.get('quiz_progress', {})
            if chapter_name not in quiz_progress:
                quiz_unlocks.append(chapter_name)

    # --- Check if all chapters are completed
    all_chapters_completed = True
    for chapter in chapters:
        for video in chapter.get('videos', []):
            vid_id = str(video['file_id'])
            if video_progress.get(vid_id, 0) < 90:
                all_chapters_completed = False
                break
        if not all_chapters_completed:
            break

    # --- Check if all quizzes passed (if required)
    quizzes_completed = True
    for chapter in chapters:
        chapter_name = chapter['chapter_name']
        if chapter_name not in enrollment.get('quiz_progress', {}):
            quizzes_completed = False
            break

    # --- Unlock final exam
    if all_chapters_completed and quizzes_completed:
        final_exam_unlocked = True

    return jsonify({
        'message': 'Progress updated',
        'quiz_unlocks': quiz_unlocks,
        'final_exam_unlocked': final_exam_unlocked
    })


from flask import jsonify, send_file

@app.route('/log-download', methods=['POST'])
def log_download():
    data = request.get_json()
    video_id = data.get('video_id')
    course_name = data.get('course_name')
    video_title = data.get('video_title')
    user_email = session.get('user_email', 'Unknown')

    # Save log
    db.video_access_logs.insert_one({
        'user_email': user_email,
        'video_id': video_id,
        'course_name': course_name,
        'video_title': video_title,
        'action': 'download',
        'timestamp': datetime.utcnow()
    })

    return jsonify({"message": "Download logged."}), 200

@app.route('/download-video/<video_id>')
def download_video(video_id):
    try:
        video_file = fs.get(ObjectId(video_id))
        return Response(video_file.read(), mimetype='video/mp4', headers={
            "Content-Disposition": f"attachment; filename=video.mp4"
        })
    except:
        return "Video not found", 404



@app.route('/quiz/<chapter_name>', methods=['GET'])
def render_quiz(chapter_name):
    user_email = session.get('user_email')
    course_id = request.args.get('course_id')

    if not user_email or not course_id:
        return "Unauthorized or missing course ID", 401

    course = courses_col.find_one({'_id': ObjectId(course_id)})
    if not course:
        return "Course not found", 404

    chapter = next((ch for ch in course.get("chapters", []) if ch.get("chapter_name") == chapter_name), None)
    if not chapter or "quiz" not in chapter:
        return "Quiz not found", 404

    return render_template('quiz.html', course_id=course_id, chapter_name=chapter_name, quiz=chapter["quiz"])


@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    user_email = session.get('user_email')
    if not user_email:
        return "Unauthorized", 401

    course_id = request.form.get("course_id")
    chapter_name = request.form.get("chapter_name")
    total_questions = int(request.form.get("total_questions", 0))
    score = 0

    course = courses_col.find_one({"_id": ObjectId(course_id)})
    if not course:
        return "Invalid course", 400

    chapter = next((ch for ch in course.get("chapters", []) if ch.get("chapter_name") == chapter_name), None)
    if not chapter or "quiz" not in chapter:
        return "Quiz not found", 400

    quiz = chapter["quiz"]

    for i in range(total_questions):
        selected = request.form.get(f"q{i}")
        correct = quiz[i]["answer"]
        if selected == correct:
            score += 1

    passed = (score / total_questions) >= 0.8  # 80% passing

    # Save quiz result in separate collection (optional)
    db.quiz_results.insert_one({
        "user_email": user_email,
        "course_id": ObjectId(course_id),
        "chapter_name": chapter_name,
        "score": score,
        "total": total_questions
    })

    # Update progress in enrollments collection
    db['enrollments'].update_one(
        {'user_email': user_email, 'course_id': ObjectId(course_id)},
        {'$set': {f'quiz_progress.{chapter_name}': {'score': score, 'total': total_questions, 'passed': passed}}},
        upsert=True
    )

    return render_template('quiz.html', 
        course_id=course_id, 
        chapter_name=chapter_name, 
        quiz=quiz, 
        score=score, 
        total=total_questions, 
        passed=passed)


@app.route('/exam/<course_id>')
def render_final_exam(course_id):
    user_email = session.get('user_email')
    if not user_email:
        return "Unauthorized", 401

    try:
        course_obj_id = ObjectId(course_id)
    except Exception:
        return "Invalid course ID", 400

    course = courses_col.find_one({'_id': course_obj_id})
    if not course or "final_exam" not in course:
        return "Final exam not found", 404

    enrollment = db['enrollments'].find_one({
        'user_email': user_email,
        'course_id': course_obj_id
    })

    if not enrollment:
        return "You are not enrolled in this course", 403

    # ---- Check Video Completion ----
    video_progress = enrollment.get('video_progress', {})
    total_videos = 0
    completed_videos = 0

    for chapter in course.get('chapters', []):
        for video in chapter.get('videos', []):
            total_videos += 1
            file_id = str(video.get('file_id'))
            if video_progress.get(file_id, 0) >= 90:
                completed_videos += 1

    # ---- Check Quiz Completion ----
    quiz_progress = enrollment.get('quiz_progress', {})
    all_quizzes_passed = all(
        quiz_progress.get(ch['chapter_name'], {}).get('passed', False)
        for ch in course.get('chapters', [])
    )

    if completed_videos < total_videos or not all_quizzes_passed:
        return "Please complete all videos and quizzes before attempting the final exam.", 403

    exam_data = course["final_exam"]
    return render_template('final_exam.html', course_id=course_id, exam=exam_data)



@app.route('/submit_final_exam', methods=['POST'])
def submit_final_exam():
    user_email = session.get('user_email')
    if not user_email:
        return "Unauthorized", 401

    course_id = request.form.get("course_id")
    total_questions = int(request.form.get("total_questions", 0))
    score = 0

    course = courses_col.find_one({"_id": ObjectId(course_id)})
    if not course or "final_exam" not in course:
        return "Invalid course or exam", 400

    exam = course["final_exam"]

    for i in range(total_questions):
        selected = request.form.get(f"q{i}")
        correct = exam[i]["answer"]
        if selected == correct:
            score += 1

    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    retake = percentage < 80

    # Save result in separate collection (optional)
    db.final_exam_results.insert_one({
        "course_id": ObjectId(course_id),
        "user_email": user_email,
        "score": score,
        "total": total_questions
    })

    # Update enrollment progress
    db['enrollments'].update_one(
        {'user_email': user_email, 'course_id': ObjectId(course_id)},
        {'$set': {'final_exam_progress': {'score': score, 'total': total_questions, 'passed': not retake}}},
        upsert=True
    )

    return render_template(
        "final_exam.html",
        course_id=course_id,
        exam=exam,
        score=score,
        total=total_questions,
        retake=retake
    )




@app.route('/get_video_progress', methods=['POST'])
def get_video_progress():
    data = request.json
    user_email = session.get('user_email')
    course_id = data.get('course_id')
    video_id = data.get('video_id')

    if not user_email:
        return jsonify({'error': 'Login required'}), 401

    enrollment = db['enrollments'].find_one({'user_email': user_email, 'course_id': ObjectId(course_id)})

    percent = enrollment.get('video_progress', {}).get(video_id, 0) if enrollment else 0

    return jsonify({'watched_percent': percent})

from bson import ObjectId

@app.route('/course_image/<course_id>')
def course_image(course_id):
    try:
        course = db.courses.find_one({'_id': ObjectId(course_id)})
        if course and 'image' in course:
            image_file = fs.get(course['image'])  # assuming 'image' holds the file_id in GridFS
            return send_file(io.BytesIO(image_file.read()), mimetype=image_file.content_type)
        else:
            return send_file('static/default-course.jpg', mimetype='image/jpeg')
    except Exception as e:
        return send_file('static/default-course.jpg', mimetype='image/jpeg')

@app.route('/user_dashboard')
def user_dashboard():
    user_email = session.get('user_email')
    if not user_email:
        flash("Please login first.", "error")
        return redirect(url_for('login'))

    user = db.users.find_one({'email': user_email})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('login'))

    # Fetch enrollments of the current user
    user_enrollments = list(db.enrollments.find({'user_email': user_email}))

    completed_ids = []
    ongoing_ids = []

    course_progress_map = {}

    for enrollment in user_enrollments:
        course_id = enrollment['course_id']
        course = db.courses.find_one({'_id': course_id})
        if not course:
            continue

        chapters = course.get("chapters", [])
        total_videos = sum(len(ch.get("videos", [])) for ch in chapters)
        completed_videos = sum(
            1 for ch in chapters for v in ch.get("videos", [])
            if enrollment.get("video_progress", {}).get(str(v["file_id"]), 0) >= 90
        )

        total_quizzes = sum(1 for ch in chapters if "quiz" in ch)
        completed_quizzes = sum(
            1 for ch in chapters
            if enrollment.get("quiz_progress", {}).get(ch["chapter_name"], {}).get("passed", False)
        )

        final_exam_passed = enrollment.get("final_exam_progress", {}).get("passed", False)
        final_exam_attempted = "final_exam_progress" in enrollment

        # Calculate individual progresses
        video_progress_percent = int((completed_videos / total_videos) * 100) if total_videos else 0
        quiz_progress_percent = int((completed_quizzes / total_quizzes) * 100) if total_quizzes else 0
        final_exam_percent = 100 if final_exam_passed else 0

        # Overall progress (weighted: 40% videos, 40% quizzes, 20% final exam)
        overall_progress = int(0.4 * video_progress_percent + 0.4 * quiz_progress_percent + 0.2 * final_exam_percent)

        # Save progress in course object
        course['video_progress'] = video_progress_percent
        course['quiz_progress'] = quiz_progress_percent
        course['progress'] = overall_progress

        # Image setup
        if 'course_image_id' in course:
            course['image_url'] = f"/image/{course['course_image_id']}"
        else:
            course['image_url'] = "/static/default.jpg"

        # Sort into completed or ongoing
        if enrollment.get('course_completed'):
            completed_ids.append(course)
        else:
            ongoing_ids.append(course)

    wallet_balance = user.get('wallet_balance', 0)

    latest_receipt = membership_col.find_one(
        {'user_email': user_email},
        sort=[('payment_date', -1)]
    )

    valid_till = latest_receipt['valid_till'] if latest_receipt else None


    return render_template(
        'user_dashboard.html',
        user=user,
        ongoing_courses=ongoing_ids,
        completed_courses=completed_ids,
        referral_code=user.get('ref_code', 'N/A'),
        wallet_balance=wallet_balance,
        valid_till=valid_till
    )

@app.route('/stall_dashboard')
def stall_dashboard():
    user_email = session.get('user_email')
    if not user_email:
        flash("Please login first.", "error")
        return redirect(url_for('login'))

    stall = book_stalls.find_one({'email': user_email})
    if not stall:
        flash("Book Stall account not found.", "error")
        return redirect(url_for('login'))

    referral_code = stall.get("referral_code", "")
    wallet_balance = stall.get("wallet_balance", 0)

    # Find all users who used this referral code
    referred_users = list(db.membership.find({'ref_code': referral_code}))

    # Check verification
    verification_status = stall.get('verified', False)

    return render_template(
        "stall_dashboard.html",
        stall=stall,
        wallet_balance=wallet_balance,
        referral_code=referral_code,
        referred_users=referred_users,
        verified=verification_status
    )


@app.route('/download_receipt')
def download_receipt():
    user_email = session.get('user_email')
    if not user_email:
        flash("Please log in to download your receipt.", "error")
        return redirect(url_for('login'))

    membership = membership_col.find_one({'user_email': user_email})
    if not membership or 'receipt_file_id' not in membership:
        flash("Receipt not found.", "error")
        return redirect(url_for('user_dashboard'))

    receipt_file_id = membership['receipt_file_id']
    fs = gridfs.GridFS(db)

    try:
        file_data = fs.get(receipt_file_id)
        return send_file(
            io.BytesIO(file_data.read()),
            mimetype='application/pdf',
            download_name=f"{membership['receipt_id']}.pdf",
            as_attachment=True
        )
    except Exception as e:
        print("Error downloading receipt:", e)
        flash("Failed to download receipt.", "error")
        return redirect(url_for('user_dashboard'))


def check_course_completion(user_email, course_id):
    enrollment = db.enrollments.find_one({'user_email': user_email, 'course_id': ObjectId(course_id)})
    course = db.courses.find_one({'_id': ObjectId(course_id)})

    if not enrollment or not course:
        return

    videos_total = sum(len(ch.get("videos", [])) for ch in course.get("chapters", []))
    videos_completed = sum(
        1 for ch in course.get("chapters", []) 
        for v in ch.get("videos", []) 
        if enrollment.get("video_progress", {}).get(str(v["file_id"]), 0) >= 90
    )

    quizzes_total = sum(1 for ch in course.get("chapters", []) if "quiz" in ch)
    quizzes_passed = sum(
        1 for ch in course.get("chapters", [])
        if enrollment.get("quiz_progress", {}).get(ch["chapter_name"], {}).get("passed", False)
    )

    final_exam_passed = enrollment.get("final_exam_progress", {}).get("passed", False)

    if (
        videos_total == videos_completed and 
        quizzes_total == quizzes_passed and 
        final_exam_passed
    ):
        db.enrollments.update_one(
            {'_id': enrollment['_id']},
            {'$set': {'course_completed': True}}
        )




@app.route('/api/complete_video', methods=['POST'])
def complete_video():
    data = request.json
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    user = db.users.find_one({'email': user_email})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    try:
        course_id = ObjectId(data['course_id'])
        video_id = data['video_id']
    except:
        return jsonify({"success": False, "message": "Invalid data"}), 400

    enrollment = db.enrollments.find_one({
        'user_email': user_email,
        'course_id': course_id
    })

    if not enrollment:
        return jsonify({"success": False, "message": "Enrollment not found"}), 404

    db.enrollments.update_one(
        {'_id': enrollment['_id']},
        {'$set': {f"video_progress.{video_id}": 100}}
    )

    check_course_completion(user_email, str(course_id))  # assuming this is a custom function

    return jsonify({"success": True, "message": "Video marked as completed."})

@app.route('/logout')
def logout():
    session.clear()  # 🧹 Clear all session variables

    resp = make_response(redirect(url_for('login')))
    # Optional: remove cookies set by your app
    resp.set_cookie('session', '', expires=0)

    return resp

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


from functools import wraps
from flask import make_response

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache

@app.before_request
def restrict_access():
    allowed_paths = ['/', '/login', '/signup', '/static']
    if not session.get('user_email') and not any(request.path.startswith(p) for p in allowed_paths):
        flash("Please login to continue")
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
