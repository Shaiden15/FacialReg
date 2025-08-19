from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import base64
try:
    import face_recognition  # heavy optional dependency
    _FACE_LIB_AVAILABLE = True
except Exception:
    face_recognition = None
    _FACE_LIB_AVAILABLE = False

from ..extensions import db
from ..models.database import Enrollment, Class, Attendance, Module, FaceEncoding

bp = Blueprint('student', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get student's enrollments
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    
    # Get upcoming classes
    today = datetime.utcnow().date()
    upcoming_classes = Class.query.join(Enrollment, Class.module_id == Enrollment.module_id).filter(
        Enrollment.student_id == current_user.id,
        Class.date >= today
    ).order_by(Class.date, Class.start_time).limit(5).all()
    
    # Get recent attendance
    recent_attendance = Attendance.query.join(
        Enrollment, Attendance.enrollment_id == Enrollment.id
    ).filter(
        Enrollment.student_id == current_user.id
    ).order_by(
        Attendance.timestamp.desc()
    ).limit(5).all()
    
    return render_template('student/dashboard.html',
                         enrollments=enrollments,
                         upcoming_classes=upcoming_classes,
                         recent_attendance=recent_attendance)

@bp.route('/classes')
@login_required
def list_classes():
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    module_id = request.args.get('module_id', type=int)
    query = Class.query.join(Enrollment, Class.module_id == Enrollment.module_id).filter(
        Enrollment.student_id == current_user.id
    )
    
    if module_id:
        query = query.filter(Class.module_id == module_id)
    
    classes = query.order_by(Class.date.desc(), Class.start_time).all()
    modules = Module.query.join(Enrollment).filter(
        Enrollment.student_id == current_user.id
    ).all()
    
    return render_template('student/classes.html',
                         classes=classes,
                         modules=modules,
                         selected_module=module_id)

@bp.route('/attendance')
@login_required
def view_attendance():
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    module_id = request.args.get('module_id', type=int)
    
    # Get all enrollments for the student
    query = Enrollment.query.filter_by(student_id=current_user.id)
    
    if module_id:
        query = query.filter_by(module_id=module_id)
    
    enrollments = query.all()
    
    # Calculate attendance statistics
    attendance_stats = []
    for enrollment in enrollments:
        total_classes = Class.query.filter_by(module_id=enrollment.module_id).count()
        attended = Attendance.query.join(
            Class, Attendance.class_id == Class.id
        ).filter(
            Attendance.enrollment_id == enrollment.id
        ).count()
        
        percentage = (attended / total_classes * 100) if total_classes > 0 else 0
        
        attendance_stats.append({
            'module': enrollment.module,
            'total_classes': total_classes,
            'attended': attended,
            'percentage': round(percentage, 2)
        })
    
    # Get all modules for the filter dropdown
    modules = Module.query.join(Enrollment).filter(
        Enrollment.student_id == current_user.id
    ).all()
    
    return render_template('student/attendance.html',
                         attendance_stats=attendance_stats,
                         modules=modules,
                         selected_module=module_id)

@bp.route('/scan')
@login_required
def scan_qr():
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('student/scan.html')

@bp.route('/api/face/register', methods=['POST'])
@login_required
def register_face():
    if not _FACE_LIB_AVAILABLE:
        return jsonify({'error': 'Face recognition library is not installed on this server'}), 503
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Load the uploaded image
        image = face_recognition.load_image_file(file)
        encodings = face_recognition.face_encodings(image)
        
        if not encodings:
            return jsonify({'error': 'No face detected in the image'}), 400
        
        # Get the first face encoding
        encoding = encodings[0]
        
        # Save the face encoding to the database
        face_encoding = FaceEncoding.query.filter_by(user_id=current_user.id).first()
        if face_encoding:
            face_encoding.encoding = encoding
        else:
            face_encoding = FaceEncoding(user_id=current_user.id, encoding=encoding)
            db.session.add(face_encoding)
        
        db.session.commit()
        
        return jsonify({'message': 'Face registered successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
