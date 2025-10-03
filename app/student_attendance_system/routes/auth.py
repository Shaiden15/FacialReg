from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, jsonify
from flask_wtf.csrf import generate_csrf
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import numpy as np
import cv2
import face_recognition
from ..extensions import db, bcrypt

from ..models.database import User
from ..auth.forms import LoginForm, RegistrationForm

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'lecturer':
            return redirect(url_for('lecturer.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirect based on user role
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'lecturer':
                return redirect(url_for('lecturer.dashboard'))
            else:
                return redirect(url_for('student.dashboard'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    # If user is already logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'lecturer':
            return redirect(url_for('lecturer.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    # Clear all session data
    session.clear()
    # Logout the user
    logout_user()
    # Clear any remember me cookies
    response = redirect(url_for('main.index'))
    response.delete_cookie('remember_token')
    return response

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password
        if not check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('auth.change_password'))
            
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('auth.change_password'))
            
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('main.profile'))
    
    return render_template('auth/change_password.html')

@bp.route('/verify-face', methods=['GET', 'POST'])
@login_required
def verify_face():
    # Check if user has face registered
    has_face = hasattr(current_user, 'face_encoding') and current_user.face_encoding is not None
    
    if not has_face:
        flash('You need to register your face before you can edit your profile.', 'warning')
        return redirect(url_for('student.register_face_page'))
    
    if request.method == 'POST':
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No image selected'}), 400
        
        try:
            # Read the image file
            img_bytes = file.read()
            nparr = np.frombuffer(img_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return jsonify({'success': False, 'message': 'Invalid image file'}), 400
            
            # Convert BGR to RGB (face_recognition uses RGB)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_image)
            
            if not face_locations:
                return jsonify({
                    'success': False, 
                    'message': 'No face detected. Please ensure your face is clearly visible and well-lit.'
                })
            
            # Get face encodings
            encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if not encodings:
                return jsonify({
                    'success': False,
                    'message': 'Could not process face. Please try again with better lighting.'
                })
            
            # Get the first face encoding
            encoding = encodings[0]
            
            # Load the stored face encoding
            stored_encoding = np.frombuffer(current_user.face_encoding.encoding, dtype=np.float32)
            
            # Ensure the stored encoding is in the correct shape (128,)
            if stored_encoding.shape != (128,):
                stored_encoding = stored_encoding.reshape(128,)
            
            # Compare faces
            matches = face_recognition.compare_faces([stored_encoding], encoding, tolerance=0.4)
            
            if True in matches:
                # Store verification in session
                session['face_verified'] = True
                session['face_verified_at'] = datetime.utcnow().isoformat()
                return jsonify({
                    'success': True,
                    'message': 'Identity verified successfully!'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Face verification failed. Please try again.'
                })
            
        except Exception as e:
            current_app.logger.error(f"Error in verify_face: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }), 500
    
    return render_template('auth/verify_face.html')

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    # Check if face is verified (within last 5 minutes)
    face_verified = session.get('face_verified', False)
    verified_at = session.get('face_verified_at')
    
    if verified_at:
        verified_time = datetime.fromisoformat(verified_at)
        if (datetime.utcnow() - verified_time).total_seconds() > 300:  # 5 minutes
            face_verified = False
    
    if not face_verified:
        return redirect(url_for('auth.verify_face'))
    
    if request.method == 'POST':
        try:
            # Update user profile
            current_user.first_name = request.form.get('first_name', current_user.first_name)
            current_user.last_name = request.form.get('last_name', current_user.last_name)
            current_user.email = request.form.get('email', current_user.email)
            
            db.session.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('main.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating profile: {str(e)}")
            flash('An error occurred while updating your profile. Please try again.', 'danger')
    
    return render_template('auth/edit_profile.html', title='Edit Profile')
