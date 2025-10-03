from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models.database import User, Module, Enrollment

bp = Blueprint('admin', __name__)

@bp.before_request
@login_required
def check_admin():
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'danger')
        return redirect(url_for('main.dashboard'))

@bp.route('/dashboard')
def dashboard():
    # Get counts for dashboard
    total_students = User.query.filter_by(role='student').count()
    total_lecturers = User.query.filter_by(role='lecturer').count()
    total_modules = Module.query.count()
    
    # Get recent activities (last 5 user registrations)
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_lecturers=total_lecturers,
                         total_modules=total_modules,
                         recent_users=recent_users)

@bp.route('/users')
def list_users():
    role = request.args.get('role', '')
    query = User.query
    
    if role in ['student', 'lecturer', 'admin']:
        query = query.filter_by(role=role)
    
    users = query.order_by(User.role, User.username).all()
    return render_template('admin/users.html', users=users, selected_role=role)

@bp.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '').strip()

        if role not in ['admin', 'lecturer', 'student']:
            flash('Invalid role selected', 'danger')
            return redirect(url_for('admin.add_user'))

        if not username or not email or not password:
            flash('Username, email, and password are required', 'danger')
            return redirect(url_for('admin.add_user'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('A user with that username or email already exists', 'danger')
            return redirect(url_for('admin.add_user'))

        user = User(
            username=username,
            email=email,
            role=role,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/add_user.html')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Only update fields that are provided in the form
        if 'email' in request.form:
            user.email = request.form['email']
        if 'role' in request.form:
            user.role = request.form['role']
        if 'first_name' in request.form:
            user.first_name = request.form['first_name'] or None
        if 'last_name' in request.form:
            user.last_name = request.form['last_name'] or None
        
        # Only update password if a new one is provided
        password = request.form.get('password')
        if password and password.strip():
            user.set_password(password)
        
        try:
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
    
    return render_template('admin/edit_user.html', user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if current_user.id == user_id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.list_users'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.list_users'))

@bp.route('/modules')
def list_modules():
    modules = Module.query.all()
    return render_template('admin/modules.html', modules=modules)

@bp.route('/modules/add', methods=['GET', 'POST'])
def add_module():
    if request.method == 'POST':
        code = request.form.get('code')
        name = request.form.get('name')
        lecturer_id = request.form.get('lecturer_id')
        
        # Validate lecturer exists and is a lecturer
        lecturer = User.query.filter_by(id=lecturer_id, role='lecturer').first()
        if not lecturer:
            flash('Please select a valid lecturer', 'danger')
            return redirect(url_for('admin.add_module'))
        
        # Check if module code already exists
        if Module.query.filter_by(code=code).first():
            flash('A module with this code already exists', 'danger')
            return redirect(url_for('admin.add_module'))
        
        module = Module(code=code, name=name, lecturer_id=lecturer_id)
        db.session.add(module)
        db.session.commit()
        
        flash('Module added successfully!', 'success')
        return redirect(url_for('admin.list_modules'))
    
    # Get all lecturers for the dropdown
    lecturers = User.query.filter_by(role='lecturer').all()
    return render_template('admin/add_module.html', lecturers=lecturers)

@bp.route('/modules/<int:module_id>/edit', methods=['GET', 'POST'])
def edit_module(module_id):
    module = Module.query.get_or_404(module_id)
    
    if request.method == 'POST':
        module.code = request.form.get('code')
        module.name = request.form.get('name')
        lecturer_id = request.form.get('lecturer_id')
        
        # Validate lecturer exists and is a lecturer
        lecturer = User.query.filter_by(id=lecturer_id, role='lecturer').first()
        if not lecturer:
            flash('Please select a valid lecturer', 'danger')
            return redirect(url_for('admin.edit_module', module_id=module_id))
        
        module.lecturer_id = lecturer_id
        db.session.commit()
        
        flash('Module updated successfully!', 'success')
        return redirect(url_for('admin.list_modules'))
    
    # Get all lecturers for the dropdown
    lecturers = User.query.filter_by(role='lecturer').all()
    return render_template('admin/edit_module.html', module=module, lecturers=lecturers)

@bp.route('/modules/<int:module_id>/delete', methods=['POST'])
def delete_module(module_id):
    module = Module.query.get_or_404(module_id)
    db.session.delete(module)
    db.session.commit()
    
    flash('Module deleted successfully!', 'success')
    return redirect(url_for('admin.list_modules'))

@bp.route('/enrollments')
def list_enrollments():
    module_id = request.args.get('module_id', type=int)
    
    query = Enrollment.query
    
    if module_id:
        query = query.filter_by(module_id=module_id)
    
    enrollments = query.all()
    modules = Module.query.all()
    
    return render_template('admin/enrollments.html',
                         enrollments=enrollments,
                         modules=modules,
                         selected_module=module_id)

@bp.route('/enrollments/add', methods=['GET', 'POST'])
def add_enrollment():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        module_id = request.form.get('module_id')
        
        # Check if student exists and is a student
        student = User.query.filter_by(id=student_id, role='student').first()
        if not student:
            flash('Please select a valid student', 'danger')
            return redirect(url_for('admin.add_enrollment'))
        
        # Check if module exists
        module = Module.query.get(module_id)
        if not module:
            flash('Please select a valid module', 'danger')
            return redirect(url_for('admin.add_enrollment'))
        
        # Check if enrollment already exists
        existing = Enrollment.query.filter_by(
            student_id=student_id,
            module_id=module_id
        ).first()
        
        if existing:
            flash('This student is already enrolled in this module', 'danger')
            return redirect(url_for('admin.add_enrollment'))
        
        enrollment = Enrollment(student_id=student_id, module_id=module_id)
        db.session.add(enrollment)
        db.session.commit()
        
        flash('Enrollment added successfully!', 'success')
        return redirect(url_for('admin.list_enrollments'))
    
    # Get all students and modules for the dropdowns
    students = User.query.filter_by(role='student').all()
    modules = Module.query.all()
    
    return render_template('admin/add_enrollment.html',
                         students=students,
                         modules=modules)

@bp.route('/enrollments/<int:enrollment_id>/delete', methods=['POST'])
def delete_enrollment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    db.session.delete(enrollment)
    db.session.commit()
    
    flash('Enrollment deleted successfully!', 'success')
    return redirect(url_for('admin.list_enrollments'))
