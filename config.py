import os
from datetime import timedelta


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'database.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=45)
    WTF_CSRF_TIME_LIMIT = 3600
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    PROFILE_PHOTO_FOLDER = os.path.join(BASE_DIR, "static", "profile_photos")
    QRCODE_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")
    ALLOWED_UPLOAD_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@college.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
