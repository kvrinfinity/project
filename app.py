from collections import defaultdict
from flask import Flask, Response, render_template, request, redirect, url_for, session, flash, jsonify
import os
import random
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from gridfs import GridFS
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB Setup
uri = "mongodb+srv://nishankamath:kvrinfinity@kvr-test.hax50hy.mongodb.net/?retryWrites=true&w=majority&appName=kvr-testZ"
client = MongoClient(uri)
db = client['company']
courses_col = db['courses']
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
    db.users.insert_one({
        'fname': fname,
        'lname': lname,
        'email': email,
        'password': password,
        'ref_code': ref_code,
        'enrolled_courses': []
    })

    return render_template('login.html')

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
                if title.strip() and video_file and video_file.filename != '':
                    file_id = fs.put(video_file, filename=secure_filename(video_file.filename))
                    videos.append({
                        "title": title.strip(),
                        "file_id": file_id
                    })

            quiz_questions = request.form.getlist(f'quiz_question_{i}[]')
            quiz_option_a = request.form.getlist(f'quiz_option1_{i}[]')
            quiz_option_b = request.form.getlist(f'quiz_option2_{i}[]')
            quiz_option_c = request.form.getlist(f'quiz_option3_{i}[]')
            quiz_answers = request.form.getlist(f'quiz_answer_{i}[]')

            quiz = []
            for q, a, b, c, ans in zip(quiz_questions, quiz_option_a, quiz_option_b, quiz_option_c, quiz_answers):
                if q.strip():
                    quiz.append({
                        "question": q.strip(),
                        "options": {
                            "a": a.strip(),
                            "b": b.strip(),
                            "c": c.strip()
                        },
                        "answer": ans.strip().lower()
                    })

            chapters.append({
                "chapter_name": chapter_name.strip(),
                "videos": videos,
                "quiz": quiz
            })

        final_exam_questions = []
        final_exam_qs = request.form.getlist('final_exam_question[]')
        final_exam_opt_a = request.form.getlist('final_exam_option_a[]')
        final_exam_opt_b = request.form.getlist('final_exam_option_b[]')
        final_exam_opt_c = request.form.getlist('final_exam_option_c[]')
        final_exam_opt_d = request.form.getlist('final_exam_option_d[]')
        final_exam_answers = request.form.getlist('final_exam_answer[]')

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
    try:
        course = courses_col.find_one({"_id": ObjectId(id)})
        if not course:
            return "Course not found", 404

        if 'course_image_id' in course:
            course['image_url'] = f"/image/{course['course_image_id']}"

        for chapter in course.get('chapters', []):
            for video in chapter.get('videos', []):
                video['stream_url'] = f"/video/{video['file_id']}"

        return render_template("course_detail.html", course=course)
    except Exception as e:
        return f"Error: {e}", 500

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

    # ✅ Directly render the course_detail page
    course = courses_col.find_one({"_id": ObjectId(course_id)})
    if not course:
        return "Course not found", 404

    if 'course_image_id' in course:
        course['image_url'] = f"/image/{course['course_image_id']}"

    for chapter in course.get('chapters', []):
        for video in chapter.get('videos', []):
            video['stream_url'] = f"/video/{video['file_id']}"

    return render_template("course_detail.html", course=course)


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

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json
    course_id = data.get('course_id')
    chapter_name = data.get('chapter_name')
    score = data.get('score')
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({'error': 'Login required'}), 401

    db['enrollments'].update_one(
        {'user_email': user_email, 'course_id': ObjectId(course_id)},
        {'$set': {f'quiz_scores.{chapter_name}': score}},
        upsert=True
    )
    return jsonify({'message': 'Quiz score saved'})

@app.route('/submit_final_exam', methods=['POST'])
def submit_final_exam():
    data = request.json
    course_id = data.get('course_id')
    score = data.get('score')
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({'error': 'Login required'}), 401

    db['enrollments'].update_one(
        {'user_email': user_email, 'course_id': ObjectId(course_id)},
        {'$set': {'final_exam_score': score}},
        upsert=True
    )
    return jsonify({'message': 'Final exam score saved'})

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

if __name__ == '__main__':
    app.run(debug=True)
