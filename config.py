import os
from datetime import timedelta

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Google Maps API Key
    GOOGLE_MAPS_API_KEY = 'AIzaSyB7POzdvk3ri7buWrkOLV7nNZK8pSeOxao'
    
    # Flask-Login configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Email configuration for notifications
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@pilotseverywhere.com'
    
    # Business configuration
    PILOT_SUBSCRIPTION_FEE = 15.0  # Monthly fee for pilots (currently free in beta)
    TRUCKING_DISPATCH_FEE = 20.0   # Per load fee for trucking companies (currently free in beta)
    LOCATION_EXPIRY_HOURS = 48     # Hours before pilot location expires
    
    # Pagination
    ITEMS_PER_PAGE = 25
    
    # File upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size 