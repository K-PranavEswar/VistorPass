import os

from flask import Flask, redirect, session, url_for
from flask_socketio import join_room
from sqlalchemy import inspect, text

from config import Config
from extensions import csrf, db, socketio
from models import Department, Student, Teacher, TimeSlot, User
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.authority import management_bp, principal_bp, staff_bp
from routes.notifications import notifications_bp
from routes.public import public_bp
from routes.security import security_bp
from utils.notifications import unread_count
from utils.security import ROLE_DASHBOARDS, current_user


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    for folder in ("UPLOAD_FOLDER", "PROFILE_PHOTO_FOLDER", "QRCODE_FOLDER"):
        os.makedirs(app.config[folder], exist_ok=True)
    os.makedirs(os.path.join(app.config["QRCODE_FOLDER"], "students"), exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp, url_prefix="/public")
    app.register_blueprint(security_bp, url_prefix="/security")
    app.register_blueprint(staff_bp, url_prefix="/staff")
    app.register_blueprint(principal_bp, url_prefix="/principal")
    app.register_blueprint(management_bp, url_prefix="/management")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    @app.context_processor
    def inject_globals():
        user = current_user()
        return {"current_user": user, "unread_count": unread_count(user.id) if user else 0}

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    @app.route("/")
    def index():
        user = current_user()
        if user:
            return redirect(url_for(ROLE_DASHBOARDS[user.role]))
        return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()
        ensure_schema()
        seed_data(app)

    return app


def seed_data(app):
    admin = User.query.filter(
        (User.username == app.config["ADMIN_USERNAME"])
        | (User.email == app.config["ADMIN_EMAIL"])
        | (User.role == "admin")
    ).first()
    if not admin:
        admin = User(
            name="Super Admin",
            username=app.config["ADMIN_USERNAME"],
            email=app.config["ADMIN_EMAIL"],
            phone="9999999999",
            role="admin",
            designation="Administrator",
            is_active=True,
            college_id="ADM001",
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
    else:
        admin.is_active = True

    if admin and not admin.username:
        admin.name = "Super Admin"
        admin.username = app.config["ADMIN_USERNAME"]
        admin.email = app.config["ADMIN_EMAIL"]
        admin.phone = "9999999999"
        admin.role = "admin"
        admin.is_active = True
        admin.set_password(app.config["ADMIN_PASSWORD"])

    for name in ("Computer Science", "Administration", "Science", "Commerce"):
        if not Department.query.filter_by(name=name).first():
            db.session.add(Department(name=name))

    defaults = [("09:00 - 10:00", "09:00", "10:00"), ("10:00 - 11:00", "10:00", "11:00"), ("14:00 - 15:00", "14:00", "15:00")]
    for label, start, end in defaults:
        if not TimeSlot.query.filter_by(label=label).first():
            db.session.add(TimeSlot(label=label, start_time=start, end_time=end))

    db.session.commit()


def ensure_schema():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "username" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(80)"))
        db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
        db.session.commit()

    if "students" in inspector.get_table_names():
        student_columns = {column["name"] for column in inspector.get_columns("students")}
        student_alters = {
            "student_id": "ALTER TABLE students ADD COLUMN student_id VARCHAR(80)",
            "student_name": "ALTER TABLE students ADD COLUMN student_name VARCHAR(120)",
            "course": "ALTER TABLE students ADD COLUMN course VARCHAR(40)",
            "admission_year": "ALTER TABLE students ADD COLUMN admission_year INTEGER",
            "batch": "ALTER TABLE students ADD COLUMN batch VARCHAR(20)",
            "current_year": "ALTER TABLE students ADD COLUMN current_year VARCHAR(40)",
            "address": "ALTER TABLE students ADD COLUMN address TEXT",
            "qr_code": "ALTER TABLE students ADD COLUMN qr_code VARCHAR(255)",
            "created_by_staff_id": "ALTER TABLE students ADD COLUMN created_by_staff_id INTEGER",
            "created_at": "ALTER TABLE students ADD COLUMN created_at DATETIME",
        }
        changed = False
        for column, statement in student_alters.items():
            if column not in student_columns:
                db.session.execute(text(statement))
                changed = True
        if changed:
            db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_students_student_id ON students (student_id)"))
            db.session.commit()

    if "visitors" in inspector.get_table_names():
        visitor_columns = {column["name"] for column in inspector.get_columns("visitors")}
        visitor_alters = {
            "visitor_type": "ALTER TABLE visitors ADD COLUMN visitor_type VARCHAR(80)",
            "relationship": "ALTER TABLE visitors ADD COLUMN relationship VARCHAR(160)",
            "student_id": "ALTER TABLE visitors ADD COLUMN student_id VARCHAR(80)",
            "student_name": "ALTER TABLE visitors ADD COLUMN student_name VARCHAR(120)",
            "department": "ALTER TABLE visitors ADD COLUMN department VARCHAR(120)",
            "year_of_study": "ALTER TABLE visitors ADD COLUMN year_of_study VARCHAR(40)",
            "parent_name": "ALTER TABLE visitors ADD COLUMN parent_name VARCHAR(120)",
            "guardian_name": "ALTER TABLE visitors ADD COLUMN guardian_name VARCHAR(120)",
            "relative_name": "ALTER TABLE visitors ADD COLUMN relative_name VARCHAR(120)",
            "emergency_contact_name": "ALTER TABLE visitors ADD COLUMN emergency_contact_name VARCHAR(120)",
            "emergency_contact_phone": "ALTER TABLE visitors ADD COLUMN emergency_contact_phone VARCHAR(30)",
            "visitor_photo": "ALTER TABLE visitors ADD COLUMN visitor_photo VARCHAR(255)",
            "id_proof_number": "ALTER TABLE visitors ADD COLUMN id_proof_number VARCHAR(120)",
            "gender": "ALTER TABLE visitors ADD COLUMN gender VARCHAR(30)",
            "address": "ALTER TABLE visitors ADD COLUMN address TEXT",
        }
        changed = False
        for column, statement in visitor_alters.items():
            if column not in visitor_columns:
                db.session.execute(text(statement))
                changed = True
        if changed:
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_visitors_student_id ON visitors (student_id)"))
            db.session.commit()

    db.session.commit()


@socketio.on("connect")
def socket_connect():
    if session.get("user_id"):
        join_room(f"user-{session['user_id']}")


app = create_app()


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
