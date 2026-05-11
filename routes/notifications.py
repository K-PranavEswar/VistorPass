from flask import Blueprint, jsonify, redirect, request, url_for

from extensions import db
from models import Notification
from utils.security import current_user, login_required

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/")
@login_required
def list_notifications():
    notes = Notification.query.filter_by(receiver_id=current_user().id).order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([{"id": n.id, "message": n.message, "is_read": n.is_read, "link": n.link, "created_at": n.created_at.isoformat()} for n in notes])


@notifications_bp.route("/read/<int:note_id>", methods=["POST"])
@login_required
def mark_read(note_id):
    note = Notification.query.filter_by(id=note_id, receiver_id=current_user().id).first_or_404()
    note.is_read = True
    db.session.commit()
    return redirect(note.link or url_for("auth.login"))
