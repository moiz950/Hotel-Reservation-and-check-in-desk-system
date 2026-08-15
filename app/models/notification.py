"""Notification and ActivityLog models."""
from datetime import datetime
from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=True)
    # info | success | warning | error | booking | payment | housekeeping | maintenance
    category = db.Column(db.String(30), nullable=False, default="info")
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification {self.title}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    entity_type = db.Column(db.String(60), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(60), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", back_populates="activity_logs", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ActivityLog {self.action}>"
