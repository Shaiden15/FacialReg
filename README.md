# Facial Recognition Attendance System

A Flask-based web application that automates student attendance tracking using facial recognition technology. This system captures student faces, recognizes them, and automatically marks attendance in real-time.

## Features

- **Automated Attendance**: Real-time facial recognition for automatic attendance marking
- **Student Management**: Add, edit, and manage student profiles with face registration
- **Face Registration**: Capture and store student facial data for recognition
- **Attendance Reports**: Generate and view attendance reports with statistics
- **Admin Dashboard**: Comprehensive admin interface for system management
- **Camera Integration**: Live camera feed for face detection and recognition

## Tech Stack

- **Backend**: Flask 2.0.1, SQLAlchemy, Flask-Login
- **Face Recognition**: face-recognition 1.3.0, OpenCV 4.5.3.56
- **Database**: SQLite (configurable for PostgreSQL/MySQL)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Image Processing**: Pillow, NumPy

## Prerequisites

- Python 3.7 or higher
- Webcam/camera for face detection
- Git

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Facial-Reg-Attendance-system-SODM301.git
   cd Facial-Reg-Attendance-system-SODM301
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download face recognition models**
   ```bash
   python download_face_models.py
   ```

5. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

## Usage

1. **Start the application**
   ```bash
   python run.py
   ```

2. **Access the application**
   - Open your browser and navigate to `http://127.0.0.1:5000`
   - Default admin credentials will be created on first run

3. **Setup students**
   - Navigate to the admin dashboard
   - Add students with their information
   - Register their faces using the camera interface

4. **Take attendance**
   - Select the class/course
   - Start the camera feed
   - System automatically detects faces and marks attendance

## Project Structure

```
Facial-Reg-Attendance-system-SODM301/
├── app/
│   ├── student_attendance_system/
│   │   ├── __init__.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── templates/
│   │   └── static/
├── instance/                 # Database files
├── venv/                     # Virtual environment
├── requirements.txt          # Python dependencies
├── run.py                   # Application entry point
├── download_face_models.py  # Model downloader
└── README.md               # This file
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
UPLOAD_FOLDER=app/student_attendance_system/static/uploads
```

### Database Configuration

By default, the app uses SQLite. To use PostgreSQL or MySQL:

```env
# PostgreSQL
DATABASE_URL=postgresql://username:password@localhost/dbname

# MySQL
DATABASE_URL=mysql://username:password@localhost/dbname
```

## API Endpoints

- `GET /` - Home page
- `GET /admin` - Admin dashboard
- `POST /register_student` - Register new student
- `POST /capture_face` - Capture student face
- `POST /mark_attendance` - Mark attendance
- `GET /attendance_report` - View attendance reports

## Face Recognition Process

1. **Face Detection**: Uses OpenCV's Haar cascades to detect faces
2. **Face Encoding**: Converts detected faces to 128-dimensional embeddings
3. **Face Matching**: Compares embeddings with stored student data
4. **Attendance Marking**: Automatically marks attendance for recognized students

## Troubleshooting

### Common Issues

1. **Camera not detected**
   - Ensure camera drivers are installed
   - Check browser permissions for camera access
   - Verify camera is not being used by another application

2. **Face recognition not working**
   - Ensure proper lighting conditions
   - Check if face models are downloaded
   - Verify face data is properly registered

3. **Database errors**
   - Run database migrations: `flask db upgrade`
   - Check database file permissions

### Performance Optimization

- Use GPU acceleration for face recognition (CUDA-compatible systems)
- Optimize image resolution for faster processing
- Limit concurrent camera sessions

## Security Considerations

- Store face data securely with encryption
- Implement proper authentication and authorization
- Regular backup of attendance data
- Compliance with data protection regulations

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [face-recognition library](https://github.com/ageitgey/face_recognition) by Adam Geitgey
- [OpenCV](https://opencv.org/) for computer vision
- [Flask](https://flask.palletsprojects.com/) web framework

## Support

For support and questions:
- Create an issue on GitHub
- Email: your.email@example.com

---

**Note**: This system is designed for educational purposes. Ensure compliance with local privacy laws and regulations when implementing in production environments.
