"""Seed data for the Hotel Reservation & Check-In Desk System.

NOTE: Demo/seed data has been DISABLED for this project. The database should
only contain real data entered through the application. The `seed_data()`
function below is now a no-op so that fake/demo data can never be reintroduced,
and the `flask seed` CLI command has also been disabled in `app/__init__.py`.

The helper functions below are retained only so existing imports do not break;
they are no longer invoked by `seed_data()`.
"""
from datetime import date, datetime, timedelta

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
    WebsiteSetting,
    HeroBanner,
    PromotionalBanner,
    Service,
    ContactMessage,
    Notification,
    ActivityLog,
)
from app.services.billing import compute_stay, derive_payment_status
from app.utils.constants import DEFAULT_SETTINGS, ALL_PERMISSIONS
from app.utils.helpers import simple_code


def _seed_settings():
    """Populate the website settings key/value store from DEFAULT_SETTINGS."""
    for key, meta in DEFAULT_SETTINGS.items():
        if WebsiteSetting.query.filter_by(key=key).first():
            continue
        db.session.add(
            WebsiteSetting(
                key=key,
                value=meta["value"],
                label=meta["label"],
                group=meta["group"],
            )
        )


def _seed_users():
    """Create the administrator, a front-desk staff member and a demo guest."""
    admin = User(
        username="admin",
        email="admin@grandmeridian.com",
        full_name="Alexandra Sterling",
        role="admin",
    )
    admin.set_password("admin123")
    db.session.add(admin)

    staff_user = User(
        username="reception",
        email="reception@grandmeridian.com",
        full_name="Daniel Reyes",
        role="staff",
    )
    staff_user.set_password("staff123")
    db.session.add(staff_user)

    guest_user = User(
        username="guest",
        email="guest@example.com",
        full_name="Sophia Bennett",
        role="guest",
    )
    guest_user.set_password("guest123")
    db.session.add(guest_user)

    db.session.flush()

    db.session.add(
        Staff(
            user_id=staff_user.id,
            job_title="Front Desk Supervisor",
            phone="+1 (555) 987-6543",
            hire_date=date.today() - timedelta(days=400),
            is_active=True,
            permissions=",".join(ALL_PERMISSIONS),
        )
    )

    return admin, staff_user, guest_user


def _seed_room_types():
    """Create the room catalogue."""
    room_types = [
        {
            "name": "Standard Room",
            "slug": "standard-room",
            "description": "A comfortable, well-appointed room ideal for business "
            "and leisure travellers. Features a plush queen bed, work desk and "
            "modern ensuite bathroom.",
            "base_price": 120,
            "capacity": 2,
            "bed_type": "Queen Bed",
            "facilities": "Free Wi-Fi,Air Conditioning,Flat-screen TV,Work Desk,"
            "Ensuite Bathroom,Tea & Coffee Maker",
        },
        {
            "name": "Deluxe Room",
            "slug": "deluxe-room",
            "description": "Spacious deluxe accommodation with a king bed, seating "
            "area and upgraded amenities for a truly relaxing stay.",
            "base_price": 180,
            "capacity": 3,
            "bed_type": "King Bed",
            "facilities": "Free Wi-Fi,Air Conditioning,Flat-screen TV,Minibar,"
            "Seating Area,Bathtub,Room Service",
        },
        {
            "name": "Executive Suite",
            "slug": "executive-suite",
            "description": "A refined suite with a separate living room, dining "
            "area and premium touches — perfect for extended stays and executives.",
            "base_price": 280,
            "capacity": 4,
            "bed_type": "King Bed + Sofa Bed",
            "facilities": "Free Wi-Fi,Air Conditioning,Flat-screen TV,Minibar,"
            "Living Room,Dining Area,Bathtub,Room Service,City View",
        },
        {
            "name": "Presidential Suite",
            "slug": "presidential-suite",
            "description": "Our signature suite offering panoramic skyline views, "
            "a private lounge, butler service and the finest in luxury hospitality.",
            "base_price": 450,
            "capacity": 5,
            "bed_type": "King Bed + 2 Sofa Beds",
            "facilities": "Free Wi-Fi,Air Conditioning,Flat-screen TV,Minibar,"
            "Private Lounge,Jacuzzi,Butler Service,Panoramic View,Room Service",
        },
    ]

    created = []
    for data in room_types:
        if RoomType.query.filter_by(slug=data["slug"]).first():
            created.append(RoomType.query.filter_by(slug=data["slug"]).first())
            continue
        rt = RoomType(**data, is_active=True)
        db.session.add(rt)
        created.append(rt)
    db.session.flush()
    return created


