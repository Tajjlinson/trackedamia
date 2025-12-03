must install in your bash
- pip install flask
- pip install flask-cors
- pip install flask-sqlalchemy
- pip install flask-login

files organization
trackademia/
├── app.py                 # Python Flask backend
├── database.py            # Database setup and models
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css     # CSS styles
│   └── js/
│       └── script.js     # JavaScript functions
└── templates/
    ├── base.html         # Base template
    ├── lecturer_dashboard.html
    ├── student_dashboard.html
    ├── create_session.html
    ├── my_sessions.html
    ├── mark_attendance.html
    ├── attendance_analytics.html
    ├── manage_students.html
    └── login.html
