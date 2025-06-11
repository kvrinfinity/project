from collections import defaultdict
import datetime
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
bundles_col = db["bundles"]
users_col = db['users']
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
    # Fetch top 6 courses with enrollment and chapter count
    top_courses = list(courses_col.aggregate([
        {
            "$addFields": {
                "enrollments_count": {
                    "$size": { "$ifNull": ["$enrolled_users", []] }
                },
                "chapters": {
                    "$size": { "$ifNull": ["$chaptername", []] }
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

    # Fetch all bundles (or top N bundles)
    bundles = list(bundles_col.find())  # You can apply sorting/filtering here

    # Add image URL and course count for each bundle
    for bundle in bundles:
        bundle['course_ids'] = bundle.get('course_ids', [])
        bundle['course_count'] = len(bundle['course_ids'])
        if 'image_id' in bundle:
            bundle['image_url'] = f"/image/{bundle['image_id']}"
        else:
            bundle['image_url'] = "/static/default-bundle.png"

    return render_template('home.html', top_courses=top_courses, bundles=bundles)

def update_bundle_progress(user_email, course_id):
    user = users_col.find_one({'email': user_email})
    if not user:
        return

    for bundle_id in user.get('enrolled_bundles', []):
        bundle = bundles_col.find_one({'_id': ObjectId(bundle_id)})
        if course_id in bundle.get('course_ids', []):
            progress = user.get('bundle_progress', {})
            bprog = progress.get(bundle_id, {'completed_courses': 0, 'courses_done': []})
            if course_id not in bprog['courses_done']:
                bprog['courses_done'].append(course_id)
                bprog['completed_courses'] += 1
                progress[bundle_id] = bprog

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

            # Add progress tracking
            progress = user.get('bundle_progress', {})
            progress[bundle_id] = {
                'completed_courses': 0,
                'courses_done': []
            }

            users_col.update_one({'email': user_email}, {
                '$set': {'enrolled_bundles': user['enrolled_bundles'],
                         'bundle_progress': progress}
            })
            flash("Enrolled in bundle!", "success")
    return redirect(url_for('bundle_detail', bundle_id=bundle_id))

@app.route('/bundle/<bundle_id>')
def bundle_detail(bundle_id):
    try:
        # Convert to ObjectId
        bundle_obj_id = ObjectId(bundle_id)
    except:
        flash("Invalid bundle ID", "error")
        return redirect(url_for('home'))

    # Fetch bundle from DB
    bundle = bundles_col.find_one({'_id': bundle_obj_id})
    if not bundle:
        flash("Bundle not found", "error")
        return redirect(url_for('home'))

    # Add image URL for bundle
    bundle['image_url'] = f"/image/{bundle.get('image_id')}" if bundle.get('image_id') else "/static/default-bundle.png"

    # Get all course ObjectIds
    course_ids = bundle.get('course_ids', [])
    course_object_ids = [ObjectId(cid) for cid in course_ids]
    courses = list(courses_col.find({'_id': {'$in': course_object_ids}}))

    # Check user and fetch progress
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

    # Add course info + progress
    for course in courses:
        course['image_url'] = f"/image/{course.get('course_image_id')}" if course.get('course_image_id') else "/static/default.jpg"
        course['chapters_count'] = len(course.get('chapters', []))
        course['enrollments_count'] = len(course.get('enrolled_users', [])) if isinstance(course.get('enrolled_users'), list) else 0

        course_id_str = str(course['_id'])
        completed_chapters = progress.get('courses_done', {}).get(course_id_str, [])
        course['completed_chapters'] = len(completed_chapters)

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

    
@app.route('/payment_success', methods=['POST'])
def payment_success():
    data = request.get_json()
    ref_code = data.get('ref_code')
    razorpay_payment_id = data.get('razorpay_payment_id')

    # (Optional) verify Razorpay payment here via their API

    if ref_code:
        referrer = db.users.find_one({'ref_code': ref_code})
        if referrer:
            db.users.update_one(
                {'_id': referrer['_id']},
                {'$inc': {'wallet': 1000}}
            )
    return jsonify({'success': True})


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

    # ---------- GET Request ----------
    all_courses = list(courses_col.find())
    all_bundles = list(bundles_col.find())

    # Attach image URL to each bundle

    for bundle in all_bundles:
      if 'image_id' in bundle:
        bundle['image_url'] = f"/image/{bundle['image_id']}"
      else:
        bundle['image_url'] = "/static/default.jpg"


    return render_template('admin.html', courses=all_courses, bundles=all_bundles)


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

    for chapter in course.get("chapters", []):
        for video in chapter.get("videos", []):
            video_id = str(video.get("file_id"))
            video["stream_url"] = f"/video/{video_id}"
            video['completed'] = False
            if enrollment and enrollment.get("video_progress", {}).get(video_id, 0) >= 90:
                video['completed'] = True

        # Quiz status
        quiz_scores = enrollment.get("quiz_progress", {}) if enrollment else {}
        chapter_name = chapter.get("chapter_name")
        quiz_data = quiz_scores.get(chapter_name, {})
        chapter["quiz_completed"] = quiz_data.get('passed', False)
        chapter["quiz_score"] = quiz_data.get('score', 0)
        chapter["quiz_total"] = quiz_data.get('total', 0)

    # Final exam status
    final_exam_data = enrollment.get('final_exam_progress', {}) if enrollment else {}
    course["final_exam"] = course.get("final_exam", [])
    course["final_exam_completed"] = final_exam_data.get('passed', False)
    course["final_exam_score"] = final_exam_data.get('score', 0)
    course["final_exam_total"] = final_exam_data.get('total', 0)

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

    # Ongoing Courses
    enrolled_course_ids = [ObjectId(c) if not isinstance(c, ObjectId) else c for c in user.get('enrolled_courses', [])]
    ongoing_courses = list(db.courses.find({'_id': {'$in': enrolled_course_ids}}))

    # Completed Courses
    completed_ids = [ObjectId(c) if not isinstance(c, ObjectId) else c for c in user.get('completed_courses', [])]
    completed_courses = list(db.courses.find({'_id': {'$in': completed_ids}}))

    # Image URLs for both sets
    for course in ongoing_courses + completed_courses:
        if 'course_image_id' in course:
            course['image_url'] = f"/image/{course['course_image_id']}"
        else:
            course['image_url'] = "/static/default.jpg"

    wallet_balance = user.get('wallet', 0)

    return render_template(
        'user_dashboard.html',
        user=user,
        ongoing_courses=ongoing_courses,
        completed_courses=completed_courses,
        referral_code=user.get('ref_code', 'N/A'),
        wallet_balance=wallet_balance
    )


def check_course_completion(user_email, course_id):
    user = db.users.find_one({'email': user_email})
    course = db.courses.find_one({'_id': ObjectId(course_id)})
    enrollment = db.enrollments.find_one({'user_id': user['_id'], 'course_id': ObjectId(course_id)})

    if not course or not enrollment:
        return False

    # 1. Check all videos
    for chapter in course.get("chapters", []):
        for video in chapter.get("videos", []):
            video_id = str(video.get("file_id"))
            if enrollment.get("video_progress", {}).get(video_id, 0) < 90:
                return False

    # 2. Check all quizzes
    for chapter in course.get("chapters", []):
        if chapter.get("quiz"):
            chapter_name = chapter.get("chapter_name")
            if not enrollment.get("quiz_results", {}).get(chapter_name):
                return False

    # 3. Check final exam
    if course.get("final_exam"):
        if not enrollment.get("final_exam_result"):
            return False

    # Mark as completed if not already in list
    if ObjectId(course_id) not in user.get("completed_courses", []):
        db.users.update_one(
            {'_id': user['_id']},
            {'$addToSet': {'completed_courses': ObjectId(course_id)}}
        )
    return True

@app.route('/api/complete_video', methods=['POST'])
def complete_video():
    data = request.json
    user_email = session.get('user_email')

    user = db.users.find_one({'email': user_email})
    enrollment = db.enrollments.find_one({
        'user_id': user['_id'],
        'course_id': ObjectId(data['course_id'])
    })

    db.enrollments.update_one(
        {'_id': enrollment['_id']},
        {'$set': {f"video_progress.{data['video_id']}": 100}}
    )

    check_course_completion(user_email, data['course_id'])

    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
