import os
from datetime import timedelta

class Config:
    # App
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///attendance.db'
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
    # In production, use environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://') or \
                             'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
