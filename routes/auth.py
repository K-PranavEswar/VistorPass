from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from extensions import db
from models import User
from utils.security import ROLE_DASHBOARDS, current_user, login_required, save_upload

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form["identity"].strip().lower()
        user = User.query.filter(
            or_(User.email == identity, User.username == identity),
            User.is_active.is_(True),
        ).first()
        if user and user.check_password(request.form["password"]):
            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role
            flash(f"Welcome back, {user.name}.", "success")
            return redirect(request.args.get("next") or url_for(ROLE_DASHBOARDS[user.role]))
        flash("Invalid username/email or password.", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Email is already registered.", "warning")
            return redirect(url_for("auth.register"))
        try:
            photo = save_upload(request.files.get("photo"), "PROFILE_PHOTO_FOLDER")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("auth.register"))
        user = User(name=request.form["name"], email=email, phone=request.form["phone"], role="public", photo=photo)
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        flash("For security, please contact the college gatepass administrator to reset your password.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    user = current_user()
    if request.method == "POST":
        if not user.check_password(request.form["current_password"]):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.change_password"))
        user.set_password(request.form["new_password"])
        db.session.commit()
        flash("Password changed successfully.", "success")
        return redirect(url_for(ROLE_DASHBOARDS[user.role]))
    return render_template("auth/change_password.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
