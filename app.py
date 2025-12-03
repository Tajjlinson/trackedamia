from flask import Flask, render_template, request, jsonify, session as flask_session, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
from database import db, User, Lecturer, Student, Course, Session as SessionModel, Attendance, init_db
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trackademia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with the app
db.init_app(app)

# Initialize database (drops and recreates for development)
init_db(app)

# Authentication middleware
@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in flask_session:
        return redirect(url_for('login'))

# Routes
@app.route('/')
def index():
    user_type = flask_session.get('user_type')
    if user_type == 'lecturer':
        return redirect(url_for('lecturer_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simplified authentication
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            flask_session['user_id'] = user.id
            flask_session['user_type'] = user.user_type
            flask_session['name'] = user.name
            
            if user.user_type == 'lecturer':
                return redirect(url_for('lecturer_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    flask_session.clear()
    return redirect(url_for('login'))

@app.route('/lecturer/dashboard')
def lecturer_dashboard():
    lecturer_id = flask_session.get('user_id')
    user = User.query.get(lecturer_id)
    lecturer = Lecturer.query.filter_by(user_id=lecturer_id).first()
    
    if not lecturer:
        # If no lecturer profile exists, redirect to login
        flask_session.clear()
        return redirect(url_for('login'))
    
    courses = Course.query.filter_by(lecturer_id=lecturer.id).all()
    total_sessions = SessionModel.query.filter_by(lecturer_id=lecturer.id).count()
    
    # Get total students across all courses
    total_students = 0
    for course in courses:
        total_students += len(course.students)
    
    # Get active sessions
    active_sessions = SessionModel.query.filter_by(
        lecturer_id=lecturer.id, 
        status='active'
    ).all()
    
    return render_template('lecturer_dashboard.html', 
                         lecturer=lecturer,
                         courses=courses,
                         total_sessions=total_sessions,
                         total_students=total_students,
                         active_sessions=active_sessions)

@app.route('/student/dashboard')
def student_dashboard():
    # Use flask_session instead of session
    student_id = flask_session.get('user_id')
    user = User.query.get(student_id)
    student = Student.query.filter_by(user_id=student_id).first()
    
    if not student:
        # If no student profile exists, redirect to login
        flask_session.clear()
        return redirect(url_for('login'))
    
    # Get active sessions for student's courses
    active_sessions_list = []
    for course in student.courses:
        for session_obj in course.sessions:
            if session_obj.status == 'active':
                active_sessions_list.append(session_obj)
    
    return render_template('student_dashboard.html', 
                         student=student,
                         active_sessions=active_sessions_list)

@app.route('/lecturer/create-session', methods=['GET', 'POST'])
def create_session():
    lecturer = Lecturer.query.filter_by(user_id=flask_session.get('user_id')).first()
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        session_name = request.form.get('session_name')
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        duration = request.form.get('duration')
        location = request.form.get('location')
        allowed_distance = request.form.get('allowed_distance')
        
        new_session = SessionModel(
            course_id=int(course_id),
            name=session_name,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            start_time=datetime.strptime(start_time, '%H:%M').time(),
            duration_minutes=int(duration),
            location=location,
            allowed_distance_meters=int(allowed_distance),
            lecturer_id=lecturer.id,
            status='upcoming'
        )
        
        db.session.add(new_session)
        db.session.commit()
        
        return redirect(url_for('my_sessions'))
    
    # Get lecturer's courses for dropdown
    courses = Course.query.filter_by(lecturer_id=lecturer.id).all()
    return render_template('create_session.html', courses=courses)

@app.route('/lecturer/my-sessions')
def my_sessions():
    lecturer = Lecturer.query.filter_by(user_id=flask_session.get('user_id')).first()
    
    # Get all sessions for this lecturer
    sessions = SessionModel.query.filter_by(lecturer_id=lecturer.id).order_by(SessionModel.date.desc(), SessionModel.start_time.desc()).all()
    
    # Categorize sessions
    now = datetime.now()
    for session_obj in sessions:
        session_datetime = datetime.combine(session_obj.date, session_obj.start_time)
        end_datetime = session_datetime + timedelta(minutes=session_obj.duration_minutes)
        
        if session_obj.status == 'active':
            if now > end_datetime:
                session_obj.status = 'past'
                db.session.commit()
        elif session_obj.status == 'upcoming':
            if session_datetime <= now <= end_datetime:
                session_obj.status = 'active'
                db.session.commit()
            elif now > end_datetime:
                session_obj.status = 'past'
                db.session.commit()
    
    return render_template('my_sessions.html', sessions=sessions)

@app.route('/api/session/update-status', methods=['POST'])
def update_session_status():
    session_id = request.json.get('session_id')
    new_status = request.json.get('status')
    
    session_obj = SessionModel.query.get(session_id)
    if session_obj:
        session_obj.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

@app.route('/lecturer/manage-students/<int:course_id>')
def manage_students(course_id):
    course = Course.query.get(course_id)
    all_students = Student.query.all()
    
    # Get students not in this course
    available_students = [s for s in all_students if s not in course.students]
    
    return render_template('manage_students.html', 
                         course=course,
                         available_students=available_students)

@app.route('/api/course/add-student', methods=['POST'])
def add_student_to_course():
    course_id = request.json.get('course_id')
    student_id = request.json.get('student_id')
    
    course = Course.query.get(course_id)
    student = Student.query.get(student_id)
    
    if course and student:
        if student not in course.students:
            course.students.append(student)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Student already in course'})
    
    return jsonify({'success': False, 'message': 'Invalid course or student'}), 400

@app.route('/student/mark-attendance')
def mark_attendance():
    student_id = flask_session.get('user_id')
    student = Student.query.filter_by(user_id=student_id).first()
    
    # Get active sessions for student's courses
    active_sessions_list = []
    for course in student.courses:
        for session_obj in course.sessions:
            if session_obj.status == 'active':
                # Check if already marked attendance
                existing = Attendance.query.filter_by(
                    student_id=student.id,
                    session_id=session_obj.id
                ).first()
                
                session_data = {
                    'id': session_obj.id,
                    'name': session_obj.name,
                    'course_name': course.name,
                    'location': session_obj.location,
                    'already_marked': existing is not None,
                    'marked_time': existing.timestamp if existing else None
                }
                active_sessions_list.append(session_data)
    
    return render_template('mark_attendance.html', sessions=active_sessions_list)

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance_api():
    student_id = flask_session.get('user_id')
    student = Student.query.filter_by(user_id=student_id).first()
    session_id = request.json.get('session_id')
    
    # For demo purposes, always approve
    # In real app, you would validate location here
    
    new_attendance = Attendance(
        student_id=student.id,
        session_id=session_id,
        latitude=0.0,
        longitude=0.0,
        status='present'
    )
    
    db.session.add(new_attendance)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/student/attendance-analytics')
def attendance_analytics():
    student_id = flask_session.get('user_id')
    student = Student.query.filter_by(user_id=student_id).first()
    
    # Calculate attendance statistics
    analytics = []
    for course in student.courses:
        # Count only past sessions
        past_sessions = [s for s in course.sessions if s.status == 'past']
        total_sessions = len(past_sessions)
        
        attended_sessions = Attendance.query.filter_by(
            student_id=student.id,
            status='present'
        ).join(SessionModel).filter(SessionModel.course_id == course.id).count()
        
        percentage = (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        analytics.append({
            'course_name': course.name,
            'total_sessions': total_sessions,
            'attended_sessions': attended_sessions,
            'percentage': round(percentage, 1)
        })
    
    return render_template('attendance_analytics.html', analytics=analytics)

@app.route('/admin/dashboard')
def admin_dashboard():
    if flask_session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/add-user', methods=['POST'])
def add_user():
    if flask_session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password')
    user_type = request.form.get('user_type')
    
    if User.query.filter_by(username=username).first():
        return "Username already exists", 400
    
    new_user = User(username=username, name=name, user_type=user_type)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    if user_type == 'student':
        student = Student(user_id=new_user.id, student_id=f"S{new_user.id:05}")
        db.session.add(student)
    elif user_type == 'lecturer':
        lecturer = Lecturer(user_id=new_user.id)
        db.session.add(lecturer)
    
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if flask_session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    user = User.query.get(user_id)
    if user and user.user_type != 'admin':
        if user.user_type == 'student':
            Student.query.filter_by(user_id=user.id).delete()
        elif user.user_type == 'lecturer':
            Lecturer.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
    
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    print("Starting Trackademia application...")
    print("Access the application at: http://localhost:5000")
    print("\nDemo Credentials:")
    print("  Lecturer: username='lecturer', password='password123'")
    print("  Student: username='student', password='password123'")
    print("  Student 2: username='student2', password='password123'")
    app.run(debug=True, port=5000)
