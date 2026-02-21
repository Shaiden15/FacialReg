from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import base64
import cv2
import numpy as np
import logging
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden

try:
    import face_recognition  # heavy optional dependency
    _FACE_LIB_AVAILABLE = True
except ImportError as e:
    face_recognition = None
    _FACE_LIB_AVAILABLE = False
    logging.warning(f"Face recognition library not available: {str(e)}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def student_required(f):
    """Decorator to ensure the user has student role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Access denied. Student access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

from ..extensions import db, csrf
from ..models.database import Enrollment, Class, Attendance, Module, FaceEncoding, User

bp = Blueprint('student', __name__)

@bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Check if face is registered
    has_face_registered = FaceEncoding.query.filter_by(user_id=current_user.id).first() is not None
    
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
    
     # Calculate attendance statistics per enrolled module (similar to view_attendance)
    attendance_stats = []
    try:
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
    except Exception as e:
        # If any error occurs, keep stats empty but don't break the dashboard
        logger.warning(f"Error computing attendance_stats for dashboard: {str(e)}")
        attendance_stats = []

    # Build recent activity items for the UI
    def _time_ago(dt):
        try:
            now_dt = datetime.now()
            diff = now_dt - dt
            seconds = int(diff.total_seconds())
            if seconds < 60:
                return f"{seconds}s ago"
            minutes = seconds // 60
            if minutes < 60:
                return f"{minutes}m ago"
            hours = minutes // 60
            if hours < 24:
                return f"{hours}h ago"
            days = hours // 24
            return f"{days}d ago"
        except Exception:
            return "recently"

    recent_activity = []
    try:
        for att in recent_attendance:
            # Safely get related class and module
            try:
                cls = Class.query.get(getattr(att, 'class_id', None))
            except Exception:
                cls = None
            module_obj = getattr(cls, 'module', None) if cls else None
            module_code = getattr(module_obj, 'code', None) or getattr(module_obj, 'name', 'Module') if module_obj else 'Module'
            att_time = getattr(att, 'timestamp', datetime.now())
            status = getattr(att, 'status', 'present')
            recent_activity.append({
                'type': 'attendance',
                'title': 'Attendance Marked',
                'time_ago': _time_ago(att_time),
                'description': f"Marked as {status} for {module_code} on {att_time.strftime('%Y-%m-%d %H:%M')}"
            })
    except Exception as e:
        logger.warning(f"Error building recent_activity for dashboard: {str(e)}")
        recent_activity = []

    return render_template('student/dashboard.html',
                         enrollments=enrollments,
                         upcoming_classes=upcoming_classes,
                         today=datetime.now().date(),
                         now=datetime.now(),
                         has_face_registered=has_face_registered,
                         attendance_stats=attendance_stats,
                         recent_activity=recent_activity)

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
    
    return render_template('student/scan_qr.html')

@bp.route('/scan-qr', methods=['GET', 'POST'])
@login_required
def scan_qr_validation():
    if request.method == 'GET':
        return render_template('student/scan_qr.html')
        
    # Handle POST request
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        if not data or 'qr_data' not in data:
            current_app.logger.error('No QR data provided in request')
            return jsonify({'error': 'No QR data provided'}), 400
        
        current_app.logger.info(f'Processing QR code data: {data["qr_data"]}')
        
        # Parse the QR data (format: attendance:class_id:timestamp)
        try:
            parts = data['qr_data'].split(':')
            if len(parts) != 3 or parts[0] != 'attendance':
                current_app.logger.error(f'Invalid QR code format: {data["qr_data"]}')
                return jsonify({'error': 'Invalid QR code format'}), 400
                
            class_id = int(parts[1])
        except (ValueError, IndexError) as e:
            current_app.logger.error(f'Error parsing QR code data: {str(e)}')
            return jsonify({'error': 'Invalid QR code data'}), 400
            
        # Check if class exists
        try:
            class_session = Class.query.get(class_id)
            if not class_session:
                current_app.logger.error(f'Class not found with ID: {class_id}')
                return jsonify({'error': 'Class not found'}), 404
            
            try:
                # Try to import pytz if available
                try:
                    from pytz import timezone as pytz_timezone
                    import pytz
                    PYTZ_AVAILABLE = True
                except ImportError:
                    PYTZ_AVAILABLE = False
                    current_app.logger.warning('pytz module not available. Using system timezone.')
                
                if PYTZ_AVAILABLE:
                    local_tz = pytz_timezone('Africa/Johannesburg')
                    now_utc = datetime.now(pytz.utc)
                    now_local = now_utc.astimezone(local_tz)
                else:
                    # Fallback to system timezone if pytz is not available
                    now_local = datetime.now()
                    now_utc = now_local  # Will be treated as local time
                    local_tz = None  # No timezone conversion available
                
                # Create a timezone-aware datetime for class start in local time
                if not hasattr(class_session, 'date') or not hasattr(class_session, 'start_time'):
                    current_app.logger.error(f'Class session is missing required date or start_time: {class_session}')
                    return jsonify({'error': 'Invalid class session data'}), 500
                
                class_start = datetime.combine(
                    class_session.date, 
                    class_session.start_time
                )
                
                # Make the class start time timezone-aware if pytz is available
                if PYTZ_AVAILABLE:
                    class_start = local_tz.localize(class_start)
                
                # Calculate the attendance window (class start time to 15 minutes after class start)
                attendance_window_start = class_start
                attendance_window_end = class_start + timedelta(minutes=15)
                
                current_app.logger.info(f'Current time (UTC): {now_utc}')
                current_app.logger.info(f'Current local time: {now_local}')
                current_app.logger.info(f'Class start time (local): {class_start}')
                current_app.logger.info(f'Attendance window starts (local): {attendance_window_start}')
                current_app.logger.info(f'Attendance window ends (local): {attendance_window_end}')
                
                # Check if current time is within the attendance window
                try:
                    if now_local < attendance_window_start:
                        error_msg = f'Too early to mark attendance. Attendance opens at {attendance_window_start.strftime("%I:%M %p")} and closes at {attendance_window_end.strftime("%I:%M %p")}.'
                        current_app.logger.warning(error_msg)
                        return jsonify({'error': error_msg}), 400
                        
                    if now_local > attendance_window_end:
                        error_msg = f'Too late to mark attendance. Attendance window closed at {attendance_window_end.strftime("%I:%M %p")}. Please see your lecturer.'
                        current_app.logger.warning(error_msg)
                        return jsonify({'error': error_msg}), 400
                except TypeError as e:
                    # Handle case where we can't compare timezone-aware and naive datetimes
                    current_app.logger.warning(f'Error comparing times: {str(e)}. Proceeding with attendance check.')
                    
            except Exception as e:
                current_app.logger.error(f'Error processing time-related operations: {str(e)}')
                return jsonify({'error': 'Error processing attendance time window'}), 500
                
            try:
                # Check if student is enrolled in the class
                enrollment = Enrollment.query.filter_by(
                    student_id=current_user.id,
                    module_id=class_session.module_id
                ).first()
                
                if not enrollment:
                    current_app.logger.warning(f'User {current_user.id} not enrolled in module {class_session.module_id}')
                    return jsonify({'error': 'You are not enrolled in this class'}), 403
                    
                # Check if attendance is already marked
                existing_attendance = Attendance.query.filter_by(
                    enrollment_id=enrollment.id,
                    class_id=class_id
                ).first()
                
                if existing_attendance:
                    current_app.logger.info(f'Attendance already marked for user {current_user.id} in class {class_id}')
                    return jsonify({
                        'error': 'Attendance already marked',
                        'status': 'already_marked',
                        'timestamp': existing_attendance.timestamp.isoformat()
                    }), 400
                
                # Get module name safely
                module_name = getattr(class_session, 'module', None)
                module_name = getattr(module_name, 'name', 'Unknown Module') if module_name else 'Unknown Module'
                
                # Prepare response data
                response_data = {
                    'success': True,
                    'class_id': class_id,
                    'class_name': module_name,
                    'class_time': class_session.start_time.strftime('%H:%M'),
                    'class_date': class_session.date.strftime('%Y-%m-%d'),
                    'redirect_url': url_for('student.facial_recognition', class_id=class_id, _external=True)
                }
                
                current_app.logger.info(f'QR code validated successfully: {response_data}')
                return jsonify(response_data)
                
            except Exception as e:
                current_app.logger.error(f'Database error during enrollment check: {str(e)}')
                return jsonify({'error': 'Error processing enrollment'}), 500
                
            except Exception as e:
                current_app.logger.error(f'Unexpected error in scan_qr_validation: {str(e)}', exc_info=True)
                return jsonify({'error': 'An unexpected error occurred'}), 500
        
        except Exception as e:
            current_app.logger.error(f'Error in class session processing: {str(e)}')
            return jsonify({'error': 'Error processing class session'}), 500
            
    except Exception as e:
        current_app.logger.error(f'Unexpected error in scan_qr_validation: {str(e)}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

@bp.route('/verify-face', methods=['POST'])
@login_required
def verify_face():
    current_app.logger.info('=== VERIFY FACE REQUEST ===')
    current_app.logger.info(f'Request form data: {request.form}')
    current_app.logger.info(f'Request files: {request.files}')
    
    if not _FACE_LIB_AVAILABLE:
        error_msg = 'Face recognition library is not installed on this server'
        current_app.logger.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 503
    
    if 'image' not in request.files:
        error_msg = 'No image file in request'
        current_app.logger.error(error_msg)
        return jsonify({'success': False, 'error': 'No image provided'}), 400
    
    class_id = request.form.get('class_id')
    current_app.logger.info(f'Class ID from form: {class_id}')
    if not class_id:
        error_msg = 'No class_id in form data'
        current_app.logger.error(error_msg)
        return jsonify({'success': False, 'error': 'No class ID provided'}), 400
    
    try:
        class_id = int(class_id)
        class_session = Class.query.get_or_404(class_id)
        
        from pytz import timezone
        import pytz
        
        # Get the local timezone
        local_tz = timezone('Africa/Johannesburg')
        
        # Get current time with timezone info
        now_utc = datetime.now(pytz.utc)
        now_local = now_utc.astimezone(local_tz)
        
        # Check if QR code expiry is set and valid
        if not hasattr(class_session, 'qr_expiry') or class_session.qr_expiry is None:
            # If no expiry is set, create one based on class end time (class start + 1 hour)
            class_end_naive = datetime.combine(
                class_session.date,
                class_session.start_time
            ) + timedelta(hours=1)
            qr_expiry = local_tz.localize(class_end_naive)
        else:
            # Make QR expiry timezone-aware
            if class_session.qr_expiry.tzinfo is None:
                # If qr_expiry is naive, localize it
                qr_expiry = local_tz.localize(class_session.qr_expiry)
            else:
                # If already timezone-aware, convert to local timezone
                qr_expiry = class_session.qr_expiry.astimezone(local_tz)
        
        # Check if QR code is still valid
        if now_local > qr_expiry:
            return jsonify({
                'success': False, 
                'error': f'QR code has expired. Expired at {qr_expiry.strftime("%Y-%m-%d %H:%M %Z")}.'
            }), 400
            
        # Create timezone-aware class start time
        class_start_naive = datetime.combine(
            class_session.date, 
            class_session.start_time
        )
        class_start = local_tz.localize(class_start_naive)
        
        # Calculate the attendance window (class start time to 15 minutes after class start)
        attendance_window_start = class_start
        attendance_window_end = class_start + timedelta(minutes=15)
        
        current_app.logger.info(f'[Verify Face] Current local time: {now_local}')
        current_app.logger.info(f'[Verify Face] Class start time: {class_start}')
        current_app.logger.info(f'[Verify Face] Attendance window starts: {attendance_window_start}')
        current_app.logger.info(f'[Verify Face] Attendance window ends: {attendance_window_end}')
        
        # Detailed time comparison logging
        current_app.logger.info(f'[Verify Face] Time Comparison Debug:')
        current_app.logger.info(f'[Verify Face]   now_local < attendance_window_start: {now_local < attendance_window_start}')
        current_app.logger.info(f'[Verify Face]   now_local > attendance_window_end: {now_local > attendance_window_end}')
        current_app.logger.info(f'[Verify Face]   Time difference from window start: {(now_local - attendance_window_start).total_seconds()} seconds')
        current_app.logger.info(f'[Verify Face]   Time difference from window end: {(now_local - attendance_window_end).total_seconds()} seconds')
        
        # Check if current time is within the attendance window
        if now_local < attendance_window_start:
            error_msg = f'Too early to mark attendance. Attendance opens at {attendance_window_start.strftime("%I:%M %p")} and closes at {attendance_window_end.strftime("%I:%M %p")}.'
            current_app.logger.warning(f'[Verify Face] EARLY: {error_msg}')
            current_app.logger.warning(f'[Verify Face] Current time: {now_local}, Window starts: {attendance_window_start}')
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
            
        if now_local > attendance_window_end:
            error_msg = f'Too late to mark attendance. Attendance window closed at {attendance_window_end.strftime("%I:%M %p")}. Please see your lecturer.'
            current_app.logger.warning(f'[Verify Face] LATE: {error_msg}')
            current_app.logger.warning(f'[Verify Face] Current time: {now_local}, Window ends: {attendance_window_end}')
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
            
        current_app.logger.info(f'[Verify Face] Time validation PASSED - current time is within attendance window')
        
        # Check if student is enrolled
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            module_id=class_session.module_id
        ).first()
        
        if not enrollment:
            return jsonify({'success': False, 'error': 'You are not enrolled in this class'}), 403
        
        # Check if attendance is already marked
        existing_attendance = Attendance.query.filter_by(
            enrollment_id=enrollment.id,
            class_id=class_id
        ).first()
        
        if existing_attendance:
            return jsonify({
                'success': False,
                'error': 'Attendance already marked',
                'timestamp': existing_attendance.timestamp.isoformat()
            }), 400
        
        # Get the uploaded image
        file = request.files['image']
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No image file selected'}), 400

        # Verify face
        face_encoding = FaceEncoding.query.filter_by(user_id=current_user.id).first()
        if not face_encoding or not face_encoding.encoding:
            return jsonify({
                'success': False,
                'error': 'No face registered. Please register your face first.'
            }), 400

        try:
            # Read the image file into memory
            img_bytes = file.read()
            if not img_bytes:
                return jsonify({
                    'success': False,
                    'error': 'Could not read image data.'
                }), 400
                
            # Convert to numpy array
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return jsonify({
                    'success': False,
                    'error': 'Could not decode image. Please try again.'
                }), 400

            # Convert from BGR (OpenCV) to RGB (face_recognition)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_img)
            if not face_locations:
                return jsonify({
                    'success': False,
                    'error': 'No face detected. Please make sure your face is clearly visible.'
                }), 400

            # Get face encodings
            try:
                encodings = face_recognition.face_encodings(rgb_img, face_locations)
                current_app.logger.debug(f'Found {len(encodings)} face(s) in the image')
            except Exception as e:
                current_app.logger.error(f'Error in face_recognition.face_encodings: {str(e)}')
                return jsonify({
                    'success': False,
                    'error': 'Error processing face. Please try again.'
                }), 400
                
            if not encodings:
                current_app.logger.warning('No faces found in the image')
                return jsonify({
                    'success': False,
                    'error': 'No face detected. Please ensure your face is clearly visible.'
                }), 400

            # Get the first face encoding
            encoding = encodings[0]
            current_app.logger.debug(f'Face encoding shape: {encoding.shape}, type: {type(encoding)}')
            
            try:
                # Ensure the current encoding is in float32
                try:
                    current_encoding = encoding.astype(np.float32)
                    current_app.logger.debug(f'Current encoding converted to float32: {current_encoding.shape}')
                except Exception as e:
                    current_app.logger.error(f'Error converting encoding to float32: {str(e)}')
                    current_app.logger.error(f'Encoding type: {type(encoding)}, shape: {getattr(encoding, "shape", "N/A")}, dtype: {getattr(encoding, "dtype", "N/A")}')
                    raise
                
                current_app.logger.debug('=== FACE VERIFICATION DEBUG ===')
                current_app.logger.debug(f'Current encoding - shape: {current_encoding.shape}, type: {current_encoding.dtype}, min: {current_encoding.min()}, max: {current_encoding.max()}, mean: {current_encoding.mean()}')
                
                try:
                    # Load the stored encoding
                    if not hasattr(face_encoding, 'encoding') or not face_encoding.encoding:
                        current_app.logger.error('No face encoding found in database')
                        return jsonify({
                            'success': False,
                            'error': 'No registered face found. Please register your face first.'
                        }), 400
                        
                    stored_encoding = np.frombuffer(face_encoding.encoding, dtype=np.float32)
                    current_app.logger.debug(f'Successfully loaded stored encoding: {stored_encoding.shape}')
                    current_app.logger.debug(f'Stored encoding - shape: {stored_encoding.shape}, type: {stored_encoding.dtype}, min: {stored_encoding.min()}, max: {stored_encoding.max()}, mean: {stored_encoding.mean()}')
                except Exception as e:
                    current_app.logger.error(f'Error loading stored encoding: {str(e)}')
                    current_app.logger.error(f'Stored encoding type: {type(face_encoding.encoding)}, length: {len(face_encoding.encoding) if face_encoding.encoding else 0} bytes')
                    return jsonify({
                        'success': False,
                        'error': 'Error loading stored face data. Please re-register your face.'
                    }), 400
                
                # Ensure both encodings have the same dimensions
                try:
                    current_app.logger.debug(f'Before processing - current encoding shape: {current_encoding.shape}, stored encoding shape: {stored_encoding.shape}')
                    
                    if current_encoding.shape != stored_encoding.shape:
                        current_app.logger.warning(f'Encoding dimension mismatch - current: {current_encoding.shape}, stored: {stored_encoding.shape}')
                        
                        # If current encoding is 64D and stored is 128D, pad with zeros
                        if current_encoding.shape[0] == 64 and stored_encoding.shape[0] == 128:
                            current_encoding = np.pad(current_encoding, (0, 64), 'constant')
                            current_app.logger.info('Padded current encoding from 64D to 128D')
                        # If current is 128D and stored is 64D, truncate current to 64D
                        elif current_encoding.shape[0] == 128 and stored_encoding.shape[0] == 64:
                            current_encoding = current_encoding[:64]
                            current_app.logger.info('Truncated current encoding from 128D to 64D')
                        else:
                            error_msg = f'Cannot reconcile encoding dimensions: current {current_encoding.shape}, stored {stored_encoding.shape}'
                            current_app.logger.error(error_msg)
                            return jsonify({
                                'success': False,
                                'error': 'Face verification error. Please re-register your face.',
                                'details': error_msg
                            }), 400
                    
                    current_app.logger.debug(f'After processing - current encoding shape: {current_encoding.shape}, stored encoding shape: {stored_encoding.shape}')
                    
                    # Ensure both are 1D arrays
                    current_encoding = current_encoding.reshape(-1)
                    stored_encoding = stored_encoding.reshape(-1)
                    
                    # Compare faces with tolerance 0.6 (standard for face_recognition)
                    current_app.logger.debug('Starting face comparison...')
                    matches = face_recognition.compare_faces(
                        [stored_encoding],
                        current_encoding,
                        tolerance=0.6
                    )
                    current_app.logger.debug(f'Face comparison result: {matches}')
                    
                except Exception as e:
                    error_msg = f'Error during face verification: {str(e)}'
                    current_app.logger.error(error_msg, exc_info=True)
                    return jsonify({
                        'success': False,
                        'error': 'Error during face verification',
                        'details': str(e)
                    }), 500
                
                if not matches[0]:
                    return jsonify({
                        'success': False,
                        'error': 'Face verification failed. Please try again.'
                    }), 400
                
                # Get current time and class start time
                now = datetime.utcnow()
                class_start = datetime.combine(
                    class_session.date, 
                    class_session.start_time
                )
                
                # Calculate time difference in minutes for status determination
                time_diff = (now - class_start).total_seconds() / 60
                
                # Mark attendance with status based on time
                status = 'present' if time_diff <= 15 else 'late'
                
                attendance = Attendance(
                    enrollment_id=enrollment.id,
                    class_id=class_id,
                    status=status,
                    timestamp=now
                )
                
                db.session.add(attendance)
                db.session.commit()
                
                status_msg = 'on time' if status == 'present' else 'late'
                return jsonify({
                    'success': True,
                    'message': f'Attendance marked successfully! You are marked as {status_msg}.'
                })
                
            except Exception as e:
                current_app.logger.error(f'Face verification error: {str(e)}', exc_info=True)
                return jsonify({
                    'success': False,
                    'error': f'Error during face verification: {str(e)}. Please try again.'
                }), 400
            
        except Exception as e:
            current_app.logger.error(f'Error processing image: {str(e)}')
            return jsonify({
                'success': False,
                'error': 'Error processing the image. Please try again.'
            }), 400
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error in verify_face: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request. Please try again.'
        }), 500

@bp.route('/facial-recognition/<int:class_id>', methods=['GET'])
@login_required
@student_required
def facial_recognition(class_id):
    """Render the facial recognition page for attendance"""
    try:
        # Get the class details
        class_session = Class.query.get_or_404(class_id)
        
        # Check if student is enrolled in this class
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            module_id=class_session.module_id
        ).first_or_404()
        
        # Check if attendance is already marked
        existing_attendance = Attendance.query.filter_by(
            enrollment_id=enrollment.id,
            class_id=class_id
        ).first()
        
        if existing_attendance:
            flash('Your attendance has already been marked for this class.', 'info')
            return redirect(url_for('student.dashboard'))
        
        # Format class time for display
        class_time = class_session.start_time.strftime('%I:%M %p')
        class_date = class_session.date.strftime('%B %d, %Y')
        
        return render_template(
            'student/facial_recognition.html',
            class_id=class_id,
            class_name=class_session.module.name,
            class_time=class_time,
            class_date=class_date
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in facial_recognition route: {str(e)}")
        flash('An error occurred while loading the facial recognition page. Please try again.', 'danger')
        return redirect(url_for('student.dashboard'))

@bp.route('/register-face', methods=['GET'])
@login_required
@student_required
def register_face_page():
    """Render the face registration page"""
    return render_template('student/register_face.html')

@bp.route('/api/face/register', methods=['GET', 'POST'])
@login_required
@student_required
@csrf.exempt
def register_face():
    if request.method == 'GET':
        return redirect(url_for('student.register_face_page'))
    if not _FACE_LIB_AVAILABLE:
        return jsonify({'success': False, 'message': 'Face recognition library is not installed on this server'}), 503
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No image selected'}), 400
    
    try:
        # Read the image file
        img_bytes = file.read()
        
        # Convert bytes to numpy array
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
            }), 400
        
        # Get face encodings
        encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        if not encodings:
            return jsonify({
                'success': False,
                'message': 'Could not process face. Please try again with better lighting.'
            }), 400
        
        # Get the first face encoding and ensure it's float32
        encoding = encodings[0].astype(np.float32)
        
        # Debug logging
        current_app.logger.debug(f'New face encoding shape: {encoding.shape}, type: {encoding.dtype}, sample: {encoding[:5].tolist()}')
        
        # Save the face encoding to the database
        face_encoding = FaceEncoding.query.filter_by(user_id=current_user.id).first()
        if face_encoding:
            face_encoding.encoding = encoding.tobytes()
        else:
            face_encoding = FaceEncoding(user_id=current_user.id, encoding=encoding.tobytes())
            db.session.add(face_encoding)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Face registered successfully!',
            'face_detected': True
        })
    
    except Exception as e:
        logger.error(f"Error in register_face: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500
