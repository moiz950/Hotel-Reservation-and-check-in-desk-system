"""Shared helpers to commit changes while adding notifications and logs."""
from app import db
from app.services.notifications import notify, log_activity


def commit_with(user, action, entity_type=None, entity_id=None, details=None,
                notification_title=None, notification_message="", notification_category="info",
                notification_link=None, ip=None):
    """Commit the current session and record an activity log + optional notification."""
    db.session.commit()
    if action:
        log_activity(action, entity_type, entity_id, details, user=user, ip=ip)
    if notification_title:
        notify(notification_title, notification_message, notification_category, notification_link)
    db.session.commit()
