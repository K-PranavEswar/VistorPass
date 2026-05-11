import os
import re
from datetime import date

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from sqlalchemy import func

from extensions import db
from models import Student, User, Visitor
from utils.notifications import create_notification, notify_role
from utils.student_qr import generate_student_qr
from utils.security import current_user, roles_required

staff_bp = Blueprint("staff", __name__)
principal_bp = Blueprint("principal", __name__)
management_bp = Blueprint("management", __name__)


def _dashboard(role, template):
    visitors = Visitor.query.filter_by(authority_id=current_user().id).order_by(Visitor.created_at.desc()).limit(20).all()
    pending = [v for v in visitors if v.status in {"forwarded", "waiting"}]
    return render_template(template, visitors=visitors, pending=pending)


@staff_bp.route("/dashboard")
@roles_required("staff")
def dashboard():
    return _dashboard("staff", "staff/dashboard.html")


@principal_bp.route("/dashboard")
@roles_required("principal")
def dashboard():
    return _dashboard("principal", "principal/dashboard.html")


@management_bp.route("/dashboard")
@roles_required("management")
def dashboard():
    return _dashboard("management", "management/dashboard.html")


@staff_bp.route("/requests")
@roles_required("staff")
def requests():
    return _dashboard("staff", "staff/requests.html")


def _valid_phone(phone):
    return bool(re.fullmatch(r"[6-9]\d{9}", phone.strip()))


COURSE_DURATIONS = {
    "MCA": 2,
    "MBA": 2,
    "MSc": 2,
    "MA": 2,
    "MCom": 2,
    "B.Tech": 4,
    "BHM": 4,
    "BCA": 3,
    "BSc": 3,
    "BCom": 3,
    "BA": 3,
    "BBA": 3,
}
COURSE_OPTIONS = list(COURSE_DURATIONS.keys())


def calculate_batch_and_year(course, admission_year):
    duration = COURSE_DURATIONS[course]
    batch = f"{admission_year}-{str(admission_year + duration)[-2:]}"
    elapsed_years = date.today().year - admission_year
    academic_number = max(1, min(duration, elapsed_years + 1))
    if academic_number >= duration:
        current_year = "Final Year"
    elif academic_number == 1:
        current_year = "1st Year"
    elif academic_number == 2:
        current_year = "2nd Year"
    elif academic_number == 3:
        current_year = "3rd Year"
    else:
        current_year = f"{academic_number}th Year"
    return batch, current_year


def admission_year_options():
    current_year = date.today().year
    return list(range(2020, current_year + 6))


def staff_department():
    user = current_user()
    return (user.department or "").strip() if user else ""


def normalized_department(value):
    return (value or "").strip().lower()


def department_students_query():
    department = staff_department()
    if not department:
        return Student.query.filter(Student.id == -1)
    return Student.query.filter(func.lower(func.trim(Student.department)) == normalized_department(department))


def get_department_student_or_403(student_id):
    student = Student.query.get_or_404(student_id)
    department = staff_department()
    if not department or normalized_department(student.department) != normalized_department(department):
        abort(403, description="Access denied. Student belongs to another department.")
    return student


@staff_bp.route("/students")
@roles_required("staff")
def students():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    department = staff_department()
    query = department_students_query()
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Student.student_id.ilike(pattern))
            | (Student.student_name.ilike(pattern))
            | (Student.course.ilike(pattern))
            | (Student.batch.ilike(pattern))
            | (Student.current_year.ilike(pattern))
            | (Student.department.ilike(pattern))
            | (Student.address.ilike(pattern))
            | (Student.phone.ilike(pattern))
            | (Student.college_id.ilike(pattern))
            | (Student.full_name.ilike(pattern))
        )
    pagination = query.order_by(Student.created_at.desc(), Student.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template(
        "staff/manage_students.html",
        pagination=pagination,
        students=pagination.items,
        search=search,
        teacher_department=department,
    )


@staff_bp.route("/students/add", methods=["GET", "POST"])
@roles_required("staff")
def add_student():
    department = staff_department()
    if not department:
        flash("Your staff account does not have a department assigned. Contact admin.", "danger")
        return redirect(url_for("staff.students"))
    if request.method == "POST":
        student_id_value = request.form["student_id"].strip().upper()
        student_name = request.form["student_name"].strip()
        course = request.form["course"]
        admission_year = int(request.form["admission_year"])
        address = request.form["address"].strip()
        phone = request.form["phone"].strip()
        batch, current_year = calculate_batch_and_year(course, admission_year)
        if not all([student_id_value, student_name, department, course, address, phone]):
            flash("All fields are required.", "danger")
            return render_template("staff/add_student.html", courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)
        if not _valid_phone(phone):
            flash("Enter a valid 10-digit Indian phone number.", "danger")
            return render_template("staff/add_student.html", courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)
        if Student.query.filter(
            (Student.student_id == student_id_value) | (Student.college_id == student_id_value)
        ).first():
            flash("Student ID already exists.", "danger")
            return render_template("staff/add_student.html", courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)

        student = Student(
            student_id=student_id_value,
            student_name=student_name,
            college_id=student_id_value,
            full_name=student_name,
            department=department,
            course=course,
            course_applied=course,
            admission_year=admission_year,
            batch=batch,
            current_year=current_year,
            address=address,
            phone=phone,
            created_by_staff_id=current_user().id,
        )
        db.session.add(student)
        db.session.flush()
        generate_student_qr(student)
        db.session.commit()
        flash("Student saved and QR code generated.", "success")
        return redirect(url_for("staff.view_student", student_id=student.id))
    return render_template("staff/add_student.html", courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)


@staff_bp.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
@roles_required("staff")
def edit_student(student_id):
    student = get_department_student_or_403(student_id)
    department = staff_department()
    if request.method == "POST":
        new_student_id = request.form["student_id"].strip().upper()
        student_name = request.form["student_name"].strip()
        course = request.form["course"]
        admission_year = int(request.form["admission_year"])
        address = request.form["address"].strip()
        phone = request.form["phone"].strip()
        batch, current_year = calculate_batch_and_year(course, admission_year)
        if not all([new_student_id, student_name, department, course, address, phone]):
            flash("All fields are required.", "danger")
            return render_template("staff/add_student.html", student=student, courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)
        if not _valid_phone(phone):
            flash("Enter a valid 10-digit Indian phone number.", "danger")
            return render_template("staff/add_student.html", student=student, courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)
        duplicate = Student.query.filter(
            Student.id != student.id,
            (Student.student_id == new_student_id) | (Student.college_id == new_student_id),
        ).first()
        if duplicate:
            flash("Student ID already exists.", "danger")
            return render_template("staff/add_student.html", student=student, courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)

        old_qr = student.qr_code
        student.student_id = new_student_id
        student.student_name = student_name
        student.college_id = new_student_id
        student.full_name = student_name
        student.department = department
        student.course = course
        student.course_applied = course
        student.admission_year = admission_year
        student.batch = batch
        student.current_year = current_year
        student.address = address
        student.phone = phone
        generate_student_qr(student)
        if old_qr and old_qr != student.qr_code:
            old_path = os.path.join(current_app.static_folder, old_qr.replace("/", os.sep))
            if os.path.exists(old_path):
                os.remove(old_path)
        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("staff.view_student", student_id=student.id))
    return render_template("staff/add_student.html", student=student, courses=COURSE_OPTIONS, admission_years=admission_year_options(), teacher_department=department)


