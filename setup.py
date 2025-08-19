from setuptools import setup, find_packages

setup(
    name="student_attendance_system",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        'Flask==2.0.1',
        'Flask-SQLAlchemy==2.5.1',
        'Flask-Login==0.5.0',
        'Flask-WTF==0.15.1',
        'Flask-Migrate==3.1.0',
        'Werkzeug==2.0.1',
        'Pillow==8.3.1',
        'face-recognition==1.3.0',
        'numpy==1.21.1',
        'opencv-python==4.5.3.56',
        'python-dotenv==0.19.0',
        'gunicorn==20.1.0',
        'email-validator==1.1.3'
    ],
    entry_points={
        'console_scripts': [
            'run-app=student_attendance_system.app:app',
        ],
    },
    python_requires='>=3.7',
    author="Your Name",
    author_email="your.email@example.com",
    description="A facial recognition-based student attendance system",
    license="MIT",
    keywords="facial recognition attendance system education",
    entry_points={
        'console_scripts': [
            'run-app=student_attendance_system.app:create_app',
        ],
    },
)