def _seed_rooms(room_types):
    """Create individual rooms across floors for each room type."""
    plan = [
        # (room_type_index, floor, start_number, count)
        # NOTE: all ranges below must use globally unique room numbers —
        # Room.room_number is unique and the skip-check below autoflushes,
        # so overlapping ranges silently collapse into aliased duplicates.
        (0, 1, 101, 6),
        (0, 2, 201, 6),
        (1, 2, 207, 4),
        (1, 3, 301, 4),
        (2, 3, 305, 3),
        (2, 4, 401, 3),
        (3, 5, 501, 2),
    ]

    rooms = []
    for rt_index, floor, start, count in plan:
        rt = room_types[rt_index]
        for i in range(count):
            number = str(start + i)
            if Room.query.filter_by(room_number=number).first():
                rooms.append(Room.query.filter_by(room_number=number).first())
                continue
            room = Room(
                room_number=number,
                room_type_id=rt.id,
                floor=floor,
                price=rt.base_price,
                capacity=rt.capacity,
                bed_type=rt.bed_type,
                description=rt.description,
                facilities=rt.facilities,
                status="available",
                is_active=True,
            )
            db.session.add(room)
            rooms.append(room)
    db.session.flush()
    return rooms


def _seed_guests(guest_user):
    """Create a handful of guest profiles."""
    guest_data = [
        {
            "full_name": "Sophia Bennett",
            "email": "guest@example.com",
            "phone": "+1 (555) 111-2233",
            "address": "48 Maple Street",
            "city": "New York",
            "country": "USA",
            "id_type": "Passport",
            "id_number": "P-884512",
            "notes": "Prefers a high floor, quiet room.",
            "user_id": guest_user.id,
        },
        {
            "full_name": "James O'Connor",
            "email": "james.oconnor@example.com",
            "phone": "+44 7700 900123",
            "address": "12 Baker Lane",
            "city": "London",
            "country": "UK",
            "id_type": "Passport",
            "id_number": "P-552190",
            "notes": "",
        },
        {
            "full_name": "Aisha Khan",
            "email": "aisha.khan@example.com",
            "phone": "+92 300 1234567",
            "address": "7 Gulberg Road",
            "city": "Lahore",
            "country": "Pakistan",
            "id_type": "ID Card",
            "id_number": "ID-334455",
            "notes": "Celebrating anniversary — arrange a welcome amenity.",
        },
        {
            "full_name": "Liam Müller",
            "email": "liam.muller@example.com",
            "phone": "+49 151 23456789",
            "address": "9 Hauptstrasse",
            "city": "Berlin",
            "country": "Germany",
            "id_type": "Passport",
            "id_number": "P-771204",
            "notes": "Business traveller, requires early check-in.",
        },
        {
            "full_name": "Emily Chen",
            "email": "emily.chen@example.com",
            "phone": "+86 138 0013 8000",
            "address": "22 Nanjing Road",
            "city": "Shanghai",
            "country": "China",
            "id_type": "Passport",
            "id_number": "P-990871",
            "notes": "",
        },
    ]

    guests = []
    for data in guest_data:
        if Guest.query.filter_by(email=data["email"]).first():
            guests.append(Guest.query.filter_by(email=data["email"]).first())
            continue
        guest = Guest(guest_code=simple_code("GST"), **data)
        db.session.add(guest)
        guests.append(guest)
    db.session.flush()
    return guests


def _make_reservation(guest, room, check_in, check_out, adults, children,
                      status, source, tax_rate, additional=0, discount=0,
                      paid=None, special_request=None, created_by=None):
    """Build a reservation with consistent financials and return it."""
    nights = (check_out - check_in).days
    rate = room.price if room else 0
    billing = compute_stay(rate, nights, additional, discount, tax_rate)
    total = float(billing["total"])
    paid_amount = float(paid) if paid is not None else 0.0
    payment_status = derive_payment_status(total, paid_amount)

    reservation = Reservation(
        reservation_code=simple_code("RES"),
        guest_id=guest.id,
        room_id=room.id if room else None,
        room_type_id=room.room_type_id if room else None,
        check_in_date=check_in,
        check_out_date=check_out,
        adults=adults,
        children=children,
        special_request=special_request,
        source=source,
        room_rate=rate,
        nights=nights,
        room_charge=billing["room_charge"],
        additional_charges=billing["additional_charges"],
        discount=billing["discount"],
        tax_rate=billing["tax_rate"],
        tax_amount=billing["tax_amount"],
        total_amount=billing["total"],
        paid_amount=paid_amount,
        status=status,
        payment_status=payment_status,
        created_by=created_by,
    )
    db.session.add(reservation)
    return reservation


