import os
from datetime import timedelta

class Config:
    # App
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    
    # Database - Read from environment variable
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            # Handle different database URL formats
            if database_url.startswith('postgres://'):
                # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
                return database_url.replace('postgres://', 'postgresql://')
            elif database_url.startswith('mysql://'):
                # MySQL URLs work as-is with PyMySQL
                return database_url
            else:
                return database_url
        else:
            # Fallback to SQLite for local development
            return 'sqlite:///attendance.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File uploads
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # QR Code
    QR_CODE_DURATION = 15  # minutes
    
    # Face Recognition
    FACE_ENCODING_TOLERANCE = 0.5
    FACE_DETECTION_MODEL = 'hog'  # 'hog' for CPU, 'cnn' for GPU
    
    # Pagination
    ITEMS_PER_PAGE = 10

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    # Production uses environment variables only
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Production-specific settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'app/student_attendance_system/static/assets/uploads'

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}