@staff_bp.route("/students/delete/<int:student_id>", methods=["POST"])
@roles_required("staff")
def delete_student(student_id):
    student = get_department_student_or_403(student_id)
    qr_code = student.qr_code
    db.session.delete(student)
    db.session.commit()
    if qr_code:
        qr_path = os.path.join(current_app.static_folder, qr_code.replace("/", os.sep))
        if os.path.exists(qr_path):
            os.remove(qr_path)
    flash("Student deleted.", "success")
    return redirect(url_for("staff.students"))


@staff_bp.route("/students/view/<int:student_id>")
@staff_bp.route("/student/<int:student_id>")
@roles_required("staff")
def view_student(student_id):
    student = get_department_student_or_403(student_id)
    return render_template("staff/view_student.html", student=student)


@staff_bp.route("/student/download-qr/<int:student_id>")
@roles_required("staff")
def download_student_qr(student_id):
    student = get_department_student_or_403(student_id)
    if not student.qr_code:
        flash("QR code is not available for this student.", "warning")
        return redirect(url_for("staff.view_student", student_id=student.id))
    directory = os.path.join(current_app.static_folder, "qrcodes", "students")
    filename = os.path.basename(student.qr_code)
    return send_from_directory(directory, filename, as_attachment=True, download_name=filename)


@principal_bp.route("/requests", endpoint="requests")
@roles_required("principal")
def principal_requests():
    return _dashboard("principal", "principal/requests.html")


@management_bp.route("/requests", endpoint="requests")
@roles_required("management")
def management_requests():
    return _dashboard("management", "management/requests.html")


def handle_action(visitor_id, role):
    visitor = Visitor.query.filter_by(id=visitor_id, authority_id=current_user().id).first_or_404()
    action = request.form["action"]
    if action == "approve":
        visitor.status = "authority_approved"
        notify_role(current_user().id, "security", f"Visitor approved: {visitor.public_user.name}", url_for("security.visitor_detail", visitor_id=visitor.id))
        flash("Visitor approved. Security has been notified.", "success")
    elif action == "reject":
        visitor.status = "rejected"
        notify_role(current_user().id, "security", f"Visitor rejected: {visitor.public_user.name}", url_for("security.visitor_detail", visitor_id=visitor.id))
        flash("Visitor rejected.", "warning")
    elif action == "delay":
        visitor.status = "waiting"
        notify_role(current_user().id, "security", f"Visitor delayed by authority: {visitor.public_user.name}", url_for("security.visitor_detail", visitor_id=visitor.id))
        flash("Security notified to keep visitor waiting.", "info")
    db.session.commit()
    return redirect(url_for(f"{role}.requests"))


@staff_bp.route("/request/<int:visitor_id>/action", methods=["POST"])
@roles_required("staff")
def request_action(visitor_id):
    return handle_action(visitor_id, "staff")


@principal_bp.route("/request/<int:visitor_id>/action", methods=["POST"], endpoint="request_action")
@roles_required("principal")
def principal_request_action(visitor_id):
    return handle_action(visitor_id, "principal")


@management_bp.route("/request/<int:visitor_id>/action", methods=["POST"], endpoint="request_action")
@roles_required("management")
def management_request_action(visitor_id):
    return handle_action(visitor_id, "management")


@staff_bp.route("/availability", methods=["POST"])
@principal_bp.route("/availability", methods=["POST"])
@management_bp.route("/availability", methods=["POST"])
@roles_required("staff", "principal", "management")
def availability():
    user = current_user()
    user.is_available = request.form.get("available") == "on"
    db.session.commit()
    flash("Availability updated.", "success")
    return redirect(url_for(f"{user.role}.dashboard"))