def _seed_reservations(guests, rooms, admin):
    """Create reservations in every lifecycle state."""
    today = date.today()
    tax_rate = 10
    reservations = []

    # --- Checked-out (completed stay, fully paid) ---
    total = float(compute_stay(rooms[0].price, 3, 45, 0, tax_rate)["total"])
    r = _make_reservation(
        guests[0], rooms[0], today - timedelta(days=10), today - timedelta(days=7),
        2, 0, "checked_out", "website", tax_rate,
        additional=45, paid=total, special_request="Late checkout requested.",
        created_by=admin.id,
    )
    reservations.append(r)

    # --- Checked-in (currently staying) ---
    r = _make_reservation(
        guests[1], rooms[6], today - timedelta(days=1), today + timedelta(days=2),
        2, 1, "checked_in", "desk", tax_rate,
        paid=float(compute_stay(rooms[6].price, 3, 0, 0, tax_rate)["total"]),
        special_request="Extra towels and a crib.",
        created_by=admin.id,
    )
    reservations.append(r)

    # --- Confirmed (upcoming) ---
    r = _make_reservation(
        guests[2], rooms[12], today + timedelta(days=3), today + timedelta(days=6),
        2, 0, "confirmed", "website", tax_rate,
        paid=0, special_request="Anniversary celebration — flowers in room.",
        created_by=admin.id,
    )
    reservations.append(r)

    # --- Pending (awaiting confirmation) ---
    r = _make_reservation(
        guests[3], rooms[18], today + timedelta(days=5), today + timedelta(days=8),
        1, 0, "pending", "phone", tax_rate,
        paid=0, special_request="",
        created_by=admin.id,
    )
    reservations.append(r)

    # --- Cancelled ---
    r = _make_reservation(
        guests[4], rooms[2], today - timedelta(days=2), today + timedelta(days=1),
        2, 0, "cancelled", "website", tax_rate,
        paid=0, special_request="",
        created_by=admin.id,
    )
    reservations.append(r)

    # --- Sync room statuses to match the seeded reservation lifecycle ---
    # NOTE: reservations are still transient here (not yet flushed), so the
    # `res.room` relationship does not resolve. Look the room up explicitly by
    # its primary key instead of relying on the relationship.
    for res in reservations:
        if not res.room_id:
            continue
        room = db.session.get(Room, res.room_id)
        if room is None:
            continue
        if res.status == "checked_in":
            room.status = "occupied"
        elif res.status in ("confirmed", "pending"):
            room.status = "reserved"
        # cancelled / checked_out rooms stay as-is (housekeeping will handle them)

    db.session.flush()
    return reservations


def _seed_check_ins(reservations, admin):
    """Create check-in records for checked-in/checked-out reservations."""
    for res in reservations:
        if res.status in ("checked_in", "checked_out"):
            if not res.check_ins.first():
                db.session.add(
                    CheckIn(
                        reservation_id=res.id,
                        checked_in_at=datetime.combine(
                            res.check_in_date, datetime.min.time()
                        ),
                        checked_in_by=admin.id,
                        notes="Standard check-in procedure completed.",
                    )
                )
    db.session.flush()


def _seed_check_outs(reservations, admin):
    """Create check-out records for checked-out reservations."""
    for res in reservations:
        if res.status == "checked_out":
            if not res.check_outs.first():
                db.session.add(
                    CheckOut(
                        reservation_id=res.id,
                        checked_out_at=datetime.combine(
                            res.check_out_date, datetime.min.time()
                        ),
                        checked_out_by=admin.id,
                        notes="Guest departed. Room released for housekeeping.",
                        final_total=res.total_amount,
                        final_paid=res.paid_amount,
                    )
                )
    db.session.flush()


