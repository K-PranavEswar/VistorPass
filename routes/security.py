import json
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from extensions import db
from models import QRLog, Student, Teacher, User, Visitor, WaitingRoom
from utils.dsa import approval_path, college_id_hash
from utils.notifications import create_notification
from utils.qr_generator import verify_payload
from utils.security import current_user, roles_required, validate_qr_visit

security_bp = Blueprint("security", __name__)


@security_bp.route("/dashboard")
@roles_required("security")
def dashboard():
    stats = {
        "pending": Visitor.query.filter_by(status="pending").count(),
        "approved": Visitor.query.filter_by(status="authority_approved").count(),
        "waiting": Visitor.query.filter_by(status="waiting").count(),
        "entered": Visitor.query.filter_by(status="entered").count(),
    }
    visitors = Visitor.query.order_by(Visitor.created_at.desc()).limit(20).all()
    return render_template("security/dashboard.html", stats=stats, visitors=visitors)


@security_bp.route("/scanner", methods=["GET", "POST"])
@roles_required("security")
def scanner():

    scanned = None
    student = None
    error = None

    if request.method == "POST":

        payload = request.form.get(
            "qr_payload",
            ""
        ).strip()

        # Existing visitor QR validation
        data = verify_payload(payload)

        if data:
            scanned = db.session.get(
                Visitor,
                int(data["visitor_id"])
            )

            if scanned:

                valid, error = validate_qr_visit(
                    scanned
                )

                db.session.add(
                    QRLog(
                        visitor_id=scanned.id,
                        security_id=current_user().id,
                        status=(
                            error
                            if not valid
                            else "valid_scan"
                        ),
                    )
                )

                db.session.commit()

                if not valid:
                    scanned = None

            else:
                error = "Visitor not found."

        else:
            # Student QR fallback
            try:
                student_data = json.loads(
                    payload
                )

                student_id = student_data.get(
                    "student_id"
                )

                if student_id:

                    student = Student.query.filter_by(
                        student_id=student_id
                    ).first()

                    if not student:
                        error = (
                            "Student not found."
                        )

                else:
                    error = (
                        "Invalid student QR."
                    )

            except Exception:
                error = (
                    "Invalid or tampered QR payload."
                )

    return render_template(
        "security/scanner.html",
        visitor=scanned,
        student=student,
        error=error
    )


@security_bp.route("/visitor/<int:visitor_id>")
@roles_required("security")
def visitor_detail(visitor_id):
    visitor = db.session.get(Visitor, visitor_id) or Visitor.query.get_or_404(visitor_id)
    return render_template("security/visitor_detail.html", visitor=visitor, path=approval_path("security", visitor.authority.role))


@security_bp.route("/visitor/<int:visitor_id>/action", methods=["POST"])
@roles_required("security")
def visitor_action(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    action = request.form["action"]
    if action == "approve":
        visitor.status = "security_approved"
        message = f"Security approved visitor {visitor.public_user.name}"
    elif action == "reject":
        visitor.status = "rejected"
        message = f"Security rejected visitor {visitor.public_user.name}"
    elif action == "forward":
        visitor.status = "forwarded"
        message = f"Visitor waiting for you: {visitor.public_user.name}"
        create_notification(current_user().id, visitor.authority_id, message, url_for(f"{visitor.authority.role}.requests"))
    elif action == "waiting":
        visitor.status = "waiting"
        if not visitor.waiting_record:
            db.session.add(WaitingRoom(visitor_id=visitor.id, priority=1 if visitor.is_vip else 5, reason="Authority busy"))
        message = f"Visitor moved to waiting: {visitor.public_user.name}"
    elif action == "entry":
        valid, msg = validate_qr_visit(visitor)
        if not valid or visitor.status != "authority_approved":
            flash(msg if not valid else "Authority approval is required before entry.", "danger")
            return redirect(url_for("security.visitor_detail", visitor_id=visitor.id))
        visitor.status = "entered"
        visitor.entry_time = datetime.utcnow()
        message = f"Entry allowed for {visitor.public_user.name}"
    elif action == "exit":
        visitor.status = "completed"
        visitor.exit_time = datetime.utcnow()
        message = f"Exit logged for {visitor.public_user.name}"
    else:
        flash("Unknown action.", "danger")
        return redirect(url_for("security.visitor_detail", visitor_id=visitor.id))
    db.session.commit()
    flash(message, "success")
    return redirect(url_for("security.visitor_detail", visitor_id=visitor.id))


@security_bp.route("/search")
@roles_required("security")
def search():

    query = request.args.get("college_id", "").strip().lower()
    visitor_results = []

    records = (
        Student.query.all()
        + Teacher.query.all()
        + User.query.filter(
            User.role.in_(
                ["staff", "principal", "management", "admin"]
            )
        ).all()
    )

    if query:
        results = []
        pattern = f"%{query}%"

        for record in records:
            college_id = getattr(
                record,
                "college_id",
                ""
            ).lower()

            if query in college_id:
                results.append(record)
        visitor_results = (
            Visitor.query.join(User, Visitor.user_id == User.id)
            .filter(
                (User.name.ilike(pattern))
                | (User.phone.ilike(pattern))
                | (Visitor.student_id.ilike(pattern))
                | (Visitor.parent_name.ilike(pattern))
                | (Visitor.relationship.ilike(pattern))
            )
            .order_by(Visitor.created_at.desc())
            .limit(25)
            .all()
        )
    else:
        results = records

    return render_template(
        "security/search.html",
        results=results,
        visitor_results=visitor_results,
        query=query
    )


@security_bp.route("/api/search")
@roles_required("security")
def api_search():
    query = request.args.get("college_id", "").strip().lower()
    records = Student.query.all() + Teacher.query.all() + User.query.filter(User.role.in_(["principal", "management"])).all()
    result = college_id_hash(records).get(query)
    if not result:
        return jsonify({"found": False})
    return jsonify(
        {
            "found": True,
            "name": getattr(result, "full_name", getattr(result, "name", "")),
            "department": getattr(result, "department", ""),
            "phone": getattr(result, "phone", ""),
            "designation": getattr(result, "designation", "Student"),
            "course_applied": getattr(result, "course_applied", ""),
            "photo": getattr(result, "photo", ""),
        }
    )
