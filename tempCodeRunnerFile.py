@app.route('/admin', methods=['GET', 'POST'])
def admin():
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

    return render_template(
        'admin.html',
        courses=all_courses,
        bundles=all_bundles,
        fitness_tests=all_fitness_tests
    )