def _seed_payments(reservations, admin):
    """Create payment records for reservations with paid amounts."""
    for res in reservations:
        if float(res.paid_amount) > 0 and not res.payments.first():
            db.session.add(
                Payment(
                    payment_code=simple_code("PAY"),
                    reservation_id=res.id,
                    guest_id=res.guest_id,
                    amount=res.paid_amount,
                    method="card",
                    reference="CARD-XXXX-4242",
                    note="Payment recorded during seeding.",
                    received_by=admin.id,
                    received_at=datetime.utcnow() - timedelta(days=1),
                )
            )
    db.session.flush()


def _seed_invoices(reservations, admin):
    """Create invoices for checked-out and checked-in reservations."""
    for res in reservations:
        if res.status in ("checked_out", "checked_in") and not res.invoices.first():
            db.session.add(
                Invoice(
                    invoice_number=simple_code("INV"),
                    reservation_id=res.id,
                    room_charge=res.room_charge,
                    additional_charges=res.additional_charges,
                    discount=res.discount,
                    tax_rate=res.tax_rate,
                    tax_amount=res.tax_amount,
                    total=res.total_amount,
                    paid=res.paid_amount,
                    status="paid" if float(res.paid_amount) >= float(res.total_amount) else "unpaid",
                    issued_by=admin.id,
                    issued_at=datetime.utcnow() - timedelta(days=1),
                )
            )
    db.session.flush()


def _seed_housekeeping(rooms):
    """Create housekeeping tasks for recently vacated rooms."""
    if HousekeepingTask.query.first():
        return
    tasks = [
        (rooms[0], "pending", "Maria Gomez", "Full clean after guest departure."),
        (rooms[1], "in_progress", "John Smith", "Deep clean — carpet shampoo."),
        (rooms[2], "completed", "Maria Gomez", "Standard refresh."),
    ]
    for room, status, assigned, notes in tasks:
        db.session.add(
            HousekeepingTask(
                room_id=room.id,
                task_code=simple_code("HK"),
                status=status,
                assigned_to=assigned,
                notes=notes,
                requested_at=datetime.utcnow() - timedelta(hours=4),
                started_at=datetime.utcnow() - timedelta(hours=2) if status == "in_progress" else None,
                completed_at=datetime.utcnow() - timedelta(hours=1) if status == "completed" else None,
                completed_by="Maria Gomez" if status == "completed" else None,
            )
        )
    db.session.flush()


def _seed_maintenance(rooms):
    """Create maintenance tasks for rooms needing attention."""
    if MaintenanceTask.query.first():
        return
    tasks = [
        (rooms[3], "open", "Air conditioning not cooling.", "Technician scheduled."),
        (rooms[4], "in_progress", "Bathroom faucet leaking.", "Parts ordered."),
        (rooms[5], "completed", "TV not turning on.", "Replaced power board."),
    ]
    for room, status, reason, notes in tasks:
        db.session.add(
            MaintenanceTask(
                room_id=room.id,
                task_code=simple_code("MNT"),
                reason=reason,
                notes=notes,
                status=status,
                requested_by="Daniel Reyes",
                created_at=datetime.utcnow() - timedelta(days=2),
                resolved_at=datetime.utcnow() - timedelta(hours=6) if status == "completed" else None,
            )
        )
    db.session.flush()


def _seed_banners():
    """Create hero and promotional banners for the website."""
    if HeroBanner.query.first():
        return
    hero_banners = [
        {
            "title": "Experience Timeless Luxury",
            "subtitle": "Grand Meridian Hotel",
            "description": "Elegant rooms, world-class dining and impeccable "
            "service in the heart of the city.",
            "cta_text": "Reserve Your Stay",
            "cta_url": "/reservation",
            "cta2_text": "Explore Rooms",
            "cta2_url": "/rooms",
            "animation": "fade",
            "display_order": 1,
        },
        {
            "title": "Unwind in Pure Comfort",
            "subtitle": "Premium Accommodation",
            "description": "From cosy standard rooms to breathtaking presidential "
            "suites — find your perfect escape.",
            "cta_text": "Book Now",
            "cta_url": "/reservation",
            "cta2_text": "View Suites",
            "cta2_url": "/rooms",
            "animation": "slide",
            "display_order": 2,
        },
        {
            "title": "Your Gateway to the City",
            "subtitle": "Prime Downtown Location",
            "description": "Steps from the finest dining, shopping and cultural "
            "landmarks. Your adventure begins here.",
            "cta_text": "Plan Your Stay",
            "cta_url": "/reservation",
            "cta2_text": "Contact Us",
            "cta2_url": "/contact",
            "animation": "zoom",
            "display_order": 3,
        },
    ]
    for data in hero_banners:
        db.session.add(HeroBanner(**data, is_active=True))

    promo_banners = [
        {
            "title": "Summer Escape Package",
            "description": "Save 20% on stays of 3 nights or more. Includes daily "
            "breakfast and late checkout.",
            "badge_text": "Limited Time",
            "cta_text": "Claim Offer",
            "cta_url": "/reservation",
            "display_order": 1,
        },
        {
            "title": "Business Traveller Special",
            "description": "Complimentary airport transfer, high-speed Wi-Fi and "
            "access to the executive lounge.",
            "badge_text": "Corporate",
            "cta_text": "Learn More",
            "cta_url": "/reservation",
            "display_order": 2,
        },
    ]
    for data in promo_banners:
        db.session.add(PromotionalBanner(**data, is_active=True))
    db.session.flush()


