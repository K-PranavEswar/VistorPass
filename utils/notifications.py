from flask import url_for

from extensions import db, socketio
from models import Notification, User


def create_notification(sender_id, receiver_id, message, link=None):
    note = Notification(sender_id=sender_id, receiver_id=receiver_id, message=message, link=link)
    db.session.add(note)
    db.session.commit()
    socketio.emit(
        "notification",
        {"id": note.id, "message": message, "link": link or "", "receiver_id": receiver_id},
        room=f"user-{receiver_id}",
    )
    return note


def notify_role(sender_id, role, message, link=None):
    receivers = User.query.filter_by(role=role, is_active=True).all()
    return [create_notification(sender_id, user.id, message, link) for user in receivers]


def unread_count(user_id):
    return Notification.query.filter_by(receiver_id=user_id, is_read=False).count()
