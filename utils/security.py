import os
import secrets
from datetime import date, datetime
from functools import wraps

from flask import current_app, flash, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from extensions import db
from models import Blacklist, TimeSlot, User, Visitor


ROLE_DASHBOARDS = {
    "public": "public.dashboard",
    "security": "security.dashboard",
    "staff": "staff.dashboard",
    "principal": "principal.dashboard",
    "management": "management.dashboard",
    "admin": "admin.dashboard",
}


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if user.role not in roles:
                flash("You are not authorized to access that page.", "danger")
                return redirect(url_for(ROLE_DASHBOARDS.get(user.role, "auth.login")))
            return view(*args, **kwargs)

        return wrapper

    return decorator


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]


def save_upload(file, folder_key):
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        raise ValueError("Unsupported file type.")
    os.makedirs(current_app.config[folder_key], exist_ok=True)
    name = secure_filename(file.filename)
    unique_name = f"{secrets.token_hex(8)}_{name}"
    file.save(os.path.join(current_app.config[folder_key], unique_name))
    folder = "profile_photos" if folder_key == "PROFILE_PHOTO_FOLDER" else "uploads"
    return f"{folder}/{unique_name}"


def validate_qr_visit(visitor):
    if not visitor:
        return False, "QR code does not exist."
    public_user = visitor.public_user
    blocked = Blacklist.query.filter(
        (Blacklist.phone == public_user.phone) | (Blacklist.email == public_user.email)
    ).first()
    if blocked:
        return False, "Visitor is blacklisted."
    if visitor.visit_date != date.today():
        return False, "Gatepass is valid only on the visit date."
    slot = TimeSlot.query.filter_by(label=visitor.visit_time, is_active=True).first()
    if not slot:
        return False, "Time slot is no longer valid."
    if visitor.status not in {"pending", "security_approved", "forwarded", "waiting", "authority_approved"}:
        return False, "QR has already been used or closed."
    if visitor.entry_time and visitor.status in {"entered", "completed"}:
        return False, "QR was already used for entry."
    return True, "Valid QR."


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()
