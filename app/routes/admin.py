"""Admin blueprint: dashboard and all management modules."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    jsonify,
)
from flask_login import current_user
from sqlalchemy import func, or_

from app import db
from app.models import (
    User,
    Staff,
    Guest,
    RoomType,
    Room,
    Reservation,
    CheckIn,
    CheckOut,
    Payment,
    Invoice,
    HousekeepingTask,
    MaintenanceTask,
    HeroBanner,
    PromotionalBanner,
    WebsiteSetting,
    Service,
    ContactMessage,
    AboutContent,
    Notification,
    ActivityLog,
    RoomImage,
    SpecialOffer,
    ThemeSetting,
)
from app.forms import (
    GuestForm,
    RoomTypeForm,
    RoomForm,
    ReservationForm,
    PaymentForm,
    HousekeepingForm,
    MaintenanceForm,
    HeroBannerForm,
    PromoBannerForm,
    ServiceForm,
    AboutContentForm,
    StaffForm,
    CheckInForm,
    CheckOutForm,
    AccountForm,
    RoomImageForm,
    SpecialOfferForm,
    ThemeForm,
)
from app.utils.decorators import staff_required, admin_required, permission_required
from app.utils.helpers import (
    simple_code,
    save_upload,
    delete_upload,
    parse_date,
    settings_value,
)
from app.utils.constants import (
    ROOM_STATUSES,
    RESERVATION_STATUSES,
    PAYMENT_STATUSES,
    PAYMENT_METHODS,
    PERMISSIONS,
    DEFAULT_SETTINGS,
    UNASSIGNABLE_ROOM_STATUSES,
    BLOCKING_RESERVATION_STATUSES,
)
from app.services.availability import (
    available_rooms,
    room_available_for_dates,
    validate_dates,
)
from app.services.billing import compute_stay, derive_payment_status, money
from app.services.notifications import notify, log_activity

admin_bp = Blueprint("admin", __name__)


def _ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")


def _commit_log(action, entity_type=None, entity_id=None, details=None, notify_title=None,
                notify_msg="", notify_cat="info", notify_link=None):
    db.session.commit()
    log_activity(action, entity_type, entity_id, details, user=current_user, ip=_ip())
    if notify_title:
        notify(notify_title, notify_msg, notify_cat, notify_link)
    db.session.commit()


# ===========================================================================
# Dashboard
# ===========================================================================
@admin_bp.route("/")
@staff_required
def dashboard():
    today = date.today()

    total_rooms = Room.query.count()
    available = Room.query.filter_by(status="available").count()
    reserved = Room.query.filter_by(status="reserved").count()
    occupied = Room.query.filter_by(status="occupied").count()
    cleaning = Room.query.filter_by(status="cleaning").count()
    maintenance = Room.query.filter_by(status="maintenance").count()

    today_checkins = Reservation.query.filter(
        Reservation.check_in_date == today,
        Reservation.status.in_(["pending", "confirmed", "checked_in"]),
    ).count()
    today_checkouts = Reservation.query.filter(
        Reservation.check_out_date == today,
        Reservation.status.in_(["checked_in", "confirmed", "pending"]),
    ).count()

    pending_payments = (
        db.session.query(func.coalesce(func.sum(Reservation.total_amount - Reservation.paid_amount), 0))
        .filter(Reservation.status.in_(["pending", "confirmed", "checked_in"]))
        .scalar()
    )

    revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.received_at >= datetime.combine(today, datetime.min.time()))
        .scalar()
    )

    recent_reservations = (
        Reservation.query.order_by(Reservation.created_at.desc()).limit(6).all()
    )
    recent_payments = Payment.query.order_by(Payment.received_at.desc()).limit(6).all()
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(8).all()
    recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(6).all()

    return render_template(
        "admin/dashboard.html",
        stats={
            "total_rooms": total_rooms,
            "available": available,
            "reserved": reserved,
            "occupied": occupied,
            "cleaning": cleaning,
            "maintenance": maintenance,
            "today_checkins": today_checkins,
            "today_checkouts": today_checkouts,
            "pending_payments": pending_payments,
            "revenue": revenue,
        },
        recent_reservations=recent_reservations,
        recent_payments=recent_payments,
        recent_activity=recent_activity,
        recent_notifications=recent_notifications,
    )


# ===========================================================================
# Rooms
# ===========================================================================
@admin_bp.route("/rooms")
@permission_required("rooms.view")
def rooms():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    room_type = request.args.get("room_type", type=int)
    page = request.args.get("page", 1, type=int)

    query = Room.query
    if q:
        query = query.filter(Room.room_number.ilike(f"%{q}%"))
    if status:
        query = query.filter(Room.status == status)
    if room_type:
        query = query.filter(Room.room_type_id == room_type)

    pagination = query.order_by(Room.floor, Room.room_number).paginate(
        page=page, per_page=12, error_out=False
    )
    return render_template(
        "admin/rooms.html",
        pagination=pagination,
        room_types=RoomType.query.all(),
        q=q,
        status=status,
        room_type=room_type,
        statuses=ROOM_STATUSES,
    )


@admin_bp.route("/rooms/new", methods=["GET", "POST"])
@permission_required("rooms.create")
def room_new():
    form = RoomForm()
    if form.validate_on_submit():
        room = Room(
            room_number=form.room_number.data,
            room_type_id=form.room_type_id.data,
            floor=form.floor.data or 1,
            price=form.price.data,
            capacity=form.capacity.data,
            bed_type=form.bed_type.data,
            description=form.description.data,
            facilities=form.facilities.data,
            status=form.status.data,
            is_active=form.is_active.data,
        )
        db.session.add(room)
        db.session.flush()
        _commit_log(
            "Room added",
            "room",
            room.id,
            f"Room {room.room_number} created",
            "Room added",
            f"Room {room.room_number} has been added.",
            "success",
            url_for("admin.rooms"),
        )
        flash("Room added successfully.", "success")
        return redirect(url_for("admin.rooms"))
    return render_template("admin/room_form.html", form=form, title="Add Room")


@admin_bp.route("/rooms/<int:room_id>/edit", methods=["GET", "POST"])
@permission_required("rooms.edit")
def room_edit(room_id):
    room = Room.query.get_or_404(room_id)
    form = RoomForm(obj=room)
    form.room_id.data = room.id
    if form.validate_on_submit():
        room.room_number = form.room_number.data
        room.room_type_id = form.room_type_id.data
        room.floor = form.floor.data or 1
        room.price = form.price.data
        room.capacity = form.capacity.data
        room.bed_type = form.bed_type.data
        room.description = form.description.data
        room.facilities = form.facilities.data
        room.status = form.status.data
        room.is_active = form.is_active.data
        _commit_log(
            "Room updated",
            "room",
            room.id,
            f"Room {room.room_number} updated",
            "Room updated",
            f"Room {room.room_number} details were updated.",
            "info",
            url_for("admin.rooms"),
        )
        flash("Room updated successfully.", "success")
        return redirect(url_for("admin.rooms"))
    return render_template("admin/room_form.html", form=form, title="Edit Room", room=room)


@admin_bp.route("/rooms/<int:room_id>/status", methods=["POST"])
@permission_required("rooms.edit")
def room_status(room_id):
    room = Room.query.get_or_404(room_id)
    new_status = request.form.get("status", "")
    if new_status not in dict(ROOM_STATUSES):
        flash("Invalid room status.", "error")
        return redirect(url_for("admin.rooms"))
    old = room.status
    room.status = new_status
    _commit_log(
        "Room status changed",
        "room",
        room.id,
        f"Room {room.room_number} status changed from {old} to {new_status}",
        "Room status changed",
        f"Room {room.room_number} is now {new_status}.",
        "info",
        url_for("admin.rooms"),
    )
    flash(f"Room {room.room_number} marked as {new_status}.", "success")
    return redirect(request.referrer or url_for("admin.rooms"))


@admin_bp.route("/rooms/<int:room_id>/delete", methods=["POST"])
@permission_required("rooms.delete")
def room_delete(room_id):
    room = Room.query.get_or_404(room_id)
    if room.reservations.count() > 0:
        flash("This room has reservation history and cannot be deleted.", "error")
        return redirect(url_for("admin.rooms"))
    number = room.room_number
    db.session.delete(room)
    _commit_log(
        "Room deleted",
        "room",
        room_id,
        f"Room {number} deleted",
        "Room deleted",
        f"Room {number} was removed.",
        "warning",
    )
    flash("Room deleted.", "success")
    return redirect(url_for("admin.rooms"))


# ===========================================================================
# Room types
# ===========================================================================
@admin_bp.route("/room-types")
@permission_required("room_types.view")
def room_types():
    return render_template(
        "admin/room_types.html", room_types=RoomType.query.order_by(RoomType.base_price).all()
    )


@admin_bp.route("/room-types/new", methods=["GET", "POST"])
@permission_required("room_types.manage")
def room_type_new():
    form = RoomTypeForm()
    if form.validate_on_submit():
        image = save_upload(form.image.data, "room_types") if form.image.data else None
        rt = RoomType(
            name=form.name.data,
            slug=form.name.data.lower().replace(" ", "-"),
            description=form.description.data,
            base_price=form.base_price.data,
            capacity=form.capacity.data,
            bed_type=form.bed_type.data,
            facilities=form.facilities.data,
            image=image,
            is_active=form.is_active.data,
        )
        db.session.add(rt)
        db.session.flush()
        _commit_log(
            "Room type added",
            "room_type",
            rt.id,
            f"Room type {rt.name} created",
            "Room type added",
            f"Room type {rt.name} has been added.",
            "success",
            url_for("admin.room_types"),
        )
        flash("Room type added.", "success")
        return redirect(url_for("admin.room_types"))
    return render_template("admin/room_type_form.html", form=form, title="Add Room Type")


@admin_bp.route("/room-types/<int:rt_id>/edit", methods=["GET", "POST"])
@permission_required("room_types.manage")
def room_type_edit(rt_id):
    rt = RoomType.query.get_or_404(rt_id)
    form = RoomTypeForm(obj=rt)
    if form.validate_on_submit():
        image = save_upload(form.image.data, "room_types") if form.image.data else None
        if image:
            delete_upload(rt.image)
            rt.image = image
        rt.name = form.name.data
        rt.slug = form.name.data.lower().replace(" ", "-")
        rt.description = form.description.data
        rt.base_price = form.base_price.data
        rt.capacity = form.capacity.data
        rt.bed_type = form.bed_type.data
        rt.facilities = form.facilities.data
        rt.is_active = form.is_active.data
        _commit_log(
            "Room type updated",
            "room_type",
            rt.id,
            f"Room type {rt.name} updated",
            "Room type updated",
            f"Room type {rt.name} was updated.",
            "info",
            url_for("admin.room_types"),
        )
        flash("Room type updated.", "success")
        return redirect(url_for("admin.room_types"))
    return render_template("admin/room_type_form.html", form=form, title="Edit Room Type", rt=rt)


@admin_bp.route("/room-types/<int:rt_id>/delete", methods=["POST"])
@permission_required("room_types.manage")
def room_type_delete(rt_id):
    rt = RoomType.query.get_or_404(rt_id)
    if rt.rooms.count() > 0:
        flash("This room type has rooms assigned and cannot be deleted.", "error")
        return redirect(url_for("admin.room_types"))
    db.session.delete(rt)
    _commit_log(
        "Room type deleted",
        "room_type",
        rt_id,
        f"Room type {rt.name} deleted",
        "Room type deleted",
        f"Room type {rt.name} was removed.",
        "warning",
    )
    flash("Room type deleted.", "success")
    return redirect(url_for("admin.room_types"))


# ===========================================================================
# Reservations
# ===========================================================================
@admin_bp.route("/reservations")
@permission_required("reservations.view")
def reservations():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    payment_status = request.args.get("payment_status", "")
    date_from = parse_date(request.args.get("date_from", ""))
    date_to = parse_date(request.args.get("date_to", ""))
    page = request.args.get("page", 1, type=int)

    query = Reservation.query
    if q:
        query = query.join(Guest).filter(
            or_(
                Reservation.reservation_code.ilike(f"%{q}%"),
                Guest.full_name.ilike(f"%{q}%"),
                Guest.phone.ilike(f"%{q}%"),
            )
        )
    if status:
        query = query.filter(Reservation.status == status)
    if payment_status:
        query = query.filter(Reservation.payment_status == payment_status)
    if date_from:
        query = query.filter(Reservation.check_in_date >= date_from)
    if date_to:
        query = query.filter(Reservation.check_out_date <= date_to)

    pagination = query.order_by(Reservation.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    return render_template(
        "admin/reservations.html",
        pagination=pagination,
        q=q,
        status=status,
        payment_status=payment_status,
        date_from=request.args.get("date_from", ""),
        date_to=request.args.get("date_to", ""),
        statuses=RESERVATION_STATUSES,
        payment_statuses=PAYMENT_STATUSES,
    )


@admin_bp.route("/reservations/new", methods=["GET", "POST"])
@permission_required("reservations.create")
def reservation_new():
    form = ReservationForm()
    if Guest.query.count() == 0:
        flash("You need to add a guest before creating a reservation.", "error")
        return redirect(url_for("admin.guest_new", next="admin.reservation_new"))
    if form.validate_on_submit():
        guest = Guest.query.get(form.guest_id.data)
        room = Room.query.get(form.room_id.data)
        ci, co = form.check_in_date.data, form.check_out_date.data

        err, _ = validate_dates(ci, co)
        if err:
            flash(err, "error")
            return render_template("admin/reservation_form.html", form=form, title="New Reservation")

        if not room_available_for_dates(room, ci, co):
            flash("This room is not available for the selected dates.", "error")
            return render_template("admin/reservation_form.html", form=form, title="New Reservation")

        nights = (co - ci).days
        calc = compute_stay(
            form.room_rate.data, nights, form.additional_charges.data or 0,
            form.discount.data or 0, form.tax_rate.data or 0,
        )
        reservation = Reservation(
            reservation_code=simple_code("RES"),
            guest_id=guest.id,
            room_id=room.id,
            room_type_id=room.room_type_id,
            check_in_date=ci,
            check_out_date=co,
            adults=form.adults.data,
            children=form.children.data or 0,
            special_request=form.special_request.data,
            source=form.source.data,
            room_rate=form.room_rate.data,
            nights=nights,
            room_charge=calc["room_charge"],
            additional_charges=calc["additional_charges"],
            discount=calc["discount"],
            tax_rate=calc["tax_rate"],
            tax_amount=calc["tax_amount"],
            total_amount=calc["total"],
            paid_amount=0,
            status=form.status.data,
            payment_status="pending",
            created_by=current_user.id,
        )
        db.session.add(reservation)
        db.session.flush()
        if room.status == "available":
            room.status = "reserved"
        _commit_log(
            "Reservation created",
            "reservation",
            reservation.id,
            f"{reservation.reservation_code} created for {guest.full_name}",
            "Reservation created",
            f"Reservation {reservation.reservation_code} for {guest.full_name}.",
            "success",
            url_for("admin.reservation_detail", reservation_id=reservation.id),
        )
        flash("Reservation created.", "success")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))
    return render_template("admin/reservation_form.html", form=form, title="New Reservation")


@admin_bp.route("/reservations/<int:reservation_id>")
@permission_required("reservations.view")
def reservation_detail(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    return render_template("admin/reservation_detail.html", reservation=reservation)


@admin_bp.route("/reservations/<int:reservation_id>/edit", methods=["GET", "POST"])
@permission_required("reservations.edit")
def reservation_edit(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    form = ReservationForm(obj=reservation)
    if form.validate_on_submit():
        guest = Guest.query.get(form.guest_id.data)
        room = Room.query.get(form.room_id.data)
        ci, co = form.check_in_date.data, form.check_out_date.data

        err, _ = validate_dates(ci, co)
        if err:
            flash(err, "error")
            return render_template("admin/reservation_form.html", form=form, title="Edit Reservation", reservation=reservation)

        if not room_available_for_dates(room, ci, co, exclude_reservation_id=reservation.id):
            flash("This room is not available for the selected dates.", "error")
            return render_template("admin/reservation_form.html", form=form, title="Edit Reservation", reservation=reservation)

        old_room = reservation.room
        nights = (co - ci).days
        calc = compute_stay(
            form.room_rate.data, nights, form.additional_charges.data or 0,
            form.discount.data or 0, form.tax_rate.data or 0,
        )

        reservation.guest_id = guest.id
        reservation.room_id = room.id
        reservation.room_type_id = room.room_type_id
        reservation.check_in_date = ci
        reservation.check_out_date = co
        reservation.adults = form.adults.data
        reservation.children = form.children.data or 0
        reservation.special_request = form.special_request.data
        reservation.source = form.source.data
        reservation.room_rate = form.room_rate.data
        reservation.nights = nights
        reservation.room_charge = calc["room_charge"]
        reservation.additional_charges = calc["additional_charges"]
        reservation.discount = calc["discount"]
        reservation.tax_rate = calc["tax_rate"]
        reservation.tax_amount = calc["tax_amount"]
        reservation.total_amount = calc["total"]
        reservation.status = form.status.data
        reservation.payment_status = derive_payment_status(calc["total"], reservation.paid_amount)

        if old_room and old_room.id != room.id:
            if old_room.status == "reserved" and not old_room.reservations.filter(
                Reservation.status.in_(BLOCKING_RESERVATION_STATUSES), Reservation.id != reservation.id
            ).first():
                old_room.status = "available"
            if room.status == "available":
                room.status = "reserved"

        _commit_log(
            "Reservation updated",
            "reservation",
            reservation.id,
            f"{reservation.reservation_code} updated",
            "Reservation updated",
            f"Reservation {reservation.reservation_code} was updated.",
            "info",
            url_for("admin.reservation_detail", reservation_id=reservation.id),
        )
        flash("Reservation updated.", "success")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))
    return render_template("admin/reservation_form.html", form=form, title="Edit Reservation", reservation=reservation)


@admin_bp.route("/reservations/<int:reservation_id>/confirm", methods=["POST"])
@permission_required("reservations.edit")
def reservation_confirm(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status == "pending":
        reservation.status = "confirmed"
        if reservation.room and reservation.room.status == "available":
            reservation.room.status = "reserved"
        _commit_log(
            "Reservation confirmed",
            "reservation",
            reservation.id,
            f"{reservation.reservation_code} confirmed",
            "Reservation confirmed",
            f"Reservation {reservation.reservation_code} is confirmed.",
            "success",
            url_for("admin.reservation_detail", reservation_id=reservation.id),
        )
        flash("Reservation confirmed.", "success")
    else:
        flash("Only pending reservations can be confirmed.", "warning")
    return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))


@admin_bp.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
@permission_required("reservations.cancel")
def reservation_cancel(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status in ("checked_out", "cancelled"):
        flash("This reservation cannot be cancelled.", "warning")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))

    reservation.status = "cancelled"
    if reservation.room and reservation.room.status == "reserved":
        reservation.room.status = "available"
    _commit_log(
        "Reservation cancelled",
        "reservation",
        reservation.id,
        f"{reservation.reservation_code} cancelled",
        "Booking cancelled",
        f"Reservation {reservation.reservation_code} was cancelled.",
        "warning",
        url_for("admin.reservations"),
    )
    flash("Reservation cancelled.", "success")
    return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))


@admin_bp.route("/reservations/<int:reservation_id>/delete", methods=["POST"])
@permission_required("reservations.delete")
def reservation_delete(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    code = reservation.reservation_code
    if reservation.payments.count() > 0:
        flash("This reservation has payments and cannot be deleted.", "error")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))
    if reservation.room and reservation.room.status == "reserved":
        reservation.room.status = "available"
    db.session.delete(reservation)
    _commit_log(
        "Reservation deleted",
        "reservation",
        reservation_id,
        f"{code} deleted",
        "Reservation deleted",
        f"Reservation {code} was deleted.",
        "warning",
    )
    flash("Reservation deleted.", "success")
    return redirect(url_for("admin.reservations"))


# ===========================================================================
# Guests
# ===========================================================================
@admin_bp.route("/guests")
@permission_required("guests.view")
def guests():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Guest.query
    if q:
        query = query.filter(
            or_(
                Guest.full_name.ilike(f"%{q}%"),
                Guest.email.ilike(f"%{q}%"),
                Guest.phone.ilike(f"%{q}%"),
                Guest.guest_code.ilike(f"%{q}%"),
            )
        )
    pagination = query.order_by(Guest.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template("admin/guests.html", pagination=pagination, q=q)


@admin_bp.route("/guests/new", methods=["GET", "POST"])
@permission_required("guests.create")
def guest_new():
    form = GuestForm()
    if form.validate_on_submit():
        guest = Guest(
            guest_code=simple_code("GST"),
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            city=form.city.data,
            country=form.country.data,
            id_type=form.id_type.data,
            id_number=form.id_number.data,
            notes=form.notes.data,
        )
        db.session.add(guest)
        db.session.flush()
        _commit_log(
            "Guest added",
            "guest",
            guest.id,
            f"Guest {guest.full_name} created",
            "Guest added",
            f"Guest {guest.full_name} has been added.",
            "success",
            url_for("admin.guest_detail", guest_id=guest.id),
        )
        flash("Guest added.", "success")
        next_url = request.args.get("next")
        if next_url:
            return redirect(url_for(next_url))
        return redirect(url_for("admin.guest_detail", guest_id=guest.id))
    return render_template("admin/guest_form.html", form=form, title="Add Guest")


@admin_bp.route("/guests/<int:guest_id>")
@permission_required("guests.view")
def guest_detail(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    reservations = guest.reservations.order_by(Reservation.created_at.desc()).all()
    return render_template("admin/guest_detail.html", guest=guest, reservations=reservations)


@admin_bp.route("/guests/<int:guest_id>/edit", methods=["GET", "POST"])
@permission_required("guests.edit")
def guest_edit(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    form = GuestForm(obj=guest)
    if form.validate_on_submit():
        guest.full_name = form.full_name.data
        guest.email = form.email.data
        guest.phone = form.phone.data
        guest.address = form.address.data
        guest.city = form.city.data
        guest.country = form.country.data
        guest.id_type = form.id_type.data
        guest.id_number = form.id_number.data
        guest.notes = form.notes.data
        _commit_log(
            "Guest updated",
            "guest",
            guest.id,
            f"Guest {guest.full_name} updated",
            "Guest updated",
            f"Guest {guest.full_name} was updated.",
            "info",
            url_for("admin.guest_detail", guest_id=guest.id),
        )
        flash("Guest updated.", "success")
        return redirect(url_for("admin.guest_detail", guest_id=guest.id))
    return render_template("admin/guest_form.html", form=form, title="Edit Guest", guest=guest)


@admin_bp.route("/guests/<int:guest_id>/delete", methods=["POST"])
@permission_required("guests.delete")
def guest_delete(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    if guest.reservations.count() > 0:
        flash("This guest has reservation history and cannot be deleted.", "error")
        return redirect(url_for("admin.guest_detail", guest_id=guest.id))
    name = guest.full_name
    db.session.delete(guest)
    _commit_log(
        "Guest deleted",
        "guest",
        guest_id,
        f"Guest {name} deleted",
        "Guest deleted",
        f"Guest {name} was removed.",
        "warning",
    )
    flash("Guest deleted.", "success")
    return redirect(url_for("admin.guests"))


# ===========================================================================
# Check-In Desk
# ===========================================================================
@admin_bp.route("/check-in", methods=["GET", "POST"])
@permission_required("checkin.manage")
def check_in():
    q = request.args.get("q", "").strip()
    results = []
    searched = False
    if request.method == "POST":
        q = request.form.get("q", "").strip()
        searched = True
        if q:
            results = (
                Reservation.query.join(Guest)
                .filter(
                    Reservation.status.in_(["pending", "confirmed"]),
                    or_(
                        Reservation.reservation_code.ilike(f"%{q}%"),
                        Guest.full_name.ilike(f"%{q}%"),
                        Guest.phone.ilike(f"%{q}%"),
                        Reservation.room.has(Room.room_number.ilike(f"%{q}%")),
                    ),
                )
                .order_by(Reservation.check_in_date)
                .all()
            )
    elif q:
        searched = True
        results = (
            Reservation.query.join(Guest)
            .filter(
                Reservation.status.in_(["pending", "confirmed"]),
                or_(
                    Reservation.reservation_code.ilike(f"%{q}%"),
                    Guest.full_name.ilike(f"%{q}%"),
                    Guest.phone.ilike(f"%{q}%"),
                    Reservation.room.has(Room.room_number.ilike(f"%{q}%")),
                ),
            )
            .order_by(Reservation.check_in_date)
            .all()
        )
    return render_template("admin/check_in.html", q=q, results=results, searched=searched)


@admin_bp.route("/check-in/<int:reservation_id>", methods=["GET", "POST"])
@permission_required("checkin.manage")
def check_in_detail(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status not in ("pending", "confirmed"):
        flash("This reservation cannot be checked in.", "warning")
        return redirect(url_for("admin.check_in"))

    form = CheckInForm()
    if form.validate_on_submit():
        room = reservation.room
        if not room:
            flash("This reservation has no assigned room.", "error")
            return redirect(url_for("admin.check_in_detail", reservation_id=reservation.id))
        if room.status in UNASSIGNABLE_ROOM_STATUSES and room.status != "reserved":
            flash("The assigned room is not available for check-in.", "error")
            return redirect(url_for("admin.check_in_detail", reservation_id=reservation.id))

        checkin = CheckIn(
            reservation_id=reservation.id,
            checked_in_by=current_user.id,
            notes=form.notes.data,
        )
        db.session.add(checkin)
        reservation.status = "checked_in"
        room.status = "occupied"
        _commit_log(
            "Guest checked in",
            "reservation",
            reservation.id,
            f"{reservation.guest.full_name} checked into {room.room_number}",
            "Guest checked in",
            f"{reservation.guest.full_name} checked into room {room.room_number}.",
            "success",
            url_for("admin.reservation_detail", reservation_id=reservation.id),
        )
        flash("Check-in completed.", "success")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))
    return render_template("admin/check_in_detail.html", reservation=reservation, form=form)


# ===========================================================================
# Check-Out Desk
# ===========================================================================
@admin_bp.route("/check-out", methods=["GET", "POST"])
@permission_required("checkout.manage")
def check_out():
    q = request.args.get("q", "").strip()
    results = []
    searched = False
    if request.method == "POST":
        q = request.form.get("q", "").strip()
        searched = True
        if q:
            results = (
                Reservation.query.join(Guest)
                .filter(
                    Reservation.status == "checked_in",
                    or_(
                        Reservation.reservation_code.ilike(f"%{q}%"),
                        Guest.full_name.ilike(f"%{q}%"),
                        Guest.phone.ilike(f"%{q}%"),
                        Reservation.room.has(Room.room_number.ilike(f"%{q}%")),
                    ),
                )
                .order_by(Reservation.check_out_date)
                .all()
            )
    elif q:
        searched = True
        results = (
            Reservation.query.join(Guest)
            .filter(
                Reservation.status == "checked_in",
                or_(
                    Reservation.reservation_code.ilike(f"%{q}%"),
                    Guest.full_name.ilike(f"%{q}%"),
                    Guest.phone.ilike(f"%{q}%"),
                    Reservation.room.has(Room.room_number.ilike(f"%{q}%")),
                ),
            )
            .order_by(Reservation.check_out_date)
            .all()
        )
    return render_template("admin/check_out.html", q=q, results=results, searched=searched)


@admin_bp.route("/check-out/<int:reservation_id>", methods=["GET", "POST"])
@permission_required("checkout.manage")
def check_out_detail(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status != "checked_in":
        flash("This reservation is not currently checked in.", "warning")
        return redirect(url_for("admin.check_out"))

    form = CheckOutForm()
    if form.validate_on_submit():
        calc = compute_stay(
            reservation.room_rate,
            reservation.nights,
            reservation.additional_charges + (form.additional_charges.data or 0),
            reservation.discount + (form.discount.data or 0),
            reservation.tax_rate,
        )
        checkout = CheckOut(
            reservation_id=reservation.id,
            checked_out_by=current_user.id,
            notes=form.notes.data,
            final_total=calc["total"],
            final_paid=reservation.paid_amount,
        )
        db.session.add(checkout)
        reservation.status = "checked_out"
        reservation.total_amount = calc["total"]
        reservation.additional_charges = calc["additional_charges"]
        reservation.discount = calc["discount"]
        reservation.tax_amount = calc["tax_amount"]
        reservation.payment_status = derive_payment_status(calc["total"], reservation.paid_amount)

        room = reservation.room
        if room:
            room.status = "cleaning"
            task = HousekeepingTask(
                room_id=room.id,
                task_code=simple_code("HK"),
                status="pending",
                notes="Auto-created after guest check-out.",
            )
            db.session.add(task)
            db.session.flush()

        _commit_log(
            "Guest checked out",
            "reservation",
            reservation.id,
            f"{reservation.guest.full_name} checked out of {room.room_number if room else 'N/A'}",
            "Guest checked out",
            f"{reservation.guest.full_name} checked out. Room sent to cleaning.",
            "success",
            url_for("admin.reservation_detail", reservation_id=reservation.id),
        )
        flash("Check-out completed. Room marked for cleaning.", "success")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))

    return render_template("admin/check_out_detail.html", reservation=reservation, form=form)


# ===========================================================================
# Payments
# ===========================================================================
@admin_bp.route("/payments")
@permission_required("payments.view")
def payments():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Payment.query
    if q:
        query = query.join(Reservation).join(Guest).filter(
            or_(
                Payment.payment_code.ilike(f"%{q}%"),
                Reservation.reservation_code.ilike(f"%{q}%"),
                Guest.full_name.ilike(f"%{q}%"),
            )
        )
    pagination = query.order_by(Payment.received_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template("admin/payments.html", pagination=pagination, q=q)


@admin_bp.route("/reservations/<int:reservation_id>/pay", methods=["GET", "POST"])
@permission_required("payments.record")
def payment_new(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status == "cancelled":
        flash("Cannot record a payment for a cancelled reservation.", "error")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))

    form = PaymentForm()
    if form.validate_on_submit():
        amount = money(form.amount.data)
        if amount <= 0:
            flash("Payment amount must be greater than zero.", "error")
            return render_template("admin/payment_form.html", form=form, reservation=reservation)

        payment = Payment(
            payment_code=simple_code("PAY"),
            reservation_id=reservation.id,
            guest_id=reservation.guest_id,
            amount=amount,
            method=form.method.data,
            reference=form.reference.data,
            note=form.note.data,
            received_by=current_user.id,
        )
        db.session.add(payment)
        reservation.paid_amount = money(reservation.paid_amount) + amount
        reservation.payment_status = derive_payment_status(
            reservation.total_amount, reservation.paid_amount
        )

        # Update or create invoice
        invoice = reservation.invoices.first()
        if not invoice:
            invoice = Invoice(
                invoice_number=simple_code("INV"),
                reservation_id=reservation.id,
                room_charge=reservation.room_charge,
                additional_charges=reservation.additional_charges,
                discount=reservation.discount,
                tax_rate=reservation.tax_rate,
                tax_amount=reservation.tax_amount,
                total=reservation.total_amount,
                paid=reservation.paid_amount,
                status=reservation.payment_status,
                issued_by=current_user.id,
            )
            db.session.add(invoice)
        else:
            invoice.paid = reservation.paid_amount
            invoice.status = reservation.payment_status

        _commit_log(
            "Payment recorded",
            "payment",
            payment.id,
            f"{payment.payment_code} of {amount} for {reservation.reservation_code}",
            "Payment recorded",
            f"Payment of {amount} received for {reservation.reservation_code}.",
            "success",
            url_for("admin.payments"),
        )
        flash("Payment recorded successfully.", "success")
        return redirect(url_for("admin.reservation_detail", reservation_id=reservation.id))
    return render_template("admin/payment_form.html", form=form, reservation=reservation)


# ===========================================================================
# Invoices
# ===========================================================================
@admin_bp.route("/invoices")
@permission_required("invoices.view")
def invoices():
    page = request.args.get("page", 1, type=int)
    pagination = Invoice.query.order_by(Invoice.issued_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    return render_template("admin/invoices.html", pagination=pagination)


@admin_bp.route("/invoices/<int:invoice_id>")
@permission_required("invoices.view")
def invoice_detail(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template("admin/invoice_detail.html", invoice=invoice)


@admin_bp.route("/invoices/<int:invoice_id>/print")
@permission_required("invoices.print")
def invoice_print(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template("admin/invoice_print.html", invoice=invoice)


# ===========================================================================
# Housekeeping
# ===========================================================================
@admin_bp.route("/housekeeping")
@permission_required("housekeeping.manage")
def housekeeping():
    tasks = HousekeepingTask.query.order_by(HousekeepingTask.requested_at.desc()).all()
    rooms = Room.query.order_by(Room.room_number).all()
    return render_template("admin/housekeeping.html", tasks=tasks, rooms=rooms)


@admin_bp.route("/housekeeping/new", methods=["GET", "POST"])
@permission_required("housekeeping.manage")
def housekeeping_new():
    form = HousekeepingForm()
    if form.validate_on_submit():
        room = Room.query.get(form.room_id.data)
        task = HousekeepingTask(
            room_id=room.id,
            task_code=simple_code("HK"),
            status="pending",
            assigned_to=form.assigned_to.data,
            notes=form.notes.data,
        )
        db.session.add(task)
        if room.status == "available":
            room.status = "cleaning"
        _commit_log(
            "Housekeeping task created",
            "housekeeping",
            task.id,
            f"Cleaning requested for room {room.room_number}",
            "Cleaning required",
            f"Room {room.room_number} requires cleaning.",
            "warning",
            url_for("admin.housekeeping"),
        )
        flash("Housekeeping task created.", "success")
        return redirect(url_for("admin.housekeeping"))
    return render_template("admin/housekeeping_form.html", form=form)


@admin_bp.route("/housekeeping/<int:task_id>/status", methods=["POST"])
@permission_required("housekeeping.manage")
def housekeeping_status(task_id):
    task = HousekeepingTask.query.get_or_404(task_id)
    new_status = request.form.get("status", "")
    if new_status not in ("pending", "in_progress", "completed"):
        flash("Invalid status.", "error")
        return redirect(url_for("admin.housekeeping"))

    task.status = new_status
    if new_status == "in_progress" and not task.started_at:
        task.started_at = datetime.utcnow()
    if new_status == "completed":
        task.completed_at = datetime.utcnow()
        task.completed_by = current_user.full_name or current_user.username
        room = task.room
        if room and room.status == "cleaning":
            room.status = "available"
        _commit_log(
            "Housekeeping completed",
            "housekeeping",
            task.id,
            f"Room {task.room.room_number} cleaned and ready",
            "Room ready",
            f"Room {task.room.room_number} is clean and available.",
            "success",
            url_for("admin.housekeeping"),
        )
        flash("Housekeeping task completed. Room is now available.", "success")
        return redirect(url_for("admin.housekeeping"))

    _commit_log(
        "Housekeeping updated",
        "housekeeping",
        task.id,
        f"Task {task.task_code} set to {new_status}",
    )
    flash("Housekeeping task updated.", "success")
    return redirect(url_for("admin.housekeeping"))


@admin_bp.route("/housekeeping/<int:task_id>/delete", methods=["POST"])
@permission_required("housekeeping.manage")
def housekeeping_delete(task_id):
    task = HousekeepingTask.query.get_or_404(task_id)
    db.session.delete(task)
    _commit_log("Housekeeping task deleted", "housekeeping", task_id, f"Task {task.task_code} deleted")
    flash("Housekeeping task deleted.", "success")
    return redirect(url_for("admin.housekeeping"))


# ===========================================================================
# Maintenance
# ===========================================================================
@admin_bp.route("/maintenance")
@permission_required("maintenance.manage")
def maintenance():
    tasks = MaintenanceTask.query.order_by(MaintenanceTask.created_at.desc()).all()
    rooms = Room.query.order_by(Room.room_number).all()
    return render_template("admin/maintenance.html", tasks=tasks, rooms=rooms)


@admin_bp.route("/maintenance/new", methods=["GET", "POST"])
@permission_required("maintenance.manage")
def maintenance_new():
    form = MaintenanceForm()
    if form.validate_on_submit():
        room = Room.query.get(form.room_id.data)
        task = MaintenanceTask(
            room_id=room.id,
            task_code=simple_code("MNT"),
            reason=form.reason.data,
            notes=form.notes.data,
            status="open",
            requested_by=current_user.full_name or current_user.username,
        )
        db.session.add(task)
        room.status = "maintenance"
        _commit_log(
            "Maintenance task created",
            "maintenance",
            task.id,
            f"Room {room.room_number} under maintenance: {form.reason.data}",
            "Maintenance required",
            f"Room {room.room_number} requires maintenance.",
            "warning",
            url_for("admin.maintenance"),
        )
        flash("Maintenance task created. Room marked as maintenance.", "success")
        return redirect(url_for("admin.maintenance"))
    return render_template("admin/maintenance_form.html", form=form)


@admin_bp.route("/maintenance/<int:task_id>/status", methods=["POST"])
@permission_required("maintenance.manage")
def maintenance_status(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    new_status = request.form.get("status", "")
    if new_status not in ("open", "in_progress", "completed"):
        flash("Invalid status.", "error")
        return redirect(url_for("admin.maintenance"))

    task.status = new_status
    if new_status == "completed":
        task.resolved_at = datetime.utcnow()
        room = task.room
        if room and room.status == "maintenance":
            room.status = "available"
        _commit_log(
            "Maintenance completed",
            "maintenance",
            task.id,
            f"Room {task.room.room_number} maintenance complete",
            "Maintenance complete",
            f"Room {task.room.room_number} is back in service.",
            "success",
            url_for("admin.maintenance"),
        )
        flash("Maintenance completed. Room is available again.", "success")
        return redirect(url_for("admin.maintenance"))

    _commit_log("Maintenance updated", "maintenance", task.id, f"Task {task.task_code} set to {new_status}")
    flash("Maintenance task updated.", "success")
    return redirect(url_for("admin.maintenance"))


@admin_bp.route("/maintenance/<int:task_id>/delete", methods=["POST"])
@permission_required("maintenance.manage")
def maintenance_delete(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    db.session.delete(task)
    _commit_log("Maintenance task deleted", "maintenance", task_id, f"Task {task.task_code} deleted")
    flash("Maintenance task deleted.", "success")
    return redirect(url_for("admin.maintenance"))


# ===========================================================================
# Booking calendar
# ===========================================================================
@admin_bp.route("/calendar")
@permission_required("calendar.view")
def calendar():
    month = request.args.get("month", type=int) or date.today().month
    year = request.args.get("year", type=int) or date.today().year
    if not (1 <= month <= 12):
        month = date.today().month
    if not (1900 <= year <= 2100):
        year = date.today().year

    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)

    reservations = (
        Reservation.query.filter(
            Reservation.status.in_(BLOCKING_RESERVATION_STATUSES),
            Reservation.check_in_date <= last,
            Reservation.check_out_date >= first,
        )
        .order_by(Reservation.check_in_date)
        .all()
    )

    # Build a day -> list of reservations map
    days = {}
    for res in reservations:
        start = max(res.check_in_date, first)
        end = min(res.check_out_date - timedelta(days=1), last)
        d = start
        while d <= end:
            days.setdefault(d.day, []).append(res)
            d += timedelta(days=1)

    return render_template(
        "admin/calendar.html",
        month=month,
        year=year,
        first=first,
        last=last,
        days=days,
        reservations=reservations,
        today=date.today(),
    )


# ===========================================================================
# Reports
# ===========================================================================
@admin_bp.route("/reports")
@permission_required("reports.view")
def reports():
    report_type = request.args.get("type", "reservations")
    date_from = parse_date(request.args.get("date_from", ""), date.today() - timedelta(days=30))
    date_to = parse_date(request.args.get("date_to", ""), date.today())

    rows = []
    summary = {}

    if report_type == "reservations":
        rows = (
            Reservation.query.filter(
                Reservation.created_at >= datetime.combine(date_from, datetime.min.time()),
                Reservation.created_at <= datetime.combine(date_to, datetime.max.time()),
            )
            .order_by(Reservation.created_at.desc())
            .all()
        )
        summary["count"] = len(rows)
        summary["total"] = sum(float(r.total_amount) for r in rows)
    elif report_type == "occupancy":
        rooms = Room.query.all()
        occupied_nights = 0
        total_nights = 0
        for room in rooms:
            for res in room.reservations.filter(Reservation.status.in_(BLOCKING_RESERVATION_STATUSES)).all():
                start = max(res.check_in_date, date_from)
                end = min(res.check_out_date, date_to)
                if end > start:
                    occupied_nights += (end - start).days
            total_nights += (date_to - date_from).days
        rows = rooms
        summary["occupied_nights"] = occupied_nights
        summary["total_nights"] = total_nights
        summary["occupancy_rate"] = round(occupied_nights / total_nights * 100, 1) if total_nights else 0
    elif report_type == "revenue":
        rows = (
            Payment.query.filter(
                Payment.received_at >= datetime.combine(date_from, datetime.min.time()),
                Payment.received_at <= datetime.combine(date_to, datetime.max.time()),
            )
            .order_by(Payment.received_at.desc())
            .all()
        )
        summary["count"] = len(rows)
        summary["total"] = sum(float(p.amount) for p in rows)
    elif report_type == "payments":
        rows = (
            Reservation.query.filter(
                Reservation.created_at >= datetime.combine(date_from, datetime.min.time()),
                Reservation.created_at <= datetime.combine(date_to, datetime.max.time()),
            )
            .order_by(Reservation.created_at.desc())
            .all()
        )
        summary["paid"] = sum(1 for r in rows if r.payment_status == "paid")
        summary["partial"] = sum(1 for r in rows if r.payment_status == "partially_paid")
        summary["pending"] = sum(1 for r in rows if r.payment_status == "pending")
        summary["outstanding"] = sum(float(r.remaining_amount) for r in rows)
    elif report_type == "guests":
        rows = (
            Guest.query.filter(
                Guest.created_at >= datetime.combine(date_from, datetime.min.time()),
                Guest.created_at <= datetime.combine(date_to, datetime.max.time()),
            )
            .order_by(Guest.created_at.desc())
            .all()
        )
        summary["count"] = len(rows)
    elif report_type == "checkins":
        rows = (
            CheckIn.query.filter(
                CheckIn.checked_in_at >= datetime.combine(date_from, datetime.min.time()),
                CheckIn.checked_in_at <= datetime.combine(date_to, datetime.max.time()),
            )
            .order_by(CheckIn.checked_in_at.desc())
            .all()
        )
        summary["count"] = len(rows)
    elif report_type == "checkouts":
        rows = (
            CheckOut.query.filter(
                CheckOut.checked_out_at >= datetime.combine(date_from, datetime.min.time()),
                CheckOut.checked_out_at <= datetime.combine(date_to, datetime.max.time()),
            )
            .order_by(CheckOut.checked_out_at.desc())
            .all()
        )
        summary["count"] = len(rows)
        summary["total"] = sum(float(c.final_total) for c in rows)
    elif report_type == "cancellations":
        rows = (
            Reservation.query.filter(
                Reservation.status == "cancelled",
                Reservation.created_at >= datetime.combine(date_from, datetime.min.time()),
                Reservation.created_at <= datetime.combine(date_to, datetime.max.time()),
            )
            .order_by(Reservation.created_at.desc())
            .all()
        )
        summary["count"] = len(rows)
    elif report_type == "room_performance":
        rows = Room.query.order_by(Room.room_number).all()
        summary["total"] = len(rows)

    return render_template(
        "admin/reports.html",
        report_type=report_type,
        date_from=date_from,
        date_to=date_to,
        rows=rows,
        summary=summary,
    )


# ===========================================================================
# Staff management
# ===========================================================================
@admin_bp.route("/staff")
@admin_required
def staff():
    staff_members = Staff.query.order_by(Staff.created_at.desc()).all()
    return render_template("admin/staff.html", staff_members=staff_members)


@admin_bp.route("/staff/new", methods=["GET", "POST"])
@admin_required
def staff_new():
    form = StaffForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("That username is already taken.", "error")
            return render_template("admin/staff_form.html", form=form, title="Add Staff")
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("That email is already in use.", "error")
            return render_template("admin/staff_form.html", form=form, title="Add Staff")
        if not form.password.data:
            flash("A password is required for a new staff account.", "error")
            return render_template("admin/staff_form.html", form=form, title="Add Staff")

        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            full_name=form.full_name.data,
            role="staff",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        staff = Staff(
            user_id=user.id,
            job_title=form.job_title.data,
            phone=form.phone.data,
            is_active=form.is_active.data,
            permissions=",".join(form.permissions.data),
        )
        db.session.add(staff)
        db.session.flush()
        _commit_log(
            "Staff added",
            "staff",
            staff.id,
            f"Staff account created for {form.full_name.data}",
            "Staff added",
            f"Staff account created for {form.full_name.data}.",
            "success",
            url_for("admin.staff"),
        )
        flash("Staff account created.", "success")
        return redirect(url_for("admin.staff"))
    return render_template("admin/staff_form.html", form=form, title="Add Staff")


@admin_bp.route("/staff/<int:staff_id>/edit", methods=["GET", "POST"])
@admin_required
def staff_edit(staff_id):
    staff = Staff.query.get_or_404(staff_id)
    user = staff.user
    form = StaffForm(obj=user)
    form.permissions.data = staff.permission_list
    if form.validate_on_submit():
        if User.query.filter(User.username == form.username.data, User.id != user.id).first():
            flash("That username is already taken.", "error")
            return render_template("admin/staff_form.html", form=form, title="Edit Staff", staff=staff)
        if User.query.filter(User.email == form.email.data.lower(), User.id != user.id).first():
            flash("That email is already in use.", "error")
            return render_template("admin/staff_form.html", form=form, title="Edit Staff", staff=staff)

        user.username = form.username.data
        user.email = form.email.data.lower()
        user.full_name = form.full_name.data
        if form.password.data:
            user.set_password(form.password.data)
        staff.job_title = form.job_title.data
        staff.phone = form.phone.data
        staff.is_active = form.is_active.data
        staff.permissions = ",".join(form.permissions.data)
        _commit_log(
            "Staff updated",
            "staff",
            staff.id,
            f"Staff account updated for {user.full_name}",
            "Staff updated",
            f"Staff account for {user.full_name} was updated.",
            "info",
            url_for("admin.staff"),
        )
        flash("Staff account updated.", "success")
        return redirect(url_for("admin.staff"))
    return render_template("admin/staff_form.html", form=form, title="Edit Staff", staff=staff)


@admin_bp.route("/staff/<int:staff_id>/toggle", methods=["POST"])
@admin_required
def staff_toggle(staff_id):
    staff = Staff.query.get_or_404(staff_id)
    if staff.user.is_admin:
        flash("The administrator account cannot be deactivated.", "error")
        return redirect(url_for("admin.staff"))
    staff.is_active = not staff.is_active
    staff.user.is_active_account = staff.is_active
    _commit_log(
        "Staff status changed",
        "staff",
        staff.id,
        f"{staff.user.full_name} {'activated' if staff.is_active else 'deactivated'}",
        "Staff status changed",
        f"{staff.user.full_name} is now {'active' if staff.is_active else 'inactive'}.",
        "info",
        url_for("admin.staff"),
    )
    flash("Staff status updated.", "success")
    return redirect(url_for("admin.staff"))


@admin_bp.route("/staff/<int:staff_id>/delete", methods=["POST"])
@admin_required
def staff_delete(staff_id):
    staff = Staff.query.get_or_404(staff_id)
    if staff.user.is_admin:
        flash("The administrator account cannot be deleted.", "error")
        return redirect(url_for("admin.staff"))
    name = staff.user.full_name
    db.session.delete(staff)
    db.session.delete(staff.user)
    _commit_log("Staff deleted", "staff", staff_id, f"Staff account {name} deleted")
    flash("Staff account deleted.", "success")
    return redirect(url_for("admin.staff"))


# ===========================================================================
# Website content
# ===========================================================================
@admin_bp.route("/content")
@permission_required("content.manage")
def content():
    return render_template("admin/content.html")


@admin_bp.route("/content/hero-banners")
@permission_required("content.manage")
def hero_banners():
    banners = HeroBanner.query.order_by(HeroBanner.display_order, HeroBanner.id).all()
    return render_template("admin/hero_banners.html", banners=banners)


@admin_bp.route("/content/hero-banners/new", methods=["GET", "POST"])
@permission_required("content.manage")
def hero_banner_new():
    form = HeroBannerForm()
    if form.validate_on_submit():
        image = save_upload(form.image.data, "banners") if form.image.data else None
        banner = HeroBanner(
            title=form.title.data,
            subtitle=form.subtitle.data,
            description=form.description.data,
            image=image,
            cta_text=form.cta_text.data,
            cta_url=form.cta_url.data,
            cta2_text=form.cta2_text.data,
            cta2_url=form.cta2_url.data,
            animation=form.animation.data,
            display_order=form.display_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(banner)
        db.session.flush()
        _commit_log(
            "Banner added",
            "hero_banner",
            banner.id,
            f"Hero banner '{banner.title}' created",
            "Banner added",
            f"Hero banner '{banner.title}' was added.",
            "success",
            url_for("admin.hero_banners"),
        )
        flash("Hero banner added.", "success")
        return redirect(url_for("admin.hero_banners"))
    return render_template("admin/hero_banner_form.html", form=form, title="Add Hero Banner")


@admin_bp.route("/content/hero-banners/<int:banner_id>/edit", methods=["GET", "POST"])
@permission_required("content.manage")
def hero_banner_edit(banner_id):
    banner = HeroBanner.query.get_or_404(banner_id)
    form = HeroBannerForm(obj=banner)
    if form.validate_on_submit():
        image = save_upload(form.image.data, "banners") if form.image.data else None
        if image:
            delete_upload(banner.image)
            banner.image = image
        banner.title = form.title.data
        banner.subtitle = form.subtitle.data
        banner.description = form.description.data
        banner.cta_text = form.cta_text.data
        banner.cta_url = form.cta_url.data
        banner.cta2_text = form.cta2_text.data
        banner.cta2_url = form.cta2_url.data
        banner.animation = form.animation.data
        banner.display_order = form.display_order.data or 0
        banner.is_active = form.is_active.data
        _commit_log(
            "Banner edited",
            "hero_banner",
            banner.id,
            f"Hero banner '{banner.title}' updated",
            "Banner edited",
            f"Hero banner '{banner.title}' was updated.",
            "info",
            url_for("admin.hero_banners"),
        )
        flash("Hero banner updated.", "success")
        return redirect(url_for("admin.hero_banners"))
    return render_template("admin/hero_banner_form.html", form=form, title="Edit Hero Banner", banner=banner)


@admin_bp.route("/content/hero-banners/<int:banner_id>/toggle", methods=["POST"])
@permission_required("content.manage")
def hero_banner_toggle(banner_id):
    banner = HeroBanner.query.get_or_404(banner_id)
    banner.is_active = not banner.is_active
    _commit_log(
        "Banner status changed",
        "hero_banner",
        banner.id,
        f"Hero banner '{banner.title}' {'enabled' if banner.is_active else 'disabled'}",
    )
    flash("Banner status updated.", "success")
    return redirect(url_for("admin.hero_banners"))


@admin_bp.route("/content/hero-banners/<int:banner_id>/delete", methods=["POST"])
@permission_required("content.manage")
def hero_banner_delete(banner_id):
    banner = HeroBanner.query.get_or_404(banner_id)
    delete_upload(banner.image)
    title = banner.title
    db.session.delete(banner)
    _commit_log(
        "Banner deleted",
        "hero_banner",
        banner_id,
        f"Hero banner '{title}' deleted",
        "Banner deleted",
        f"Hero banner '{title}' was removed.",
        "warning",
    )
    flash("Hero banner deleted.", "success")
    return redirect(url_for("admin.hero_banners"))


@admin_bp.route("/content/promo-banners")
@permission_required("content.manage")
def promo_banners():
    banners = PromotionalBanner.query.order_by(PromotionalBanner.display_order, PromotionalBanner.id).all()
    return render_template("admin/promo_banners.html", banners=banners)


@admin_bp.route("/content/promo-banners/new", methods=["GET", "POST"])
@permission_required("content.manage")
def promo_banner_new():
    form = PromoBannerForm()
    if form.validate_on_submit():
        image = save_upload(form.image.data, "banners") if form.image.data else None
        banner = PromotionalBanner(
            title=form.title.data,
            description=form.description.data,
            image=image,
            badge_text=form.badge_text.data,
            cta_text=form.cta_text.data,
            cta_url=form.cta_url.data,
            display_order=form.display_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(banner)
        db.session.flush()
        _commit_log(
            "Promo banner added",
            "promo_banner",
            banner.id,
            f"Promo banner '{banner.title}' created",
            "Promo banner added",
            f"Promo banner '{banner.title}' was added.",
            "success",
            url_for("admin.promo_banners"),
        )
        flash("Promotional banner added.", "success")
        return redirect(url_for("admin.promo_banners"))
    return render_template("admin/promo_banner_form.html", form=form, title="Add Promo Banner")


@admin_bp.route("/content/promo-banners/<int:banner_id>/edit", methods=["GET", "POST"])
@permission_required("content.manage")
def promo_banner_edit(banner_id):
    banner = PromotionalBanner.query.get_or_404(banner_id)
    form = PromoBannerForm(obj=banner)
    if form.validate_on_submit():
        image = save_upload(form.image.data, "banners") if form.image.data else None
        if image:
            delete_upload(banner.image)
            banner.image = image
        banner.title = form.title.data
        banner.description = form.description.data
        banner.badge_text = form.badge_text.data
        banner.cta_text = form.cta_text.data
        banner.cta_url = form.cta_url.data
        banner.display_order = form.display_order.data or 0
        banner.is_active = form.is_active.data
        _commit_log(
            "Promo banner edited",
            "promo_banner",
            banner.id,
            f"Promo banner '{banner.title}' updated",
            "Promo banner edited",
            f"Promo banner '{banner.title}' was updated.",
            "info",
            url_for("admin.promo_banners"),
        )
        flash("Promotional banner updated.", "success")
        return redirect(url_for("admin.promo_banners"))
    return render_template("admin/promo_banner_form.html", form=form, title="Edit Promo Banner", banner=banner)


@admin_bp.route("/content/promo-banners/<int:banner_id>/toggle", methods=["POST"])
@permission_required("content.manage")
def promo_banner_toggle(banner_id):
    banner = PromotionalBanner.query.get_or_404(banner_id)
    banner.is_active = not banner.is_active
    _commit_log(
        "Promo banner status changed",
        "promo_banner",
        banner.id,
        f"Promo banner '{banner.title}' {'enabled' if banner.is_active else 'disabled'}",
    )
    flash("Banner status updated.", "success")
    return redirect(url_for("admin.promo_banners"))


@admin_bp.route("/content/promo-banners/<int:banner_id>/delete", methods=["POST"])
@permission_required("content.manage")
def promo_banner_delete(banner_id):
    banner = PromotionalBanner.query.get_or_404(banner_id)
    delete_upload(banner.image)
    title = banner.title
    db.session.delete(banner)
    _commit_log(
        "Promo banner deleted",
        "promo_banner",
        banner_id,
        f"Promo banner '{title}' deleted",
        "Promo banner deleted",
        f"Promo banner '{title}' was removed.",
        "warning",
    )
    flash("Promotional banner deleted.", "success")
    return redirect(url_for("admin.promo_banners"))


@admin_bp.route("/content/branding", methods=["GET", "POST"])
@permission_required("content.manage")
def branding():
    if request.method == "POST":
        logo = request.files.get("logo")
        favicon = request.files.get("favicon")
        if logo and logo.filename:
            path = save_upload(logo, "branding", max_size=(240, 80))
            if path:
                old = settings_value("logo")
                delete_upload(old)
                _set_setting("logo", path)
        if favicon and favicon.filename:
            path = save_upload(favicon, "branding", max_size=(64, 64))
            if path:
                old = settings_value("favicon")
                delete_upload(old)
                _set_setting("favicon", path)

        for key in ("hotel_name", "tagline", "hotel_description"):
            if key in request.form:
                _set_setting(key, request.form.get(key, ""))

        for bkey in ("banner_rooms", "banner_about", "banner_contact", "banner_services"):
            f = request.files.get(bkey)
            if f and f.filename:
                path = save_upload(f, "banners", max_size=(1920, 480))
                if path:
                    old = settings_value(bkey)
                    delete_upload(old)
                    _set_setting(bkey, path)

        db.session.commit()

        _commit_log(
            "Branding updated",
            "branding",
            None,
            "Logo, favicon or hotel name updated",
            "Branding updated",
            "Website branding was updated.",
            "info",
            url_for("admin.branding"),
        )
        flash("Branding updated.", "success")
        return redirect(url_for("admin.branding"))

    return render_template("admin/branding.html")


@admin_bp.route("/content/settings", methods=["GET", "POST"])
@permission_required("content.manage")
def content_settings():
    if request.method == "POST":
        for key in DEFAULT_SETTINGS:
            if key in request.form:
                _set_setting(key, request.form.get(key, ""))
        _commit_log(
            "Settings updated",
            "settings",
            None,
            "Website settings updated",
            "Settings updated",
            "Website settings were updated.",
            "info",
            url_for("admin.content_settings"),
        )
        flash("Settings updated.", "success")
        return redirect(url_for("admin.content_settings"))
    return render_template(
        "admin/content_settings.html", DEFAULT_SETTINGS=DEFAULT_SETTINGS
    )


@admin_bp.route("/content/services")
@permission_required("content.manage")
def services():
    services = Service.query.order_by(Service.display_order, Service.id).all()
    return render_template("admin/services.html", services=services)


@admin_bp.route("/content/services/new", methods=["GET", "POST"])
@permission_required("content.manage")
def service_new():
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(
            name=form.name.data,
            description=form.description.data,
            icon=form.icon.data,
            display_order=form.display_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(service)
        db.session.flush()
        _commit_log(
            "Service added",
            "service",
            service.id,
            f"Service '{service.name}' created",
            "Service added",
            f"Service '{service.name}' was added.",
            "success",
            url_for("admin.services"),
        )
        flash("Service added.", "success")
        return redirect(url_for("admin.services"))
    return render_template("admin/service_form.html", form=form, title="Add Service")


@admin_bp.route("/content/services/<int:service_id>/edit", methods=["GET", "POST"])
@permission_required("content.manage")
def service_edit(service_id):
    service = Service.query.get_or_404(service_id)
    form = ServiceForm(obj=service)
    if form.validate_on_submit():
        service.name = form.name.data
        service.description = form.description.data
        service.icon = form.icon.data
        service.display_order = form.display_order.data or 0
        service.is_active = form.is_active.data
        _commit_log(
            "Service edited",
            "service",
            service.id,
            f"Service '{service.name}' updated",
            "Service edited",
            f"Service '{service.name}' was updated.",
            "info",
            url_for("admin.services"),
        )
        flash("Service updated.", "success")
        return redirect(url_for("admin.services"))
    return render_template("admin/service_form.html", form=form, title="Edit Service", service=service)


@admin_bp.route("/content/services/<int:service_id>/delete", methods=["POST"])
@permission_required("content.manage")
def service_delete(service_id):
    service = Service.query.get_or_404(service_id)
    name = service.name
    db.session.delete(service)
    _commit_log(
        "Service deleted",
        "service",
        service_id,
        f"Service '{name}' deleted",
        "Service deleted",
        f"Service '{name}' was removed.",
        "warning",
    )
    flash("Service deleted.", "success")
    return redirect(url_for("admin.services"))


@admin_bp.route("/content/about")
@permission_required("content.manage")
def about_content():
    items = AboutContent.query.order_by(
        AboutContent.section, AboutContent.display_order, AboutContent.id
    ).all()
    story = [i for i in items if i.section == AboutContent.SECTION_STORY]
    highlights = [i for i in items if i.section == AboutContent.SECTION_HIGHLIGHT]
    return render_template(
        "admin/about_content.html",
        story=story,
        highlights=highlights,
    )


@admin_bp.route("/content/about/new", methods=["GET", "POST"])
@permission_required("content.manage")
def about_content_new():
    form = AboutContentForm()
    if form.validate_on_submit():
        item = AboutContent(
            section=form.section.data,
            title=form.title.data,
            body=form.body.data,
            icon=form.icon.data or None,
            display_order=form.display_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(item)
        db.session.flush()
        _commit_log(
            "About content added",
            "about_content",
            item.id,
            f"About content '{item.title}' ({item.section}) created",
            "About content added",
            f"About content '{item.title}' was added.",
            "success",
            url_for("admin.about_content"),
        )
        flash("About content added.", "success")
        return redirect(url_for("admin.about_content"))
    return render_template(
        "admin/about_content_form.html", form=form, title="Add About Content"
    )


@admin_bp.route("/content/about/<int:item_id>/edit", methods=["GET", "POST"])
@permission_required("content.manage")
def about_content_edit(item_id):
    item = AboutContent.query.get_or_404(item_id)
    form = AboutContentForm(obj=item)
    if form.validate_on_submit():
        item.section = form.section.data
        item.title = form.title.data
        item.body = form.body.data
        item.icon = form.icon.data or None
        item.display_order = form.display_order.data or 0
        item.is_active = form.is_active.data
        _commit_log(
            "About content edited",
            "about_content",
            item.id,
            f"About content '{item.title}' ({item.section}) updated",
            "About content edited",
            f"About content '{item.title}' was updated.",
            "info",
            url_for("admin.about_content"),
        )
        flash("About content updated.", "success")
        return redirect(url_for("admin.about_content"))
    return render_template(
        "admin/about_content_form.html",
        form=form,
        title="Edit About Content",
        item=item,
    )


@admin_bp.route("/content/about/<int:item_id>/delete", methods=["POST"])
@permission_required("content.manage")
def about_content_delete(item_id):
    item = AboutContent.query.get_or_404(item_id)
    name = item.title
    db.session.delete(item)
    _commit_log(
        "About content deleted",
        "about_content",
        item_id,
        f"About content '{name}' deleted",
        "About content deleted",
        f"About content '{name}' was removed.",
        "warning",
    )
    flash("About content deleted.", "success")
    return redirect(url_for("admin.about_content"))


@admin_bp.route("/content/contact-messages")
@permission_required("content.manage")
def contact_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin/contact_messages.html", messages=messages)


@admin_bp.route("/content/contact-messages/<int:message_id>/read", methods=["POST"])
@permission_required("content.manage")
def contact_message_read(message_id):
    message = ContactMessage.query.get_or_404(message_id)
    message.is_read = True
    db.session.commit()
    flash("Message marked as read.", "success")
    return redirect(url_for("admin.contact_messages"))


@admin_bp.route("/content/contact-messages/<int:message_id>/delete", methods=["POST"])
@permission_required("content.manage")
def contact_message_delete(message_id):
    message = ContactMessage.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash("Message deleted.", "success")
    return redirect(url_for("admin.contact_messages"))


def _set_setting(key, value):
    setting = WebsiteSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        db.session.add(WebsiteSetting(key=key, value=value))


# ===========================================================================
# Notifications
# ===========================================================================
@admin_bp.route("/notifications")
@permission_required("notifications.manage")
def notifications():
    page = request.args.get("page", 1, type=int)
    pagination = Notification.query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template("admin/notifications.html", pagination=pagination)


@admin_bp.route("/notifications/mark-all-read", methods=["POST"])
@permission_required("notifications.manage")
def notifications_mark_all_read():
    Notification.query.update({Notification.is_read: True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("admin.notifications"))


@admin_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@permission_required("notifications.manage")
def notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    return redirect(notification.link or url_for("admin.notifications"))


@admin_bp.route("/notifications/<int:notification_id>/delete", methods=["POST"])
@permission_required("notifications.manage")
def notification_delete(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    db.session.delete(notification)
    db.session.commit()
    flash("Notification deleted.", "success")
    return redirect(url_for("admin.notifications"))


# ===========================================================================
# Activity logs
# ===========================================================================
@admin_bp.route("/activity-logs")
@permission_required("logs.view")
def activity_logs():
    page = request.args.get("page", 1, type=int)
    pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template("admin/activity_logs.html", pagination=pagination)


# ===========================================================================
# API helpers (availability check)
# ===========================================================================
@admin_bp.route("/api/available-rooms")
@permission_required("reservations.create")
def api_available_rooms():
    check_in = parse_date(request.args.get("check_in", ""))
    check_out = parse_date(request.args.get("check_out", ""))
    room_type_id = request.args.get("room_type_id", type=int)
    if not check_in or not check_out or check_out <= check_in:
        return jsonify({"error": "Invalid dates"}), 400
    rooms = available_rooms(check_in, check_out, room_type_id=room_type_id)
    return jsonify(
        {
            "rooms": [
                {
                    "id": r.id,
                    "room_number": r.room_number,
                    "price": float(r.price),
                    "capacity": r.capacity,
                    "status": r.status,
                    "room_type": r.room_type.name if r.room_type else "",
                }
                for r in rooms
            ]
        }
    )


# ===========================================================================
# Admin account management (self-service)
# ===========================================================================
@admin_bp.route("/account", methods=["GET", "POST"])
@staff_required
def account():
    form = AccountForm(obj=current_user)
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("admin.account"))
        current_user.username = form.username.data
        current_user.email = form.email.data.lower()
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Your account has been updated.", "success")
        return redirect(url_for("admin.account"))
    return render_template("admin/account.html", form=form)


# ===========================================================================
# Room images (admin only, multiple per room)
# ===========================================================================
@admin_bp.route("/rooms/<int:room_id>/images", methods=["GET", "POST"])
@permission_required("rooms.manage")
def room_images(room_id):
    room = Room.query.get_or_404(room_id)
    form = RoomImageForm()
    if form.validate_on_submit():
        path = save_upload(form.image.data, "rooms")
        if path:
            if form.is_primary.data:
                for img in room.images.all():
                    img.is_primary = False
            image = RoomImage(
                room_id=room.id,
                image=path,
                caption=form.caption.data or "",
                is_primary=form.is_primary.data,
                display_order=room.images.count(),
            )
            db.session.add(image)
            db.session.flush()
            _commit_log(
                "Room image added",
                "room",
                room.id,
                f"Image uploaded for room {room.room_number}",
                "Room image added",
                f"A new image was uploaded for room {room.room_number}.",
                "info",
                url_for("admin.room_images", room_id=room.id),
            )
            flash("Image uploaded.", "success")
        else:
            flash("Could not save the uploaded image.", "danger")
        return redirect(url_for("admin.room_images", room_id=room.id))
    images = room.images.order_by(RoomImage.display_order, RoomImage.id).all()
    return render_template("admin/room_images.html", room=room, form=form, images=images)


@admin_bp.route("/rooms/<int:room_id>/images/<int:image_id>/delete", methods=["POST"])
@permission_required("rooms.manage")
def room_image_delete(room_id, image_id):
    room = Room.query.get_or_404(room_id)
    image = RoomImage.query.filter_by(id=image_id, room_id=room.id).first_or_404()
    delete_upload(image.image)
    db.session.delete(image)
    db.session.commit()
    flash("Image deleted.", "success")
    return redirect(url_for("admin.room_images", room_id=room.id))


@admin_bp.route("/rooms/<int:room_id>/images/<int:image_id>/primary", methods=["POST"])
@permission_required("rooms.manage")
def room_image_primary(room_id, image_id):
    room = Room.query.get_or_404(room_id)
    image = RoomImage.query.filter_by(id=image_id, room_id=room.id).first_or_404()
    for img in room.images.all():
        img.is_primary = (img.id == image.id)
    db.session.commit()
    flash("Primary image updated.", "success")
    return redirect(url_for("admin.room_images", room_id=room.id))


# ===========================================================================
# Special offers (dated, admin managed)
# ===========================================================================
@admin_bp.route("/content/special-offers")
@permission_required("content.manage")
def special_offers():
    offers = SpecialOffer.query.order_by(SpecialOffer.display_order, SpecialOffer.id).all()
    return render_template("admin/special_offers.html", offers=offers)


@admin_bp.route("/content/special-offers/new", methods=["GET", "POST"])
@permission_required("content.manage")
def special_offer_new():
    form = SpecialOfferForm()
    if form.validate_on_submit():
        image = None
        if form.image.data and form.image.data.filename:
            image = save_upload(form.image.data, "offers")
        offer = SpecialOffer(
            title=form.title.data,
            description=form.description.data or "",
            discount_details=form.discount_details.data or "",
            image=image,
            badge_text=form.badge_text.data or "",
            cta_text=form.cta_text.data or "",
            cta_url=form.cta_url.data or "",
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            display_order=form.display_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(offer)
        db.session.flush()
        _commit_log(
            "Special offer added",
            "offer",
            offer.id,
            f"Offer '{offer.title}' created",
            "Special offer added",
            f"Special offer '{offer.title}' was created.",
            "success",
            url_for("admin.special_offers"),
        )
        flash("Special offer added.", "success")
        return redirect(url_for("admin.special_offers"))
    return render_template("admin/special_offer_form.html", form=form, title="Add Special Offer")


@admin_bp.route("/content/special-offers/<int:offer_id>/edit", methods=["GET", "POST"])
@permission_required("content.manage")
def special_offer_edit(offer_id):
    offer = SpecialOffer.query.get_or_404(offer_id)
    form = SpecialOfferForm(obj=offer)
    if form.validate_on_submit():
        if form.image.data and hasattr(form.image.data, "filename") and form.image.data.filename:
            delete_upload(offer.image)
            offer.image = save_upload(form.image.data, "offers")
        offer.title = form.title.data
        offer.description = form.description.data or ""
        offer.discount_details = form.discount_details.data or ""
        offer.badge_text = form.badge_text.data or ""
        offer.cta_text = form.cta_text.data or ""
        offer.cta_url = form.cta_url.data or ""
        offer.start_date = form.start_date.data
        offer.end_date = form.end_date.data
        offer.display_order = form.display_order.data or 0
        offer.is_active = form.is_active.data
        _commit_log(
            "Special offer edited",
            "offer",
            offer.id,
            f"Offer '{offer.title}' updated",
            "Special offer edited",
            f"Special offer '{offer.title}' was updated.",
            "info",
            url_for("admin.special_offers"),
        )
        flash("Special offer updated.", "success")
        return redirect(url_for("admin.special_offers"))
    return render_template("admin/special_offer_form.html", form=form, title="Edit Special Offer", offer=offer)


@admin_bp.route("/content/special-offers/<int:offer_id>/toggle", methods=["POST"])
@permission_required("content.manage")
def special_offer_toggle(offer_id):
    offer = SpecialOffer.query.get_or_404(offer_id)
    offer.is_active = not offer.is_active
    db.session.commit()
    flash("Offer visibility updated.", "success")
    return redirect(url_for("admin.special_offers"))


@admin_bp.route("/content/special-offers/<int:offer_id>/delete", methods=["POST"])
@permission_required("content.manage")
def special_offer_delete(offer_id):
    offer = SpecialOffer.query.get_or_404(offer_id)
    delete_upload(offer.image)
    db.session.delete(offer)
    db.session.commit()
    flash("Special offer deleted.", "success")
    return redirect(url_for("admin.special_offers"))


# ===========================================================================
# Branding: logo / favicon delete
# ===========================================================================
@admin_bp.route("/content/branding/delete-logo", methods=["POST"])
@permission_required("content.manage")
def branding_delete_logo():
    old = settings_value("logo")
    delete_upload(old)
    _set_setting("logo", "")
    db.session.commit()
    flash("Logo removed.", "success")
    return redirect(url_for("admin.branding"))


@admin_bp.route("/content/branding/delete-favicon", methods=["POST"])
@permission_required("content.manage")
def branding_delete_favicon():
    old = settings_value("favicon")
    delete_upload(old)
    _set_setting("favicon", "")
    db.session.commit()
    flash("Favicon removed.", "success")
    return redirect(url_for("admin.branding"))


@admin_bp.route("/content/branding/delete-banner/<key>", methods=["POST"])
@permission_required("content.manage")
def branding_delete_banner(key):
    allowed = {"banner_rooms", "banner_about", "banner_contact", "banner_services"}
    if key not in allowed:
        flash("Unknown banner.", "error")
        return redirect(url_for("admin.branding"))
    old = settings_value(key)
    delete_upload(old)
    _set_setting(key, "")
    db.session.commit()
    flash("Banner removed.", "success")
    return redirect(url_for("admin.branding"))


# ===========================================================================
# Theme management (colors + light/dark)
# ===========================================================================
THEME_KEYS = [
    "theme_primary_color",
    "theme_secondary_color",
    "theme_background_color",
    "theme_text_color",
    "theme_button_style",
    "theme_mode",
]


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


@admin_bp.route("/content/theme", methods=["GET", "POST"])
@permission_required("content.manage")
def theme():
    current = _theme_dict()
    form = ThemeForm(
        primary_color=current["theme_primary_color"],
        secondary_color=current["theme_secondary_color"],
        background_color=current["theme_background_color"],
        text_color=current["theme_text_color"],
        button_style=current["theme_button_style"],
        mode=current["theme_mode"],
    )
    if form.validate_on_submit():
        mapping = {
            "theme_primary_color": form.primary_color.data,
            "theme_secondary_color": form.secondary_color.data,
            "theme_background_color": form.background_color.data,
            "theme_text_color": form.text_color.data,
            "theme_button_style": form.button_style.data,
            "theme_mode": form.mode.data,
        }
        for key, value in mapping.items():
            existing = ThemeSetting.query.filter_by(key=key).first()
            if existing:
                existing.value = value
            else:
                db.session.add(ThemeSetting(key=key, value=value))
        db.session.commit()
        flash("Theme applied.", "success")
        return redirect(url_for("admin.theme"))
    return render_template("admin/theme.html", form=form, current=current)

