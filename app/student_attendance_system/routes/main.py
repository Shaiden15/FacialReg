from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

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
    return render_template('main/index.html')

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
