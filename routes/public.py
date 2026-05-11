from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from extensions import db
from models import Appointment, Student, TimeSlot, User, Visitor
from utils.notifications import notify_role
from utils.qr_generator import generate_qr
from utils.security import current_user, parse_date, roles_required, save_upload

public_bp = Blueprint("public", __name__)


@public_bp.route("/dashboard")
@roles_required("public")
def dashboard():
    user = current_user()
    visitors = Visitor.query.filter_by(user_id=user.id).order_by(Visitor.created_at.desc()).all()
    return render_template("public/dashboard.html", visitors=visitors)


@public_bp.route("/book", methods=["GET", "POST"])
@roles_required("public")
def book():
    authorities = User.query.filter(User.role.in_(["staff", "principal", "management"]), User.is_active.is_(True)).all()
    slots = TimeSlot.query.filter_by(is_active=True).order_by(TimeSlot.start_time).all()
    if request.method == "POST":
        try:
            user = current_user()
            id_proof = save_upload(request.files.get("id_proof"), "UPLOAD_FOLDER")
            visitor_photo = save_upload(request.files.get("visitor_photo"), "PROFILE_PHOTO_FOLDER")
            email = request.form["email"].strip().lower()
            email_owner = User.query.filter(User.email == email, User.id != user.id).first()
            if email_owner:
                flash("That email is already used by another account.", "danger")
                return redirect(url_for("public.book"))

            user.name = request.form["full_name"].strip()
            user.phone = request.form["phone"].strip()
            user.email = email

            student_id = request.form.get("student_id", "").strip().upper()
            student = None
            if student_id:
                student = Student.query.filter(
                    (Student.student_id == student_id) | (Student.college_id == student_id)
                ).first()
            visitor = Visitor(
                user_id=user.id,
                purpose=request.form["purpose"],
                visit_date=parse_date(request.form["visit_date"]),
                visit_time=request.form["visit_time"],
                authority_id=int(request.form["authority_id"]),
                visitor_type=request.form["visitor_type"],
                relationship=request.form["relationship"],
                student_id=student_id,
                student_name=(student.student_name or student.full_name) if student else request.form.get("student_name"),
                department=student.department if student else request.form.get("department"),
                year_of_study=request.form.get("year_of_study"),
                parent_name=request.form.get("parent_name"),
                guardian_name=request.form.get("guardian_name"),
                relative_name=request.form.get("relative_name"),
                emergency_contact_name=request.form.get("emergency_contact_name"),
                emergency_contact_phone=request.form.get("emergency_contact_phone"),
                visitor_photo=visitor_photo,
                id_proof_number=request.form.get("id_proof_number"),
                gender=request.form.get("gender"),
                address=request.form["address"],
                id_proof=id_proof,
                is_vip=request.form.get("is_vip") == "on",
            )
            db.session.add(visitor)
            db.session.flush()
            db.session.add(Appointment(visitor_id=visitor.id, notes="Public booking"))
            generate_qr(visitor)
            db.session.commit()
            notify_role(user.id, "security", f"New visitor booked: {user.name}", url_for("security.visitor_detail", visitor_id=visitor.id))
            flash("Appointment booked and QR gatepass generated.", "success")
            return redirect(url_for("public.dashboard"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Booking failed: {exc}", "danger")
    return render_template("public/book.html", authorities=authorities, slots=slots)


@public_bp.route("/api/student/<student_id>")
@roles_required("public")
def student_lookup(student_id):
    student_key = student_id.strip().upper()
    student = Student.query.filter(
        (Student.student_id == student_key) | (Student.college_id == student_key)
    ).first()
    if not student:
        return jsonify({"found": False})
    return jsonify(
        {
            "found": True,
            "student_id": student.student_id or student.college_id,
            "student_name": student.student_name or student.full_name,
            "department": student.department or "",
            "phone": student.phone or "",
        }
    )


@public_bp.route("/visitor/<int:visitor_id>")
@roles_required("public")
def visitor_detail(visitor_id):
    visitor = Visitor.query.filter_by(id=visitor_id, user_id=current_user().id).first_or_404()
    timeline = ["pending", "security_approved", "forwarded", "waiting", "authority_approved", "entered", "completed"]
    return render_template("public/visitor_detail.html", visitor=visitor, timeline=timeline)
