from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import base64
import os

from ..extensions import db
from ..models.database import Module, Class, Attendance, Enrollment, User
from ..utils import allowed_file

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

@bp.route('/class/<int:class_id>/qr_code')
@login_required
def generate_qr_code(class_id):
    class_session = Class.query.get_or_404(class_id)
    
    if class_session.module.lecturer_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Generate QR code data
    qr_data = f"attendance:{class_id}:{datetime.utcnow().timestamp()}"
    
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
    
    # Set QR code expiry (15 minutes from now)
    expiry_time = datetime.utcnow() + timedelta(minutes=15)
    class_session.qr_code = qr_data
    class_session.qr_expiry = expiry_time
    db.session.commit()
    
    return jsonify({
        'qr_code': img_str,
        'expiry': expiry_time.isoformat()
    })

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
