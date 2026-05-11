from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, index=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, index=True)
    department = db.Column(db.String(120))
    photo = db.Column(db.String(255))
    college_id = db.Column(db.String(80), unique=True, index=True)
    designation = db.Column(db.String(120))
    course_applied = db.Column(db.String(120))
    is_available = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    visitors = db.relationship("Visitor", backref="public_user", foreign_keys="Visitor.user_id")
    authority_visits = db.relationship("Visitor", backref="authority", foreign_keys="Visitor.authority_id")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TimeSlot(db.Model):
    __tablename__ = "time_slots"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(80), unique=True, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)


class Visitor(db.Model):
    __tablename__ = "visitors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    purpose = db.Column(db.Text, nullable=False)
    visit_date = db.Column(db.Date, nullable=False, index=True)
    visit_time = db.Column(db.String(80), nullable=False)
    authority_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(40), default="pending", index=True)
    visitor_type = db.Column(db.String(80))
    relationship = db.Column(db.String(160))
    student_id = db.Column(db.String(80), index=True)
    student_name = db.Column(db.String(120))
    department = db.Column(db.String(120))
    year_of_study = db.Column(db.String(40))
    parent_name = db.Column(db.String(120))
    guardian_name = db.Column(db.String(120))
    relative_name = db.Column(db.String(120))
    emergency_contact_name = db.Column(db.String(120))
    emergency_contact_phone = db.Column(db.String(30))
    visitor_photo = db.Column(db.String(255))
    id_proof_number = db.Column(db.String(120))
    gender = db.Column(db.String(30))
    address = db.Column(db.Text)
    qr_code = db.Column(db.String(255), unique=True)
    qr_token_hash = db.Column(db.String(255), unique=True, index=True)
    id_proof = db.Column(db.String(255))
    entry_time = db.Column(db.DateTime)
    exit_time = db.Column(db.DateTime)
    is_vip = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitors.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    visitor = db.relationship("Visitor", backref="appointment", uselist=False)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])


class WaitingRoom(db.Model):
    __tablename__ = "waiting_room"

    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitors.id"), nullable=False, unique=True)
    priority = db.Column(db.Integer, default=5)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    visitor = db.relationship("Visitor", backref="waiting_record", uselist=False)


class QRLog(db.Model):
    __tablename__ = "qr_logs"

    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitors.id"), nullable=False, index=True)
    security_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    scan_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(80), nullable=False)
    visitor = db.relationship("Visitor")
    security = db.relationship("User")


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(80), unique=True, index=True)
    student_name = db.Column(db.String(120))
    college_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    course_applied = db.Column(db.String(120))
    course = db.Column(db.String(40))
    admission_year = db.Column(db.Integer)
    batch = db.Column(db.String(20))
    current_year = db.Column(db.String(40))
    department = db.Column(db.String(120))
    address = db.Column(db.Text)
    phone = db.Column(db.String(30))
    qr_code = db.Column(db.String(255), unique=True)
    created_by_staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    photo = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_staff = db.relationship("User")


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    designation = db.Column(db.String(120))
    photo = db.Column(db.String(255))


class Blacklist(db.Model):
    __tablename__ = "blacklist"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(30), index=True)
    email = db.Column(db.String(160), index=True)
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
