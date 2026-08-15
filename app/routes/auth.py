"""Authentication routes: login, register, logout."""
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, Guest
from app.forms import LoginForm, RegisterForm
from app.utils.helpers import simple_code
from app.services.notifications import log_activity

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.username.data)
        ).first()
        if user and user.check_password(form.password.data):
            if not user.is_active_account:
                flash("This account has been deactivated. Contact the administrator.", "error")
                return render_template("auth/login.html", form=form)
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_activity("User logged in", "user", user.id, f"{user.username} signed in", user=user)
            db.session.commit()
            flash(f"Welcome back, {user.full_name or user.username}!", "success")
            if user.is_staff_member:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("public.home"))
        flash("Invalid username or password.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            full_name=form.full_name.data,
            role="guest",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        guest = Guest(
            guest_code=simple_code("GST"),
            full_name=form.full_name.data,
            email=form.email.data.lower(),
            user_id=user.id,
        )
        db.session.add(guest)
        db.session.commit()

        log_activity("Guest registered", "guest", guest.id, f"{guest.full_name} created an account", user=user)
        db.session.commit()

        login_user(user)
        flash("Your account has been created. Welcome!", "success")
        return redirect(url_for("public.home"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_activity("User logged out", "user", current_user.id, f"{current_user.username} signed out", user=current_user)
    db.session.commit()
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("public.home"))