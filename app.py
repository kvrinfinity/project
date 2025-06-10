from collections import defaultdict
from flask import Flask, Response, render_template, request, redirect, url_for, session, flash, jsonify
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

def generate_otp():
    return str(random.randint(1000, 9999))

def send_otp_email(to_email, otp):
    subject = "Your OTP for Email Verification"
    body = f"Your OTP is: {otp}"
    sender_email = "nishankamath@gmail.com"
        
    sender_password = "hxui wjwz adsz vycn" 

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

@app.route('/home')
def home():
    return render_template('home.html')

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

    referrer = db.users.find_one({'ref_code': ref_code})
    if referrer:
        # Update wallet balance
        db.users.update_one(
            {'_id': referrer['_id']},
            {'$inc': {'wallet': 1000}}
        )
        print('valid')
        return jsonify({'valid': True})
    else:
        print('invalid')
        return jsonify({'valid': False})

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        course_name = request.form['course_name']
        main_section = request.form['main_section']

        course_image_file = request.files['course_image']
        image_id = fs.put(course_image_file, filename=secure_filename(course_image_file.filename))

        chapters = []
        chapter_names = request.form.getlist('chapter_name[]')

        for i, chapter_name in enumerate(chapter_names):
            videos = []
            video_titles = request.form.getlist(f'video_title_{i}[]')
            video_files = request.files.getlist(f'video_file_{i}[]')

            for title, video_file in zip(video_titles, video_files):
                if title.strip() and video_file and video_file.filename:
                    file_id = fs.put(video_file, filename=secure_filename(video_file.filename))
                    videos.append({
                        "title": title.strip(),
                        "file_id": file_id
                    })

            quiz_questions = request.form.getlist(f'quiz_question_{i}[]')
            quiz_option_a = request.form.getlist(f'quiz_option_a_{i}[]')
            quiz_option_b = request.form.getlist(f'quiz_option_b_{i}[]')
            quiz_option_c = request.form.getlist(f'quiz_option_c_{i}[]')
            quiz_option_d = request.form.getlist(f'quiz_option_d_{i}[]')
            quiz_answers = request.form.getlist(f'quiz_answer_{i}[]')

            quiz = []
            for q, a, b, c, d, ans in zip(quiz_questions, quiz_option_a, quiz_option_b, quiz_option_c, quiz_option_d, quiz_answers):
                if q.strip():
                    quiz.append({
                        "question": q.strip(),
                        "options": {
                            "a": a.strip(),
                            "b": b.strip(),
                            "c": c.strip(),
                            "d": d.strip()
                        },
                        "answer": ans.strip().lower()
                    })

            chapters.append({
                "chapter_name": chapter_name.strip(),
                "videos": videos,
                "quiz": quiz
            })

        # Final Exam
        final_exam_questions = []
        final_exam_qs = request.form.getlist('final_question[]')
        final_exam_opt_a = request.form.getlist('final_option_a[]')
        final_exam_opt_b = request.form.getlist('final_option_b[]')
        final_exam_opt_c = request.form.getlist('final_option_c[]')
        final_exam_opt_d = request.form.getlist('final_option_d[]')
        final_exam_answers = request.form.getlist('final_answer[]')

        for q, a, b, c, d, ans in zip(final_exam_qs, final_exam_opt_a, final_exam_opt_b, final_exam_opt_c, final_exam_opt_d, final_exam_answers):
            if q.strip():
                final_exam_questions.append({
                    "question": q.strip(),
                    "options": {
                        "a": a.strip(),
                        "b": b.strip(),
                        "c": c.strip(),
                        "d": d.strip()
                    },
                    "answer": ans.strip().lower()
                })

        course_data = {
            "course_name": course_name,
            "main_section": main_section,
            "course_image_id": image_id,
            "chapters": chapters,
            "final_exam": final_exam_questions
        }

        courses_col.insert_one(course_data)
        flash('Course added successfully!', 'success')
        return redirect('/admin')

    return render_template('admin.html')


@app.route('/courses')
def courses():
    all_courses = list(courses_col.find({}))

    for course in all_courses:
        if 'course_image_id' in course:
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

@app.route('/course/<id>')
def course_detail(id):
    if "user_email" not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for("login"))

    user_email = session["user_email"]
    course = courses_col.find_one({"_id": ObjectId(id)})
    if not course:
        return "Course not found", 404

    enrollment = db['enrollments'].find_one({
        'user_email': user_email,
        'course_id': ObjectId(id)
    })

    # Process each chapter
    for chapter in course.get("chapters", []):
        for video in chapter.get("videos", []):
            video_id = str(video.get("file_id"))
            video["stream_url"] = f"/video/{video_id}"
            video['completed'] = False
            if enrollment and enrollment.get("video_progress", {}).get(video_id, 0) >= 90:
                video['completed'] = True

        # Quiz status
        quiz_scores = enrollment.get("quiz_scores", {}) if enrollment else {}
        chapter_name = chapter.get("chapter_name")
        chapter["quiz_completed"] = chapter_name in quiz_scores
        chapter["quiz_score"] = quiz_scores.get(chapter_name)
        chapter["quiz_total"] = len(chapter.get("quiz", []))

    # Final exam score
    course["final_exam"] = course.get("final_exam", [])
    course["final_exam_score"] = enrollment.get("final_exam_score") if enrollment else None

    return render_template("course_detail.html", course=course)


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
    if ObjectId(course_id) not in enrolled_courses:
        enrolled_courses.append(ObjectId(course_id))
        db.users.update_one({"email": user_email}, {"$set": {"enrolled_courses": enrolled_courses}})
        flash("Successfully enrolled in the course!", "success")
    else:
        flash("Already enrolled in this course.", "info")

    # Redirect to course_detail page instead of rendering directly
    return redirect(url_for('course_detail', id=course_id))


@app.route('/update_progress', methods=['POST'])
def update_progress():
    data = request.json
    course_id = data.get('course_id')
    video_id = data.get('video_id')
    watched_percent = data.get('watched_percent')
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({'error': 'Login required'}), 401

    db['enrollments'].update_one(
        {'user_email': user_email, 'course_id': ObjectId(course_id)},
        {'$set': {f'video_progress.{video_id}': watched_percent}},
        upsert=True
    )

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

    # Initial render: no score, no retake flag
    return render_template('final_exam.html', course_id=course_id, exam=course["final_exam"])


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

    enrolled_course_ids = [ObjectId(c) if not isinstance(c, ObjectId) else c for c in user.get('enrolled_courses', [])]
    ongoing_courses = list(db.courses.find({'_id': {'$in': enrolled_course_ids}}))

    for course in ongoing_courses:
        if 'course_image_id' in course:
            course['image_url'] = f"/image/{course['course_image_id']}"
        else:
            course['image_url'] = "/static/default.jpg"

    # Handle wallet balance
    wallet_balance = user.get('wallet', 0)

    return render_template(
        'user_dashboard.html',
        user=user,
        ongoing_courses=ongoing_courses,
        completed_courses=[],  # Replace with your actual completed course logic
        referral_code=user.get('ref_code', 'N/A'),
        wallet_balance=wallet_balance
    )


if __name__ == '__main__':
    app.run(debug=True)
