#!/usr/bin/env python3
"""
Database connection debug script for Railway
"""

import os
import sys
from flask import Flask

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.student_attendance_system import create_app
from app.student_attendance_system.extensions import db

def debug_database():
    """Debug database connection"""
    print("=== Database Connection Debug ===")
    
    # Check environment variables
    database_url = os.environ.get('DATABASE_URL')
    flask_env = os.environ.get('FLASK_ENV')
    railway_env = os.environ.get('RAILWAY_ENVIRONMENT')
    
    print(f"DATABASE_URL: {database_url}")
    print(f"FLASK_ENV: {flask_env}")
    print(f"RAILWAY_ENVIRONMENT: {railway_env}")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables!")
        print("Please check Railway Variables tab.")
        return False
    
    app = create_app('production')
    
    with app.app_context():
        try:
            # Test database connection
            print("\n🔍 Testing database connection...")
            db.engine.execute("SELECT 1")
            print("✅ Database connection successful!")
            
            # Check if tables exist
            print("\n🔍 Checking database tables...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if tables:
                print(f"✅ Found {len(tables)} tables: {', '.join(tables)}")
            else:
                print("⚠️  No tables found. Running migrations...")
                
                # Create tables
                db.create_all()
                print("✅ Tables created successfully!")
                
                # Check again
                tables = inspector.get_table_names()
                print(f"✅ Now have {len(tables)} tables: {', '.join(tables)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

if __name__ == '__main__':
    debug_database()
