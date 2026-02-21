import os
from app.student_attendance_system import create_app
from flask_cors import CORS

# Use production config on Railway
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)
CORS(app)

if __name__ == "__main__":
    # Set up the upload folder if it doesn't exist
    upload_folder = os.path.join('app', 'student_attendance_system', 'static', 'assets', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask application on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)