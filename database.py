from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timedelta
import sys

# Create the SQLAlchemy instance
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'lecturer' or 'student'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Lecturer(db.Model):
    __tablename__ = 'lecturers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department = db.Column(db.String(100))
    
    user = db.relationship('User', backref='lecturer_profile')
    courses = db.relationship('Course', backref='lecturer', lazy=True)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.String(50), unique=True)
    
    user = db.relationship('User', backref='student_profile')
    courses = db.relationship('Course', secondary='enrollments', back_populates='students')
    attendances = db.relationship('Attendance', backref='student', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=False)
    
    students = db.relationship('Student', secondary='enrollments', back_populates='courses')
    sessions = db.relationship('Session', backref='course', lazy=True)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

class Session(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    allowed_distance_meters = db.Column(db.Integer, nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=False)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, active, past
    
    attendances = db.relationship('Attendance', backref='session', lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(20), default='present')  # present, absent, excused

def init_db(app):
    """Initialize database with app context"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if we need to create demo data
        if User.query.count() == 0:
            create_demo_data()

def create_demo_data():
    """Create demo users and data - Working version"""
    print("Creating demo data...")
    
    try:
        # Create lecturer user
        lecturer_user = User()
        lecturer_user.username = 'lecturer'
        lecturer_user.name = 'Dr. Ricardo Anderson'
        lecturer_user.user_type = 'lecturer'
        lecturer_user.set_password('password123')
        db.session.add(lecturer_user)
        db.session.commit()
        
        # Create lecturer profile
        lecturer = Lecturer()
        lecturer.user_id = lecturer_user.id
        lecturer.department = 'Computer Science'
        db.session.add(lecturer)
        db.session.commit()
        
        # Create student 1
        student_user1 = User()
        student_user1.username = 'student'
        student_user1.name = 'John Doe'
        student_user1.user_type = 'student'
        student_user1.set_password('password123')
        db.session.add(student_user1)
        db.session.commit()
        
        student1 = Student()
        student1.user_id = student_user1.id
        student1.student_id = '620163325'
        db.session.add(student1)
        db.session.commit()
        
        # Create student 2
        student_user2 = User()
        student_user2.username = 'student2'
        student_user2.name = 'Jane Smith'
        student_user2.user_type = 'student'
        student_user2.set_password('password123')
        db.session.add(student_user2)
        db.session.commit()
        
        student2 = Student()
        student2.user_id = student_user2.id
        student2.student_id = '620163326'
        db.session.add(student2)
        db.session.commit()
        
        # Create course 1
        course1 = Course()
        course1.name = 'Software Engineering'
        course1.code = 'COMP2140'
        course1.lecturer_id = lecturer.id
        db.session.add(course1)
        db.session.commit()
        
        # Enroll students in course 1
        enrollment1 = Enrollment(student_id=student1.id, course_id=course1.id)
        enrollment2 = Enrollment(student_id=student2.id, course_id=course1.id)
        db.session.add_all([enrollment1, enrollment2])
        db.session.commit()
        
        # Create sessions for course 1
        # Past session
        session1 = Session()
        session1.course_id = course1.id
        session1.name = 'Introduction to Software Engineering'
        session1.date = date.today() - timedelta(days=2)
        session1.start_time = time(10, 0)
        session1.duration_minutes = 90
        session1.location = 'Computer Lab 3'
        session1.allowed_distance_meters = 100
        session1.lecturer_id = lecturer.id
        session1.status = 'past'
        db.session.add(session1)
        db.session.commit()
        
        # Active session
        session2 = Session()
        session2.course_id = course1.id
        session2.name = 'Requirements Engineering'
        session2.date = date.today()
        session2.start_time = time(14, 0)
        session2.duration_minutes = 90
        session2.location = 'Lecture Hall A'
        session2.allowed_distance_meters = 100
        session2.lecturer_id = lecturer.id
        session2.status = 'active'
        db.session.add(session2)
        db.session.commit()
        
        # Upcoming session
        session3 = Session()
        session3.course_id = course1.id
        session3.name = 'Software Design'
        session3.date = date.today() + timedelta(days=2)
        session3.start_time = time(11, 30)
        session3.duration_minutes = 90
        session3.location = 'Room 101'
        session3.allowed_distance_meters = 100
        session3.lecturer_id = lecturer.id
        session3.status = 'upcoming'
        db.session.add(session3)
        db.session.commit()
        
        # Create attendance for past session
        attendance1 = Attendance()
        attendance1.student_id = student1.id
        attendance1.session_id = session1.id
        attendance1.latitude = 18.0060
        attendance1.longitude = -76.7468
        attendance1.status = 'present'
        db.session.add(attendance1)
        db.session.commit()
        
        # Create course 2
        course2 = Course()
        course2.name = 'Database Systems'
        course2.code = 'COMP2210'
        course2.lecturer_id = lecturer.id
        db.session.add(course2)
        db.session.commit()
        
        # Enroll student 1 in course 2
        enrollment3 = Enrollment(student_id=student1.id, course_id=course2.id)
        db.session.add(enrollment3)
        db.session.commit()
        
        # Create active session for course 2
        session4 = Session()
        session4.course_id = course2.id
        session4.name = 'Introduction to Databases'
        session4.date = date.today()
        session4.start_time = time(9, 0)
        session4.duration_minutes = 90
        session4.location = 'Database Lab'
        session4.allowed_distance_meters = 100
        session4.lecturer_id = lecturer.id
        session4.status = 'active'
        db.session.add(session4)
        db.session.commit()
        
        print("Demo data created successfully!")
        print(f"  - Users: {User.query.count()}")
        print(f"  - Courses: {Course.query.count()}")
        print(f"  - Sessions: {Session.query.count()}")
        print(f"  - Students: {Student.query.count()}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating demo data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)