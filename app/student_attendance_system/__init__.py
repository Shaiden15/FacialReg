from flask import Flask
import os
import logging
from .extensions import db, login_manager, bcrypt, migrate, csrf

# Configure SQLAlchemy logging
logging.basicConfig()
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_logger.setLevel(logging.WARNING)  # Only show warnings and errors

def create_app(config_name='default'):
    """Application factory function"""
    app = Flask(__name__)
    
    # Load configuration
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from config.settings import config
    app.config.from_object(config[config_name])
    # Normalize upload folder to absolute path
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'assets', 'uploads')
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Import and register blueprints
    from .routes.auth import bp as auth_blueprint
    from .routes.main import bp as main_blueprint
    from .routes.admin import bp as admin_blueprint
    from .routes.lecturer import bp as lecturer_blueprint
    from .routes.student import bp as student_blueprint
    
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    app.register_blueprint(lecturer_blueprint, url_prefix='/lecturer')
    app.register_blueprint(student_blueprint, url_prefix='/student')
    
    # Import User after db initialization to avoid circular imports
    from .models.database import User
    from datetime import datetime
    
    # Make current year available in all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models.database import User
        return User.query.get(int(user_id))
    
    

    with app.app_context():
        db.create_all()
        # Seed default admin user if not present
        try:
            from .models.database import User
            admin_email = "Admin123@gmail.com"
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(
                    username="admin",
                    email=admin_email,
                    role="admin",
                    first_name="Admin",
                    last_name="User",
                )
                admin.set_password("1234567890")
                db.session.add(admin)
            else:
                # Ensure role and password match requested hardcoded admin
                admin.role = "admin"
                admin.set_password("1234567890")
            db.session.commit()
        except Exception:
            # Avoid crashing app startup if seeding fails; errors will surface in logs
            db.session.rollback()
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500
        
    # Context processors
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}
    
    return app
