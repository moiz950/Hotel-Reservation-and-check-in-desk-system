"""Public customer-facing website routes."""
from datetime import date, timedelta

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
)
from flask_login import current_user

from app import db
from app.models import (
    RoomType,
    Room,
    HeroBanner,
    PromotionalBanner,
    Service,
    Guest,
    Reservation,
    ContactMessage,
    SpecialOffer,
    ThemeSetting,
    AboutContent,
)
from app.forms import ContactForm
from app.services.availability import available_rooms, validate_dates
from app.services.billing import compute_stay
from app.utils.helpers import simple_code, settings_value
from app.utils.constants import BLOCKING_RESERVATION_STATUSES
from app.services.notifications import notify, log_activity

public_bp = Blueprint("public", __name__)


def _theme_dict():
    theme = {}
    for row in ThemeSetting.query.all():
        theme[row.key] = row.value
    defaults = {
        "theme_primary_color": "#0A1F44",
        "theme_secondary_color": "#1F4E79",
        "theme_background_color": "#FFFFFF",
        "theme_text_color": "#0A1F44",
        "theme_button_style": "rounded",
        "theme_mode": "light",
    }
    defaults.update(theme)
    return defaults




def _active_room_types():
    return RoomType.query.filter_by(is_active=True).order_by(RoomType.base_price).all()


@public_bp.route("/")
def home():
    banners = (
        HeroBanner.query.filter_by(is_active=True)
        .order_by(HeroBanner.display_order, HeroBanner.id)
        .all()
    )
    today = date.today()
    promos = (
        SpecialOffer.query.filter_by(is_active=True)
        .order_by(SpecialOffer.display_order, SpecialOffer.id)
        .all()
    )
    # Show active offers that are not yet expired. A future start_date is
    # treated as an "upcoming" offer and is still displayed on the home page.
    promos = [p for p in promos if not (p.end_date and p.end_date < today)]
    services = (
        Service.query.filter_by(is_active=True)
        .order_by(Service.display_order, Service.id)
        .all()
    )
    featured = (
        RoomType.query.filter_by(is_active=True)
        .order_by(RoomType.base_price)
        .limit(6)
        .all()
    )
    return render_template(
        "public/home.html",
        banners=banners,
        promos=promos,
        services=services,
        featured=featured,
        room_types=_active_room_types(),
        theme=_theme_dict(),
    )


@public_bp.route("/rooms")
def rooms():
    room_types = _active_room_types()
    selected_type = request.args.get("type", type=int)
    check_in = request.args.get("check_in", "")
    check_out = request.args.get("check_out", "")

    query = RoomType.query.filter_by(is_active=True)
    if selected_type:
        query = query.filter(RoomType.id == selected_type)
    types = query.order_by(RoomType.base_price).all()
    return render_template(
        "public/rooms.html",
        room_types=types,
        all_types=room_types,
        selected_type=selected_type,
        check_in=check_in,
        check_out=check_out,
    )


@public_bp.route("/rooms/<int:room_type_id>")
def room_detail(room_type_id):
    room_type = RoomType.query.get_or_404(room_type_id)
    if not room_type.is_active:
        abort(404)
    return render_template("public/room_detail.html", room_type=room_type)


@public_bp.route("/reservation", methods=["GET", "POST"])
def reservation():
    """Availability search + reservation creation."""
    check_in = request.args.get("check_in", "")
    check_out = request.args.get("check_out", "")
    guests = request.args.get("guests", "2", type=int)
    room_type_id = request.args.get("room_type", type=int)

    available = []
    error = None
    selected_room = None
    summary = None

    if request.method == "POST":
        check_in = request.form.get("check_in", "")
        check_out = request.form.get("check_out", "")
        guests = request.form.get("guests", "2", type=int)
        room_type_id = request.form.get("room_type", type=int)
        room_id = request.form.get("room_id", type=int)

        from app.utils.helpers import parse_date

        ci = parse_date(check_in)
        co = parse_date(check_out)
        err, dates = validate_dates(ci, co)
        if err:
            error = err
        else:
            ci, co = dates
            available = available_rooms(ci, co, room_type_id=room_type_id, capacity=guests)
            if room_id:
                selected_room = Room.query.get(room_id)
                if selected_room and selected_room not in available:
                    error = "Sorry, this room is not available for the selected dates."
                    selected_room = None
                elif selected_room:
                    nights = (co - ci).days
                    tax_rate = float(settings_value("tax_rate", "0") or 0)
                    summary = compute_stay(
                        selected_room.price, nights, tax_rate=tax_rate
                    )
                    summary["nights"] = nights
                    summary["room"] = selected_room
                    summary["check_in"] = ci
                    summary["check_out"] = co
                    summary["guests"] = guests
                    summary["room_type_id"] = room_type_id
    else:
        if check_in and check_out:
            from app.utils.helpers import parse_date

            ci = parse_date(check_in)
            co = parse_date(check_out)
            err, dates = validate_dates(ci, co)
            if not err:
                available = available_rooms(ci, co, room_type_id=room_type_id, capacity=guests)

    return render_template(
        "public/reservation.html",
        room_types=_active_room_types(),
        available=available,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        room_type_id=room_type_id,
        error=error,
        summary=summary,
    )


