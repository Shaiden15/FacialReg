import os
from . import create_app

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Set up the upload folder if it doesn't exist
    upload_folder = os.path.join('app', 'student_attendance_system', 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask application on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)