"""Permission decorators and login helpers."""
from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def staff_required(view):
    """Require an authenticated administrator or staff account."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_staff_member:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Require an authenticated administrator account."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def permission_required(permission):
    """Require the current user to hold a specific permission.

    Administrators implicitly pass every permission check.
    """

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user.is_staff_member:
                abort(403)
            if not current_user.has_permission(permission):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
