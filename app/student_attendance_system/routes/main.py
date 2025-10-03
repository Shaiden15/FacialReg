import io
import base64
import qrcode
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, session
from flask_login import login_required, current_user
from ..auth.forms import LoginForm, RegistrationForm

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'lecturer':
            return redirect(url_for('lecturer.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    login_form = LoginForm()
    register_form = RegistrationForm()
    return render_template('main/index.html', login_form=login_form, register_form=register_form)

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'lecturer':
        return redirect(url_for('lecturer.dashboard'))
    else:
        return redirect(url_for('student.dashboard'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html')

import random
import string

def generate_random_code(length=7):
    """Generate a random code with uppercase letters and numbers."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@bp.route('/generate-qr', methods=['GET', 'POST'])
@login_required
def generate_qr():
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturer access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    qr_code_data = None
    random_code = None
    
    if request.method == 'POST':
        data = request.form.get('qr_data', '').strip()
        if data:
            # Generate a random 7-digit code with capital letters and numbers
            random_code = generate_random_code(7)
            
            # Combine user data with the random code
            qr_data = f"{data}?code={random_code}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 for displaying in HTML
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            qr_code_data = base64.b64encode(buffered.getvalue()).decode()
            
            # Save the image data and random code in session for download
            session['qr_code_data'] = qr_code_data
            session['qr_random_code'] = random_code
    
    # Get the random code from session if it exists
    random_code = session.get('qr_random_code') if 'qr_random_code' in session else None
    return render_template('main/qr_generator.html', 
                         qr_code_data=qr_code_data,
                         random_code=random_code)

@bp.route('/download-qr')
@login_required
def download_qr():
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturer access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    qr_code_data = session.get('qr_code_data')
    if not qr_code_data:
        abort(400, "No QR code generated yet")
    
    # Convert base64 back to bytes
    qr_img = base64.b64decode(qr_code_data)
    return send_file(
        io.BytesIO(qr_img),
        mimetype='image/png',
        as_attachment=True,
        download_name='qrcode.png'
    )
