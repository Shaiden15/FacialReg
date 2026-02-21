#!/usr/bin/env python3
"""
Database migration script for Railway deployment
"""

import os
import sys
from flask import Flask
from flask_migrate import upgrade

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.student_attendance_system import create_app
from app.student_attendance_system.extensions import db

def migrate_database():
    """Run database migrations"""
    app = create_app('production')
    
    with app.app_context():
        try:
            # Create all tables if they don't exist
            db.create_all()
            print("Database tables created successfully!")
            
            # Run migrations if they exist
            try:
                upgrade()
                print("Database migrations completed successfully!")
            except Exception as e:
                print(f"Migration warning: {e}")
                print("Continuing with existing schema...")
                
        except Exception as e:
            print(f"Database setup error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    migrate_database()
