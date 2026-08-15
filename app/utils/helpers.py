"""Helper functions used across the application."""
import os
import uuid
from datetime import date, datetime, timedelta

from flask import current_app
from werkzeug.utils import secure_filename

from app.models import WebsiteSetting


# ---------------------------------------------------------------------------
# Money & formatting
# ---------------------------------------------------------------------------
def format_money(value, currency=None):
    """Format a numeric value using the configured currency symbol."""
    if value is None:
        value = 0
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError):
        amount = 0.0
    symbol = currency or settings_value("currency") or "$"
    if amount == int(amount):
        return f"{symbol}{int(amount):,}"
    return f"{symbol}{amount:,.2f}"


def status_badge_class(status):
    """Map a status string to a CSS badge class for consistent styling."""
    mapping = {
        # Room statuses
        "available": "success",
        "reserved": "info",
        "occupied": "primary",
        "cleaning": "warning",
        "maintenance": "danger",
        "out_of_service": "dark",
        # Reservation statuses
        "pending": "warning",
        "confirmed": "info",
        "checked_in": "success",
        "checked_out": "secondary",
        "cancelled": "danger",
        # Payment statuses
        "paid": "success",
        "partially_paid": "warning",
        "unpaid": "danger",
        # Housekeeping / maintenance
        "in_progress": "info",
        "open": "warning",
        "completed": "success",
        # Notifications
        "info": "info",
        "success": "success",
        "warning": "warning",
        "error": "danger",
    }
    return mapping.get(str(status).lower(), "secondary")


def today_local():
    return date.today()


# ---------------------------------------------------------------------------
# Website settings
# ---------------------------------------------------------------------------
def settings_value(key, default=""):
    """Return a single website setting value."""
    setting = WebsiteSetting.query.filter_by(key=key).first()
    return setting.value if setting else default


def app_settings():
    """Return all website settings as a plain dict (for templates/context)."""
    values = {}
    for setting in WebsiteSetting.query.all():
        values[setting.key] = setting.value
    return values


# ---------------------------------------------------------------------------
# Website theme
# ---------------------------------------------------------------------------
THEME_KEYS = [
    "theme_primary_color",
    "theme_secondary_color",
    "theme_background_color",
    "theme_text_color",
    "theme_button_style",
    "theme_mode",
]

_THEME_DEFAULTS = {
    "theme_primary_color": "#1F4E79",
    "theme_secondary_color": "#C9A24B",
    "theme_background_color": "#FFFFFF",
    "theme_text_color": "#1A1A1A",
    "theme_button_style": "rounded",
    "theme_mode": "light",
}


def theme_dict():
    """Return the active website theme as a plain dict with safe defaults."""
    theme = dict(_THEME_DEFAULTS)
    from app.models import ThemeSetting

    for row in ThemeSetting.query.all():
        if row.key in THEME_KEYS:
            theme[row.key] = row.value
    return theme


# ---------------------------------------------------------------------------
# Unique codes
# ---------------------------------------------------------------------------
def generate_code(prefix, model, column="code", length=8):
    """Generate a unique alphanumeric code with the given prefix.

    Example: RES-X7K2P9AQ

    ``model`` is the SQLAlchemy model class, ``column`` is the name of the
    unique code column to check for collisions.
    """
    import random
    import string

    alphabet = string.ascii_uppercase + string.digits
    for _ in range(50):
        body = "".join(random.choice(alphabet) for _ in range(length))
        candidate = f"{prefix}-{body}"
        exists = model.query.filter(getattr(model, column) == candidate).first()
        if not exists:
            return candidate
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def simple_code(prefix):
    """A fast unique code generator used during seeding."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------
def allowed_image(filename):
    """Validate that the uploaded file has an allowed image extension."""
    if not filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_upload(file_storage, subfolder="banners"):
    """Securely save an uploaded image and return a web path.

    Returns None when the upload is invalid.
    """
    # Reject non-upload input (e.g. a string filename left in the form on edit).
    if not file_storage or not hasattr(file_storage, "filename") or not file_storage.filename:
        return None
    if not allowed_image(file_storage.filename):
        return None

    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    safe_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, safe_name))
    return f"/static/uploads/{subfolder}/{safe_name}"


def delete_upload(path):
    """Delete an uploaded file referenced by a web path (best effort)."""
    if not path or not path.startswith("/static/uploads/"):
        return
    filename = path.replace("/static/uploads/", "", 1)
    abs_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def parse_date(value, default=None):
    """Parse a YYYY-MM-DD string into a date object."""
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default


def nights_between(check_in, check_out):
    """Number of nights (check-out minus check-in)."""
    return max((check_out - check_in).days, 0)
