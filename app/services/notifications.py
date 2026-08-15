"""Notification and activity-log helpers."""
from app import db
from app.models import Notification, ActivityLog


def notify(title, message="", category="info", link=None):
    """Create a system notification."""
    notification = Notification(
        title=title,
        message=message,
        category=category,
        link=link,
    )
    db.session.add(notification)
    return notification


def log_activity(action, entity_type=None, entity_id=None, details=None, user=None, ip=None):
    """Record an activity log entry.

    If ``user`` is not supplied and we are inside a request, the current
    user is used automatically.
    """
    if user is None:
        from flask_login import current_user

        try:
            if current_user.is_authenticated:
                user = current_user
        except Exception:
            user = None

    entry = ActivityLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=(details or "")[:500],
        ip_address=ip,
    )
    db.session.add(entry)
    return entry


def commit_notifications_and_logs():
    """Flush both new notifications and log entries to the database."""
    db.session.flush()
