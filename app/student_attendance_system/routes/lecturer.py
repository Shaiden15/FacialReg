from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, time
import qrcode
from io import BytesIO
import base64
import os

from ..extensions import db
from ..models.database import Module, Class, Attendance, Enrollment, User, db
from ..services.utils import allowed_file

bp = Blueprint('lecturer', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturer access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get lecturer's modules
    modules = Module.query.filter_by(lecturer_id=current_user.id).all()
    
    # Get today's classes
    today = datetime.utcnow().date()
    upcoming_classes = Class.query.join(Module).filter(
        Module.lecturer_id == current_user.id,
        Class.date >= today
    ).order_by(Class.date, Class.start_time).limit(5).all()
    
    return render_template('lecturer/dashboard.html', 
                         modules=modules, 
                         upcoming_classes=upcoming_classes)

@bp.route('/modules')
@login_required
def list_modules():
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturer access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    modules = Module.query.filter_by(lecturer_id=current_user.id).all()
    return render_template('lecturer/modules.html', modules=modules)

@bp.route('/classes')
@login_required
def list_classes():
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturer access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    module_id = request.args.get('module_id', type=int)
    classes = Class.query.join(Module).filter(
        Module.lecturer_id == current_user.id
    )
    
    if module_id:
        classes = classes.filter(Class.module_id == module_id)
    
    classes = classes.order_by(Class.date.desc(), Class.start_time).all()
    modules = Module.query.filter_by(lecturer_id=current_user.id).all()
    
    return render_template('lecturer/classes.html', 
                         classes=classes, 
                         modules=modules,
                         selected_module=module_id)

@bp.route('/class/<int:class_id>/attendance')
@login_required
def view_attendance(class_id):
    class_session = Class.query.get_or_404(class_id)
    
    if class_session.module.lecturer_id != current_user.id:
        flash('You do not have permission to view this class.', 'danger')
        return redirect(url_for('lecturer.list_classes'))
    
    # Get all students enrolled in the module
    enrollments = Enrollment.query.filter_by(module_id=class_session.module_id).all()
    
    # Get attendance records for this class
    attendance_records = {}
    for record in class_session.attendances:
        attendance_records[record.enrollment.student_id] = record
    
    return render_template('lecturer/attendance.html',
                         class_session=class_session,
                         enrollments=enrollments,
                         attendance_records=attendance_records)

@bp.route('/classes/<int:class_id>/qrcode')
@login_required
def generate_qr_code(class_id):
    class_session = Class.query.get_or_404(class_id)
    
    if class_session.module.lecturer_id != current_user.id:
        flash('You are not authorized to generate QR codes for this class', 'danger')
        return redirect(url_for('lecturer.list_classes'))
    
    # Generate QR code data using class's start time
    qr_data = f"attendance:{class_id}:{int(datetime.combine(class_session.date, class_session.start_time).timestamp())}"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to bytes
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Set QR code expiry (15 minutes from class start time)
    class_start_datetime = datetime.combine(class_session.date, class_session.start_time)
    expiry_time = class_start_datetime + timedelta(minutes=15)
    class_session.qr_code = qr_data
    class_session.qr_expiry = expiry_time
    db.session.commit()
    
    # Calculate time remaining
    time_remaining = expiry_time - datetime.utcnow()
    minutes, seconds = divmod(time_remaining.seconds, 60)
    
    return render_template('lecturer/qr_code.html',
                         qr_code=img_str,
                         expiry=expiry_time,
                         time_remaining=f"{minutes}:{seconds:02d}",
                         class_name=f"{class_session.module.code} - {class_session.module.name}",
                         class_session=class_session)

@bp.route('/classes/add', methods=['GET', 'POST'])
@login_required
def add_class():
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturer access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get lecturer's modules for the dropdown
    modules = Module.query.filter_by(lecturer_id=current_user.id).all()
    
    if request.method == 'POST':
        try:
            module_id = request.form.get('module_id')
            class_date = datetime.strptime(request.form.get('class_date'), '%Y-%m-%d').date()
            start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
            end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
            
            # Generate a random 7-character code (uppercase and digits)
            import random
            import string
            qr_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            
            # Set QR expiry to 5 minutes from now
            qr_expiry = datetime.utcnow() + timedelta(minutes=5)
            
            # Create new class
            new_class = Class(
                module_id=module_id,
                date=class_date,
                start_time=start_time,
                end_time=end_time,
                qr_code=qr_code,
                qr_expiry=qr_expiry
            )
            
            db.session.add(new_class)
            db.session.commit()
            
            flash('Class added successfully!', 'success')
            return redirect(url_for('lecturer.list_classes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding class: {str(e)}', 'danger')
    
    return render_template('lecturer/add_class.html', modules=modules)

@bp.route('/api/attendance/scan', methods=['POST'])
@login_required
def scan_attendance():
    if current_user.role != 'student':
        return jsonify({'error': 'Students only'}), 403
    
    data = request.get_json()
    qr_data = data.get('qr_data')
    
    if not qr_data or not qr_data.startswith('attendance:'):
        return jsonify({'error': 'Invalid QR code'}), 400
    
    try:
        _, class_id, _ = qr_data.split(':')
        class_id = int(class_id)
    except (ValueError, IndexError):
        return jsonify({'error': 'Invalid QR code format'}), 400
    
    # Verify class exists and QR code is still valid
    class_session = Class.query.get(class_id)
    if not class_session or class_session.qr_code != qr_data or class_session.qr_expiry < datetime.utcnow():
        return jsonify({'error': 'QR code expired or invalid'}), 400
    
    # Check if student is enrolled in the module
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        module_id=class_session.module_id
    ).first()
    
    if not enrollment:
        return jsonify({'error': 'You are not enrolled in this module'}), 403
    
    # Check if attendance already marked
    existing = Attendance.query.filter_by(
        enrollment_id=enrollment.id,
        class_id=class_id
    ).first()
    
    if existing:
        return jsonify({'message': 'Attendance already marked'}), 200
    
    # Mark attendance
    attendance = Attendance(
        enrollment_id=enrollment.id,
        class_id=class_id,
        status='present'
    )
    
    db.session.add(attendance)
    db.session.commit()
    
    return jsonify({'message': 'Attendance marked successfully'}), 200
