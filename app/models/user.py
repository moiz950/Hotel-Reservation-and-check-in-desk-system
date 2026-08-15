"""User and Staff models."""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class User(UserMixin, db.Model):
    """An authenticated account (administrator, staff member, or website customer)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="guest")  # admin | staff | guest
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationship to the staff profile (if this user is a staff member)
    staff_profile = db.relationship(
        "Staff", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # Relationships
    activity_logs = db.relationship(
        "ActivityLog", back_populates="user", lazy="dynamic", foreign_keys="ActivityLog.user_id"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_staff(self):
        return self.role == "staff"

    @property
    def is_staff_member(self):
        return self.role in ("admin", "staff")

    def has_permission(self, permission):
        """Return True if this user may perform the given permission.

        Administrators implicitly hold every permission.
        """
        if self.is_admin:
            return True
        if self.staff_profile and self.staff_profile.is_active:
            return permission in (self.staff_profile.permissions or [])
        return False

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Staff(db.Model):
    """Front-desk / operational staff profile linked to a User account."""

    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    job_title = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    hire_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # Comma-separated permission keys, e.g. "rooms.view,reservations.create"
    permissions = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="staff_profile")

    @property
    def permission_list(self):
        if not self.permissions:
            return []
        return [p.strip() for p in self.permissions.split(",") if p.strip()]

    def __repr__(self):
        return f"<Staff {self.job_title} user={self.user_id}>"