@public_bp.route("/reservation/confirm", methods=["POST"])
def reservation_confirm():
    """Create a reservation from the booking summary."""
    from app.utils.helpers import parse_date

    check_in = request.form.get("check_in", "")
    check_out = request.form.get("check_out", "")
    room_id = request.form.get("room_id", type=int)
    guests = request.form.get("guests", "2", type=int)
    room_type_id = request.form.get("room_type_id", type=int)
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    special_request = request.form.get("special_request", "").strip()

    ci = parse_date(check_in)
    co = parse_date(check_out)
    err, dates = validate_dates(ci, co)
    if err:
        flash(err, "error")
        return redirect(url_for("public.reservation"))

    room = Room.query.get(room_id)
    if not room:
        flash("Please select a valid room.", "error")
        return redirect(url_for("public.reservation"))

    # Re-verify availability to prevent double booking.
    from app.services.availability import room_available_for_dates

    if not room_available_for_dates(room, ci, co):
        flash("Sorry, this room is not available for the selected dates.", "error")
        return redirect(url_for("public.reservation"))

    if not full_name or not email:
        flash("Please provide your name and email to complete the booking.", "error")
        return redirect(url_for("public.reservation"))

    # Find or create the guest.
    guest = None
    if current_user.is_authenticated:
        guest = Guest.query.filter_by(user_id=current_user.id).first()
    if not guest:
        guest = Guest.query.filter_by(email=email.lower()).first()
    if not guest:
        guest = Guest(
            guest_code=simple_code("GST"),
            full_name=full_name,
            email=email.lower(),
            phone=phone,
            user_id=current_user.id if current_user.is_authenticated else None,
        )
        db.session.add(guest)
        db.session.flush()

    nights = (co - ci).days
    tax_rate = float(settings_value("tax_rate", "0") or 0)
    calc = compute_stay(room.price, nights, tax_rate=tax_rate)

    reservation = Reservation(
        reservation_code=simple_code("RES"),
        guest_id=guest.id,
        room_id=room.id,
        room_type_id=room.room_type_id,
        check_in_date=ci,
        check_out_date=co,
        adults=guests,
        children=0,
        special_request=special_request or None,
        source="website",
        room_rate=room.price,
        nights=nights,
        room_charge=calc["room_charge"],
        additional_charges=calc["additional_charges"],
        discount=calc["discount"],
        tax_rate=calc["tax_rate"],
        tax_amount=calc["tax_amount"],
        total_amount=calc["total"],
        paid_amount=0,
        status="pending",
        payment_status="pending",
        created_by=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(reservation)
    db.session.commit()

    notify(
        "New reservation received",
        f"{guest.full_name} booked {room.room_number} from {ci} to {co}.",
        "booking",
        url_for("admin.reservation_detail", reservation_id=reservation.id),
    )
    log_activity(
        "Reservation created",
        "reservation",
        reservation.id,
        f"{reservation.reservation_code} created via website",
    )
    db.session.commit()

    return redirect(url_for("public.confirmation", reservation_id=reservation.id))


@public_bp.route("/confirmation/<int:reservation_id>")
def confirmation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    return render_template("public/confirmation.html", reservation=reservation)


@public_bp.route("/about")
def about():
    story = (
        AboutContent.query.filter_by(
            section=AboutContent.SECTION_STORY, is_active=True
        )
        .order_by(AboutContent.display_order, AboutContent.id)
        .all()
    )
    highlights = (
        AboutContent.query.filter_by(
            section=AboutContent.SECTION_HIGHLIGHT, is_active=True
        )
        .order_by(AboutContent.display_order, AboutContent.id)
        .all()
    )
    return render_template(
        "public/about.html", about_story=story, about_highlights=highlights
    )


@public_bp.route("/services")
def services():
    services = (
        Service.query.filter_by(is_active=True)
        .order_by(Service.display_order, Service.id)
        .all()
    )
    return render_template("public/services.html", services=services)


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            subject=form.subject.data,
            message=form.message.data,
        )
        db.session.add(message)
        db.session.commit()
        notify(
            "New contact message",
            f"{message.name} sent a message: {message.subject or 'No subject'}",
            "info",
            url_for("admin.contact_messages"),
        )
        db.session.commit()
        flash("Thank you! Your message has been sent. We will reply shortly.", "success")
        return redirect(url_for("public.contact"))
    return render_template("public/contact.html", form=form)