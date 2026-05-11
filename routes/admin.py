from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Appointment, Blacklist, Department, Notification, QRLog, Student, TimeSlot, User, Visitor, WaitingRoom
from utils.security import roles_required, save_upload

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@roles_required("admin")
def dashboard():
    today = date.today()
    stats = {
        "daily": Visitor.query.filter_by(visit_date=today).count(),
        "approved": Visitor.query.filter(Visitor.status.in_(["authority_approved", "entered", "completed"])).count(),
        "rejected": Visitor.query.filter_by(status="rejected").count(),
        "users": User.query.count(),
    }
    visitors_by_status = db.session.query(Visitor.status, db.func.count(Visitor.id)).group_by(Visitor.status).all()
    return render_template("admin/dashboard.html", stats=stats, visitors_by_status=visitors_by_status)


@admin_bp.route("/users", methods=["GET", "POST"])
@roles_required("admin")
def users():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("admin.users"))
        try:
            photo = save_upload(request.files.get("photo"), "PROFILE_PHOTO_FOLDER")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin.users"))
        user = User(
            name=request.form["name"],
            username=request.form.get("username") or None,
            email=email,
            phone=request.form["phone"],
            role=request.form["role"],
            department=request.form.get("department"),
            college_id=request.form.get("college_id") or None,
            designation=request.form.get("designation"),
            photo=photo,
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("admin.users"))
    users = User.query.order_by(User.created_at.desc()).all()
    departments = Department.query.order_by(Department.name).all()
    return render_template("admin/users.html", users=users, departments=departments)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    if user.role == "admin":
        user.is_active = True
        db.session.commit()
        flash("Admin accounts cannot be deleted.", "warning")
        return redirect(url_for("admin.users"))

    visitor_ids = [
        visitor.id
        for visitor in Visitor.query.filter((Visitor.user_id == user.id) | (Visitor.authority_id == user.id)).all()
    ]
    if visitor_ids:
        QRLog.query.filter(QRLog.visitor_id.in_(visitor_ids)).delete(synchronize_session=False)
        WaitingRoom.query.filter(WaitingRoom.visitor_id.in_(visitor_ids)).delete(synchronize_session=False)
        Appointment.query.filter(Appointment.visitor_id.in_(visitor_ids)).delete(synchronize_session=False)
        Visitor.query.filter(Visitor.id.in_(visitor_ids)).delete(synchronize_session=False)

    QRLog.query.filter_by(security_id=user.id).delete(synchronize_session=False)
    Notification.query.filter(
        (Notification.sender_id == user.id) | (Notification.receiver_id == user.id)
    ).delete(synchronize_session=False)
    Student.query.filter_by(created_by_staff_id=user.id).update(
        {"created_by_staff_id": None}, synchronize_session=False
    )

    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/departments", methods=["GET", "POST"])
@roles_required("admin")
def departments():
    if request.method == "POST":
        db.session.add(Department(name=request.form["name"]))
        db.session.commit()
        flash("Department added.", "success")
        return redirect(url_for("admin.departments"))
    return render_template("admin/departments.html", departments=Department.query.order_by(Department.name).all())


@admin_bp.route("/timeslots", methods=["GET", "POST"])
@roles_required("admin")
def timeslots():
    if request.method == "POST":
        db.session.add(TimeSlot(label=request.form["label"], start_time=request.form["start_time"], end_time=request.form["end_time"]))
        db.session.commit()
        flash("Time slot added.", "success")
        return redirect(url_for("admin.timeslots"))
    return render_template("admin/timeslots.html", slots=TimeSlot.query.order_by(TimeSlot.start_time).all())


@admin_bp.route("/blacklist", methods=["GET", "POST"])
@roles_required("admin")
def blacklist():
    if request.method == "POST":
        db.session.add(Blacklist(phone=request.form.get("phone"), email=request.form.get("email"), reason=request.form["reason"]))
        db.session.commit()
        flash("Blacklist record added.", "warning")
        return redirect(url_for("admin.blacklist"))
    return render_template("admin/blacklist.html", records=Blacklist.query.order_by(Blacklist.created_at.desc()).all())


@admin_bp.route("/logs")
@roles_required("admin")
def logs():
    return render_template("admin/logs.html", visitors=Visitor.query.order_by(Visitor.created_at.desc()).all(), qr_logs=QRLog.query.order_by(QRLog.scan_time.desc()).all())
