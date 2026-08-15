"""WTForms definitions (all CSRF-protected)."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    IntegerField,
    DecimalField,
    SelectField,
    SelectMultipleField,
    DateField,
    HiddenField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    Optional,
    NumberRange,
    ValidationError,
)

from flask_login import current_user
from app.models import User, RoomType, Room, Guest
from app.utils.constants import (
    ROOM_STATUSES,
    RESERVATION_STATUSES,
    PAYMENT_METHODS,
    BANNER_ANIMATIONS,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign In")


class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=160)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=128)]
    )
    confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("An account with that email already exists.")


# ---------------------------------------------------------------------------
# Guests
# ---------------------------------------------------------------------------
class GuestForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=160)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    country = StringField("Country", validators=[Optional(), Length(max=80)])
    id_type = SelectField(
        "ID Type",
        choices=[
            ("", "Select ID type"),
            ("Passport", "Passport"),
            ("National ID", "National ID"),
            ("Driving License", "Driving License"),
            ("Other", "Other"),
        ],
        validators=[Optional()],
    )
    id_number = StringField("ID Number", validators=[Optional(), Length(max=80)])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save Guest")


# ---------------------------------------------------------------------------
# Rooms & room types
# ---------------------------------------------------------------------------
class RoomTypeForm(FlaskForm):
    name = StringField("Room Type Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional()])
    base_price = DecimalField(
        "Base Price", validators=[DataRequired(), NumberRange(min=0)], places=2
    )
    capacity = IntegerField(
        "Capacity", validators=[DataRequired(), NumberRange(min=1, max=20)], default=1
    )
    bed_type = StringField("Bed Type", validators=[Optional(), Length(max=80)])
    facilities = StringField(
        "Facilities (comma separated)", validators=[Optional(), Length(max=500)]
    )
    image = FileField("Image", validators=[FileAllowed(["png", "jpg", "jpeg", "webp", "gif"])])
    is_active = BooleanField("Active")
    submit = SubmitField("Save Room Type")


class RoomForm(FlaskForm):
    room_id = HiddenField("Room ID")
    room_number = StringField("Room Number", validators=[DataRequired(), Length(max=20)])
    room_type_id = SelectField("Room Type", coerce=int, validators=[DataRequired()])
    floor = IntegerField("Floor", validators=[Optional(), NumberRange(min=0, max=100)], default=1)
    price = DecimalField(
        "Nightly Price", validators=[DataRequired(), NumberRange(min=0)], places=2
    )
    capacity = IntegerField(
        "Capacity", validators=[DataRequired(), NumberRange(min=1, max=20)], default=1
    )
    bed_type = StringField("Bed Type", validators=[Optional(), Length(max=80)])
    description = TextAreaField("Description", validators=[Optional()])
    facilities = StringField(
        "Facilities (comma separated)", validators=[Optional(), Length(max=500)]
    )
    status = SelectField("Status", choices=ROOM_STATUSES, validators=[DataRequired()])
    is_active = BooleanField("Active")
    submit = SubmitField("Save Room")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_type_id.choices = [
            (rt.id, rt.name) for rt in RoomType.query.filter_by(is_active=True).all()
        ]

    def validate_room_number(self, field):
        room = Room.query.filter_by(room_number=field.data).first()
        room_id_val = None
        if self.room_id and self.room_id.data not in (None, ""):
            try:
                room_id_val = int(self.room_id.data)
            except (TypeError, ValueError):
                room_id_val = None
        if room and (room_id_val is None or room.id != room_id_val):
            raise ValidationError("A room with this number already exists.")


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------
class ReservationForm(FlaskForm):
    guest_id = SelectField("Guest", coerce=int, validators=[DataRequired()])
    room_id = SelectField("Room", coerce=int, validators=[DataRequired()])
    check_in_date = DateField("Check-In Date", validators=[DataRequired()])
    check_out_date = DateField("Check-Out Date", validators=[DataRequired()])
    adults = IntegerField(
        "Adults", validators=[DataRequired(), NumberRange(min=1, max=20)], default=1
    )
    children = IntegerField(
        "Children", validators=[Optional(), NumberRange(min=0, max=20)], default=0
    )
    special_request = TextAreaField("Special Request", validators=[Optional()])
    room_rate = DecimalField(
        "Nightly Rate", validators=[DataRequired(), NumberRange(min=0)], places=2
    )
    additional_charges = DecimalField(
        "Additional Charges", validators=[Optional(), NumberRange(min=0)], places=2, default=0
    )
    discount = DecimalField(
        "Discount", validators=[Optional(), NumberRange(min=0)], places=2, default=0
    )
    tax_rate = DecimalField(
        "Tax Rate (%)", validators=[Optional(), NumberRange(min=0, max=100)], places=2, default=0
    )
    status = SelectField("Status", choices=RESERVATION_STATUSES, validators=[DataRequired()])
    source = SelectField(
        "Source",
        choices=[("website", "Website"), ("desk", "Front Desk"), ("phone", "Phone")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Reservation")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guest_id.choices = [
            (g.id, f"{g.full_name} ({g.guest_code})") for g in Guest.query.order_by(Guest.full_name).all()
        ]
        self.room_id.choices = [
            (r.id, f"{r.room_number} — {r.room_type.name if r.room_type else ''}") for r in Room.query.all()
        ]


class ReservationSearchForm(FlaskForm):
    q = StringField("Search", validators=[Optional(), Length(max=120)])
    status = SelectField("Status", choices=[("", "All statuses")] + RESERVATION_STATUSES, validators=[Optional()])
    payment_status = SelectField(
        "Payment",
        choices=[("", "All payments"), ("pending", "Pending"), ("partially_paid", "Partially Paid"), ("paid", "Paid")],
        validators=[Optional()],
    )
    date_from = DateField("From", validators=[Optional()])
    date_to = DateField("To", validators=[Optional()])
    submit = SubmitField("Filter")


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
class PaymentForm(FlaskForm):
    amount = DecimalField("Amount", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    method = SelectField("Method", choices=PAYMENT_METHODS, validators=[DataRequired()])
    reference = StringField("Reference", validators=[Optional(), Length(max=120)])
    note = StringField("Note", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Record Payment")


# ---------------------------------------------------------------------------
# Housekeeping & maintenance
# ---------------------------------------------------------------------------
class HousekeepingForm(FlaskForm):
    room_id = SelectField("Room", coerce=int, validators=[DataRequired()])
    assigned_to = StringField("Assigned To", validators=[Optional(), Length(max=100)])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Create Task")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id.choices = [
            (r.id, f"{r.room_number} ({r.status})") for r in Room.query.order_by(Room.room_number).all()
        ]


class MaintenanceForm(FlaskForm):
    room_id = SelectField("Room", coerce=int, validators=[DataRequired()])
    reason = StringField("Reason", validators=[DataRequired(), Length(max=200)])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Create Task")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id.choices = [
            (r.id, f"{r.room_number} ({r.status})") for r in Room.query.order_by(Room.room_number).all()
        ]


# ---------------------------------------------------------------------------
# Website content
# ---------------------------------------------------------------------------
class HeroBannerForm(FlaskForm):
    title = StringField("Banner Title", validators=[DataRequired(), Length(max=160)])
    subtitle = StringField("Subtitle", validators=[Optional(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional()])
    image = FileField("Banner Image", validators=[FileAllowed(["png", "jpg", "jpeg", "webp", "gif"])])
    cta_text = StringField("Primary Button Text", validators=[Optional(), Length(max=80)])
    cta_url = StringField("Primary Button URL", validators=[Optional(), Length(max=255)])
    cta2_text = StringField("Secondary Button Text", validators=[Optional(), Length(max=80)])
    cta2_url = StringField("Secondary Button URL", validators=[Optional(), Length(max=255)])
    animation = SelectField("Animation", choices=BANNER_ANIMATIONS, validators=[DataRequired()])
    display_order = IntegerField("Display Order", validators=[Optional()], default=0)
    is_active = BooleanField("Active")
    submit = SubmitField("Save Banner")


class PromoBannerForm(FlaskForm):
    title = StringField("Banner Title", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Description", validators=[Optional()])
    image = FileField("Banner Image", validators=[FileAllowed(["png", "jpg", "jpeg", "webp", "gif"])])
    badge_text = StringField("Badge Text", validators=[Optional(), Length(max=60)])
    cta_text = StringField("Button Text", validators=[Optional(), Length(max=80)])
    cta_url = StringField("Button URL", validators=[Optional(), Length(max=255)])
    display_order = IntegerField("Display Order", validators=[Optional()], default=0)
    is_active = BooleanField("Active")
    submit = SubmitField("Save Banner")


class ServiceForm(FlaskForm):
    name = StringField("Service Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional()])
    icon = StringField("Icon (emoji or class)", validators=[Optional(), Length(max=60)])
    display_order = IntegerField("Display Order", validators=[Optional()], default=0)
    is_active = BooleanField("Active")
    submit = SubmitField("Save Service")


class ContactForm(FlaskForm):
    name = StringField("Your Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=160)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    subject = StringField("Subject", validators=[Optional(), Length(max=200)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Send Message")


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------
class StaffForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=160)])
    password = PasswordField(
        "Password (leave blank to keep current)",
        validators=[Optional(), Length(min=6, max=128)],
    )
    job_title = StringField("Job Title", validators=[Optional(), Length(max=100)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    permissions = SelectMultipleField("Permissions", coerce=str, validators=[Optional()])
    is_active = BooleanField("Active")
    submit = SubmitField("Save Staff")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.utils.constants import PERMISSIONS

        self.permissions.choices = [
            (key, f"{group['label']} — {item}")
            for group in PERMISSIONS.values()
            for key, item in group["items"].items()
        ]


# ---------------------------------------------------------------------------
# Check-in / check-out
# ---------------------------------------------------------------------------
class CheckInForm(FlaskForm):
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Complete Check-In")


class CheckOutForm(FlaskForm):
    additional_charges = DecimalField(
        "Additional Charges", validators=[Optional(), NumberRange(min=0)], places=2, default=0
    )
    discount = DecimalField(
        "Discount", validators=[Optional(), NumberRange(min=0)], places=2, default=0
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Complete Check-Out")


# ---------------------------------------------------------------------------
# Admin account & media
# ---------------------------------------------------------------------------
class AccountForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=160)])
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password (leave blank to keep current)",
        validators=[Optional(), Length(min=6, max=128)],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[Optional(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Save Changes")

    def validate_username(self, field):
        if User.query.filter(User.username == field.data, User.id != current_user.id).first():
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.query.filter(User.email == field.data.lower(), User.id != current_user.id).first():
            raise ValidationError("An account with that email already exists.")


class RoomImageForm(FlaskForm):
    image = FileField(
        "Room Image",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp", "gif"]), DataRequired()],
    )
    caption = StringField("Caption", validators=[Optional(), Length(max=160)])
    is_primary = BooleanField("Set as primary image")
    submit = SubmitField("Upload Image")


class SpecialOfferForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Description", validators=[Optional()])
    discount_details = StringField("Discount Details", validators=[Optional(), Length(max=255)])
    image = FileField("Image", validators=[FileAllowed(["png", "jpg", "jpeg", "webp", "gif"])])
    badge_text = StringField("Badge Text", validators=[Optional(), Length(max=60)])
    cta_text = StringField("Button Text", validators=[Optional(), Length(max=80)])
    cta_url = StringField("Button URL", validators=[Optional(), Length(max=255)])
    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
    display_order = IntegerField("Display Order", validators=[Optional()], default=0)
    is_active = BooleanField("Active")
    submit = SubmitField("Save Offer")

    def validate_end_date(self, field):
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError("End date cannot be before the start date.")


class ThemeForm(FlaskForm):
    primary_color = StringField("Primary Color", validators=[DataRequired(), Length(max=9)])
    secondary_color = StringField("Secondary Color", validators=[DataRequired(), Length(max=9)])
    background_color = StringField("Background Color", validators=[DataRequired(), Length(max=9)])
    text_color = StringField("Text Color", validators=[DataRequired(), Length(max=9)])
    button_style = SelectField(
        "Button Style",
        choices=[("rounded", "Rounded"), ("square", "Square"), ("pill", "Pill")],
        validators=[DataRequired()],
    )
    mode = SelectField(
        "Mode",
        choices=[("light", "Light"), ("dark", "Dark")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Apply Theme")
