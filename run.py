import os
from app.student_attendance_system import create_app
from flask_cors import CORS

# Use production config on Railway
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)
CORS(app)