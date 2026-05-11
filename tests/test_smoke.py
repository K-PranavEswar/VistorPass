import unittest
from datetime import date

from app import app
from extensions import db
from models import Notification, QRLog, Student, User, Visitor


class GatePassSmokeTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def login_as(self, role):
        with app.app_context():
            user = User.query.filter_by(role=role, is_active=True).first()
            if not user:
                user = User(name=f"{role.title()} User", email=f"{role}@example.test", phone="9999999999", role=role)
                user.set_password("Password@123")
                db.session.add(user)
                db.session.commit()
            user_id = user.id
        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["role"] = role

    def test_login_page_loads(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"admin123", response.data)

    def test_admin_cannot_be_deleted(self):
        self.login_as("admin")
        with app.app_context():
            admin = User.query.filter_by(username="admin").first()
            admin_id = admin.id
        response = self.client.post(f"/admin/users/{admin_id}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            admin = db.session.get(User, admin_id)
            self.assertTrue(admin.is_active)

    def test_non_admin_user_can_be_deleted(self):
        self.login_as("admin")
        with app.app_context():
            existing = User.query.filter_by(email="delete.me@example.test").first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            user = User(
                name="Delete Me",
                username="delete_me",
                email="delete.me@example.test",
                phone="9999999999",
                role="staff",
            )
            user.set_password("Password@123")
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        response = self.client.post(f"/admin/users/{user_id}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertIsNone(db.session.get(User, user_id))

    def test_user_with_history_can_be_deleted(self):
        self.login_as("admin")
        with app.app_context():
            for email in ("history.user@example.test", "history.authority@example.test", "history.security@example.test"):
                existing = User.query.filter_by(email=email).first()
                if existing:
                    db.session.delete(existing)
            db.session.commit()

            public_user = User(name="History User", email="history.user@example.test", phone="9999999999", role="public")
            authority = User(name="History Authority", email="history.authority@example.test", phone="9999999998", role="staff")
            security = User(name="History Security", email="history.security@example.test", phone="9999999997", role="security")
            for user in (public_user, authority, security):
                user.set_password("Password@123")
                db.session.add(user)
            db.session.flush()

            visitor = Visitor(
                user_id=public_user.id,
                authority_id=authority.id,
                purpose="History cleanup test",
                visit_date=date.today(),
                visit_time="09:00 - 10:00",
            )
            db.session.add(visitor)
            db.session.flush()
            db.session.add(QRLog(visitor_id=visitor.id, security_id=security.id, status="valid_scan"))
            db.session.add(Notification(sender_id=public_user.id, receiver_id=authority.id, message="History cleanup"))
            db.session.commit()
            user_id = public_user.id
            visitor_id = visitor.id

        response = self.client.post(f"/admin/users/{user_id}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertIsNone(db.session.get(User, user_id))
            self.assertIsNone(db.session.get(Visitor, visitor_id))
            self.assertIsNone(QRLog.query.filter_by(visitor_id=visitor_id).first())
            self.assertIsNone(Notification.query.filter_by(message="History cleanup").first())

   

    def test_role_dashboards_load(self):
        for role, path in [
            ("admin", "/admin/dashboard"),
            ("security", "/security/dashboard"),
            ("staff", "/staff/dashboard"),
            ("principal", "/principal/dashboard"),
            ("management", "/management/dashboard"),
            ("public", "/public/dashboard"),
        ]:
            with self.subTest(role=role):
                self.login_as(role)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