def _seed_services():
    """Create the services shown on the website."""
    if Service.query.first():
        return
    services = [
        ("Spa & Wellness", "Rejuvenate with signature massages, sauna and a "
         "fully equipped fitness centre.", "💆", 1),
        ("Fine Dining", "Three restaurants and a rooftop bar serving local and "
         "international cuisine.", "🍽️", 2),
        ("24/7 Room Service", "Around-the-clock dining delivered to your room, "
         "whenever you need it.", "🛎️", 3),
        ("Airport Transfers", "Chauffeured pick-up and drop-off in luxury "
         "vehicles, available on request.", "🚗", 4),
        ("Conference Rooms", "Modern meeting and event spaces with full AV "
         "support for up to 200 guests.", "💼", 5),
        ("Concierge", "Our dedicated team arranges tours, tickets and anything "
         "else you need for a perfect stay.", "🗺️", 6),
    ]
    for name, description, icon, order in services:
        db.session.add(
            Service(name=name, description=description, icon=icon,
                    display_order=order, is_active=True)
        )
    db.session.flush()


def _seed_contact_messages():
    """Add a couple of sample contact messages."""
    if ContactMessage.query.first():
        return
    db.session.add(
        ContactMessage(
            name="Robert Wilson",
            email="robert.wilson@example.com",
            phone="+1 (555) 222-3344",
            subject="Group booking enquiry",
            message="Hello, we are planning a corporate retreat for 25 people "
            "in October. Could you share group rates and availability?",
            is_read=False,
        )
    )
    db.session.add(
        ContactMessage(
            name="Fatima Noor",
            email="fatima.noor@example.com",
            phone="+92 321 5556677",
            subject="Wedding venue question",
            message="We are interested in hosting a wedding reception. Do you "
            "offer event packages and catering?",
            is_read=True,
        )
    )
    db.session.flush()


def _seed_notifications(admin):
    """Create sample notifications and activity logs."""
    if Notification.query.first():
        return
    notifications = [
        ("New reservation received", "Reservation RES-… is pending confirmation.",
         "booking", "/admin/reservations"),
        ("Payment recorded", "A card payment was recorded for a checked-in guest.",
         "payment", "/admin/payments"),
        ("Housekeeping task pending", "Room 101 is awaiting a full clean.",
         "housekeeping", "/admin/housekeeping"),
        ("Maintenance request open", "Room 104 has an open maintenance request.",
         "maintenance", "/admin/maintenance"),
    ]
    for title, message, category, link in notifications:
        db.session.add(
            Notification(title=title, message=message, category=category,
                         link=link, is_read=False)
        )

    if ActivityLog.query.first():
        return
    logs = [
        ("System seeded with demo data", "system", None, "Initial demo dataset created."),
        ("Reservation created", "reservation", 1, "New reservation RES-… created from the website."),
        ("Check-in completed", "check_in", 1, "Guest checked in to room 101."),
        ("Payment recorded", "payment", 1, "Card payment of $540.00 recorded."),
        ("Room status updated", "room", 1, "Room 101 set to cleaning."),
    ]
    for action, entity_type, entity_id, details in logs:
        db.session.add(
            ActivityLog(
                user_id=admin.id if entity_type != "system" else None,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                ip_address="127.0.0.1",
            )
        )
    db.session.flush()


def seed_data():
    """DISABLED: demo/seed data has been removed from this project.

    This function no longer inserts fake/demo data into the database. It is
    kept only so existing imports do not break. The database should only
    contain real data entered through the application.
    """
    print(
        "seed_data() is disabled. Demo/fake data is no longer added to the "
        "database."
    )
    return
