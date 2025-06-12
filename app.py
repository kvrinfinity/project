from collections import defaultdict
import datetime
from email.mime.application import MIMEApplication
from flask import Flask, Response, abort, render_template, request, redirect, url_for, session, flash, jsonify
import os
import random
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
from datetime import datetime
from email.mime.multipart import MIMEMultipart

def generate_otp():
    return str(random.randint(1000, 9999))

def send_otp_email(to_email, otp):
    subject = "Your OTP for Email Verification"
    body = f"Your OTP is: {otp}"
    sender_email = "no-reply@kvrinfinity.in"
        
    sender_password = "dhsa xczp azcg mpbr" 

    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        print('mail has been sent otp is {message}')
    except Exception as e:
        print("Error sending email:", e)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB Setup
uri = "mongodb+srv://nishankamath:kvrinfinity@kvr-test.hax50hy.mongodb.net/?retryWrites=true&w=majority&appName=kvr-testZ"
client = MongoClient(uri)
db = client['company']
courses_col = db['courses']
results_col = db['final_exam_results']
bundles_col = db["bundles"]
users_col = db['users']
fitness_tests_col = db['fitness_test']
fs = GridFS(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == 'admin@kvrinfinity.in' and password == 'admin':
            return redirect(url_for('admin'))

        user = db.users.find_one({"email": email, "password": password})
        if user:
            session['user_email'] = email
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/signup')
def signUp():
    return render_template('signup.html')

@app.route('/membership')
def membership():
    return render_template('membership.html')

@app.route('/payment_success', methods=['POST'])
def payment_success():
    data = request.get_json()
    payment_id = data.get('razorpay_payment_id')
    referral_code = data.get('ref_code')

    # 🔐 Get user details
    user_email = session.get('user_email', 'default@email.com')
    user_name = session.get('user_name', 'Valued Member')

    # 💰 Determine amount
    amount_paid = 3000 if referral_code else 10000

    # 📄 Generate Receipt
    receipt_id = f"KVR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    file_name = f"receipt_{receipt_id}.pdf"
    generate_receipt(
        member_name=user_name,
        email=user_email,
        amount=amount_paid,
        receipt_id=receipt_id
    )

    # 📧 Email Content
    subject = "Payment Successful - KVR Infinity Membership"
    body = f"""Hello {user_name},

Your payment of ₹{amount_paid} was successful!

Membership: All Courses Access  
Receipt ID: {receipt_id}  
Date: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}

Thank you for becoming a premium member of KVR Infinity!

Warm regards,  
KVR Infinity Team
"""

    sender_email = "nishankamath@gmail.com"
    sender_password = "hxui wjwz adsz vycn"

    # 📎 Compose email with attachment
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = user_email
    message.attach(MIMEText(body, 'plain'))

    try:
        with open(file_name, 'rb') as f:
            part = MIMEApplication(f.read(), _subtype='pdf')
            part.add_header('Content-Disposition', 'attachment', filename=file_name)
            message.attach(part)
    except Exception as e:
        print(f"❌ Failed to attach PDF: {e}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, user_email, message.as_string())
        print(f"✅ Email with receipt sent to {user_email}")
    except Exception as e:
        print("❌ Failed to send email:", e)

    return jsonify({"status": "success", "redirect": "/login"})

# 🧾 Generate Receipt PDF (no phone number)
def generate_receipt(member_name, email, amount, receipt_id):
    file_name = f"receipt_{receipt_id}.pdf"
    doc = SimpleDocTemplate(file_name, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    date_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    elements.append(Paragraph("<b>KVR Infinity - Membership Receipt</b>", styles['Title']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Receipt ID: <b>{receipt_id}</b><br/>Date: <b>{date_str}</b>", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [
        ["Field", "Details"],
        ["Name", member_name],
        ["Email", email],
        ["Membership", "All Courses Access"],
        ["Amount Paid", f"₹{amount}"],
    ]

    table = Table(data, hAlign='LEFT', colWidths=[150, 300])
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
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("✅ Thank you for becoming a premium member of <b>KVR Infinity</b>!", styles['Normal']))
    elements.append(Paragraph("This receipt is computer-generated and does not require a signature.", styles['Italic']))

    doc.build(elements)
    print(f"✅ Receipt saved as: {file_name}")

@app.route('/home')
def home():
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

def get_refcode():
    while True:
        code = random.randint(10000, 99999)
        reff_code = 'kvr' + str(code)
        if not db.users.find_one({'ref_code': reff_code}):
            return reff_code

@app.route('/add_user', methods=['POST'])
def add_user():
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('email')
    password = request.form.get('password')

    if db.users.find_one({'email': email}):
        return render_template('signup.html', msg="User already exists")

    ref_code = get_refcode()
    '''db.users.insert_one({
        'fname': fname,
        'lname': lname,
        'email': email,
        'password': password,
        'ref_code': ref_code,
        'enrolled_courses': []
    })'''
    
    otp = generate_otp()
    session['temp_user'] = {'fname': fname, 'lname': lname, 'email': email, 'password': password, 'ref_code': ref_code}
    session['otp'] = otp
    session['user_name'] = fname+' '+lname
    session['user_email'] =email

    send_otp_email(email, otp)
    return render_template('otp_validation.html')
    #return render_template('validation.html')
    #return render_template('membership.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    entered_otp = request.form.get('otp')
    actual_otp = session.get('otp')
    user_data = session.get('temp_user')

    if not actual_otp or not user_data:
        return redirect(url_for('signUp'))

    if entered_otp == actual_otp:
        db.users.insert_one({
            'fname': user_data['fname'],
            'lname': user_data['lname'],
            'email': user_data['email'],
            'password': user_data['password'],
            'ref_code': user_data['ref_code'],
            'enrolled_courses': []
        })

        session.pop('otp')
        session.pop('temp_user')
        session['user_email'] = user_data['email']
        return redirect(url_for('membership'))  # or home page
    else:
        return render_template('otp_validation.html', msg="Incorrect OTP")
    
@app.route('/apply_referral', methods=['POST'])
def apply_referral():
    data = request.get_json()
    ref_code = data.get('ref_code')
    just_validate = data.get('just_validate', False)

    referrer = db.users.find_one({'ref_code': ref_code})
    if referrer:
        if just_validate:
            return jsonify({'valid': True})
    return jsonify({'valid': False})

    


from flask import Flask, render_template, request, redirect, flash, session
from bson import ObjectId
from werkzeug.utils import secure_filename

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # ---------- BUNDLE CREATION ----------
        if 'bundle_name' in request.form:
            bundle_name = request.form['bundle_name']
            bundle_description = request.form.get('bundle_description', '')
            selected_course_ids = request.form.getlist('selected_courses')

            course_object_ids = [ObjectId(cid) for cid in selected_course_ids if cid]

            image_file = request.files['bundle_image']
            if image_file and image_file.filename:
                image_id = fs.put(image_file, filename=secure_filename(image_file.filename), content_type=image_file.content_type)
            else:
                flash("Bundle image is required.", "error")
                return redirect('/admin')

            bundles_col.insert_one({
                'bundle_name': bundle_name,
                'description': bundle_description,
                'course_ids': course_object_ids,
                'image_id': image_id,
            })

            flash('Bundle created successfully!', 'success')
            return redirect('/admin')

        # ---------- COURSE CREATION ----------
        if 'course_name' in request.form:
            course_name = request.form['course_name']
            main_section = request.form['main_section']
            description = request.form.getlist('description[]')

            image_file = request.files['course_image']
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
        if 'test_name' in request.form:
            test_name = request.form['test_name']
            test_image = request.files['test_image']
            if test_image and test_image.filename:
                image_id = fs.put(test_image, filename=secure_filename(test_image.filename), content_type=test_image.content_type)
            else:
                image_id = None

            ft_questions = request.form.getlist('ft_question[]')
            ft_a = request.form.getlist('ft_option_a[]')
            ft_b = request.form.getlist('ft_option_b[]')
            ft_c = request.form.getlist('ft_option_c[]')
            ft_d = request.form.getlist('ft_option_d[]')
            ft_ans = request.form.getlist('ft_answer[]')
            ft_company = request.form.getlist('ft_company[]')

            questions = []
            for q, a, b, c, d, ans, comp in zip(ft_questions, ft_a, ft_b, ft_c, ft_d, ft_ans, ft_company):
                if q:
                    questions.append({
                        'question': q,
                        'options': {'a': a, 'b': b, 'c': c, 'd': d},
                        'answer': ans,
                        'company': comp
                    })

            fitness_tests_col.insert_one({
                'test_name': test_name,
                'image_id': image_id,
                'questions': questions
            })

            flash("Fitness test created successfully!", "success")
            return redirect('/admin')

    # ---------- GET REQUEST ----------
    all_courses = list(courses_col.find())
    all_bundles = list(bundles_col.find())
    all_fitness_tests = list(fitness_tests_col.find())

    # Attach image URLs
    for bundle in all_bundles:
        bundle['image_url'] = f"/image/{bundle['image_id']}" if 'image_id' in bundle else "/static/default.jpg"

    for test in all_fitness_tests:
        test['image_url'] = f"/image/{test['image_id']}" if 'image_id' in test else "/static/default.jpg"

    return render_template(
        'admin.html',
        courses=all_courses,
        bundles=all_bundles,
        fitness_tests=all_fitness_tests
    )

@app.route('/delete_fitness_test/<test_id>', methods=['POST'])
def delete_fitness_test(test_id):
    try:
        fitness_tests_col.delete_one({'_id': ObjectId(test_id)})
        flash("Fitness test deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting fitness test: {str(e)}", "error")
    return redirect('/admin')

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

    return render_template(
        'take_fitness_test.html',
        test=test,
        score=score,
        total=total_questions,
        user_answers=user_answers
    )
@app.route('/delete_bundle/<bundle_id>', methods=['POST'])
def delete_bundle(bundle_id):
    bundle = bundles_col.find_one({'_id': ObjectId(bundle_id)})
    if bundle:
        image_id = bundle.get('image_id')
        if image_id:
            try:
                fs.delete(ObjectId(image_id))
            except:
                pass
        bundles_col.delete_one({'_id': ObjectId(bundle_id)})
        flash("Bundle deleted successfully.", "success")
    else:
        flash("Bundle not found.", "error")
    return redirect('/admin')
from bson import ObjectId


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



@app.route('/admin/edit/<course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    course = courses_col.find_one({'_id': ObjectId(course_id)})
    if not course:
        flash('Course not found.', 'error')
        return redirect('/admin')

    if request.method == 'POST':
        main_section = request.form['main_section']
        course_name = request.form['course_name']
        description = request.form.getlist('description[]')

        # Optional: handle image upload
        if 'course_image' in request.files and request.files['course_image'].filename != '':
            # Delete old image
            if 'course_image_id' in course:
                fs.delete(course['course_image_id'])
            img_file = request.files['course_image']
            img_id = fs.put(img_file, filename=secure_filename(img_file.filename))
            course['course_image_id'] = img_id

        # Update fields
        course['main_section'] = main_section
        course['course_name'] = course_name
        course['description'] = description

        courses_col.replace_one({'_id': course['_id']}, course)
        flash('Course updated successfully.', 'success')
        return redirect('/admin')

    return render_template('edit_course.html', course=course)

@app.route('/admin/edit_quiz/<course_id>', methods=['GET', 'POST'])
def edit_quiz(course_id):
    course = courses_col.find_one({'_id': ObjectId(course_id)})

    if request.method == 'POST':
        questions = []
        num_questions = len(request.form.getlist('question'))

        for i in range(num_questions):
            question_text = request.form.getlist('question')[i]
            options = request.form.getlist(f'option{i}')
            answer = request.form.getlist('answer')[i]

            questions.append({
                'question': question_text,
                'options': options,
                'answer': answer
            })

        courses_col.update_one({'_id': ObjectId(course_id)}, {'$set': {'quiz': questions}})
        flash('Quiz updated successfully.', 'success')
        return redirect('/admin')

    return render_template('edit_quiz.html', course=course)

@app.route('/admin/edit_exam/<course_id>', methods=['GET', 'POST'])
def edit_exam(course_id):
    course = courses_col.find_one({'_id': ObjectId(course_id)})

    if request.method == 'POST':
        final_exam = []
        num_questions = len(request.form.getlist('question'))

        for i in range(num_questions):
            question_text = request.form.getlist('question')[i]
            options = request.form.getlist(f'option{i}')
            answer = request.form.getlist('answer')[i]

            final_exam.append({
                'question': question_text,
                'options': options,
                'answer': answer
            })

        courses_col.update_one({'_id': ObjectId(course_id)}, {'$set': {'final_exam': final_exam}})
        flash('Final exam updated successfully.', 'success')
        return redirect('/admin')

    return render_template('edit_exam.html', course=course)

@app.route('/admin/edit_videos/<course_id>', methods=['GET', 'POST'])
def edit_videos(course_id):
    course = courses_col.find_one({'_id': ObjectId(course_id)})

    if request.method == 'POST':
        chapters = []
        total_chapters = int(request.form.get('total_chapters', 0))

        for i in range(total_chapters):
            chapter_title = request.form.get(f'chapter_title_{i}')
            total_videos = int(request.form.get(f'total_videos_{i}', 0))
            videos = []

            for j in range(total_videos):
                video_title = request.form.get(f'video_title_{i}_{j}')
                video_url = request.form.get(f'video_url_{i}_{j}')
                videos.append({
                    'title': video_title,
                    'url': video_url
                })

            chapters.append({
                'title': chapter_title,
                'videos': videos
            })

        courses_col.update_one({'_id': ObjectId(course_id)}, {'$set': {'chapters': chapters}})
        flash('Videos updated successfully.', 'success')
        return redirect('/admin')

    return render_template('edit_videos.html', course=course)



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

    # Fetch course
    course = db['courses'].find_one({'_id': course_obj_id})
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for('home'))

    # Fetch user
    user = db['users'].find_one({'email': user_email})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('login'))

    # Auto-enroll if not already enrolled
    if course_obj_id not in user.get('enrolled_courses', []):
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

    # Create enrollment record if it doesn't exist
    enrollment = db['enrollments'].find_one({
        'user_email': user_email,
        'course_id': course_obj_id
    })

    if not enrollment:
        enrollment = {
            'user_email': user_email,
            'course_id': course_obj_id,
            'video_progress': {},
            'quiz_progress': {},
            'final_exam_progress': {},
            'course_completed': False
        }
        db['enrollments'].insert_one(enrollment)

    # Fetch updated enrollment
    video_progress = enrollment.get('video_progress', {})
    quiz_progress = enrollment.get('quiz_progress', {})
    final_exam_progress = enrollment.get('final_exam_progress', {})

    # Progress calculation
    total_videos = 0
    completed_videos = 0

    for chapter in course.get('chapters', []):
        for video in chapter.get('videos', []):
            total_videos += 1
            file_id = str(video.get('file_id'))
            progress = video_progress.get(file_id, 0)
            video['completed'] = progress >= 90
            if video['completed']:
                completed_videos += 1

        chapter_name = chapter.get('chapter_name', '')
        quiz_info = quiz_progress.get(chapter_name, {})
        chapter['quiz_completed'] = quiz_info.get('passed', False)
        chapter['quiz_score'] = quiz_info.get('score', 0)
        chapter['quiz_total'] = quiz_info.get('total', 0)

    # Final exam progress
    if 'final_exam' in course:
        course['final_exam_completed'] = final_exam_progress.get('passed', False)
        course['final_exam_score'] = final_exam_progress.get('score', 0)
        course['final_exam_total'] = final_exam_progress.get('total', 0)
    else:
        course['final_exam_completed'] = False

    # Completion percentage
    course['video_completion_percent'] = int((completed_videos / total_videos) * 100) if total_videos else 0
    check_course_completion(user_email, course_id)
    return render_template('course_detail.html', course=course)




@app.route('/video/<video_id>')
def stream_video(video_id):
    try:
        video_file = fs.get(ObjectId(video_id))
        return Response(video_file.read(), mimetype='video/mp4')
    except:
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
    data = request.json
    course_id = data.get('course_id')
    video_id = data.get('video_id')
    watched_percent = data.get('watched_percent')
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({'error': 'Login required'}), 401

    try:
        watched_percent = float(watched_percent)
        if not (0 <= watched_percent <= 100):
            raise ValueError("Invalid percent")
    except:
        return jsonify({'error': 'Invalid watched_percent'}), 400

    # Update progress
    result = db['enrollments'].update_one(
        {'user_email': user_email, 'course_id': ObjectId(course_id)},
        {'$set': {f'video_progress.{video_id}': watched_percent}},
        upsert=True
    )

    # 🟢 Call the check function here
    check_course_completion(user_email, course_id)

    return jsonify({'message': 'Progress updated'})



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

    course = courses_col.find_one({'_id': ObjectId(course_id)})
    if not course or "final_exam" not in course:
        return "Final exam not found", 404

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

    wallet_balance = user.get('wallet', 0)

    return render_template(
        'user_dashboard.html',
        user=user,
        ongoing_courses=ongoing_ids,
        completed_courses=completed_ids,
        referral_code=user.get('ref_code', 'N/A'),
        wallet_balance=wallet_balance
    )



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



if __name__ == '__main__':
    app.run(debug=True)
