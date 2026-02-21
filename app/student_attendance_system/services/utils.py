import os
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_file(file, folder=''):
    """Save uploaded file to the specified folder"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Create directory if it doesn't exist
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return filepath
    return None
