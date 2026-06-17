import os

class Config:
    # Flask application secret key
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'auto-assemble-super-secret-key-18273645')
    
    # Database Configuration
    DB_HOST = os.environ.get('DB_HOST', 'db')
    DB_USER = os.environ.get('DB_USER', 'auto_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'auto_pass123')
    DB_NAME = os.environ.get('DB_NAME', 'auto_assemble_db')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    
    # Session options
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with SSL
    SESSION_COOKIE_SAMESITE = 'Lax'
