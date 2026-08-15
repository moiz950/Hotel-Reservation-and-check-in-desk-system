"""Shared pytest fixtures for the hotel system test suite."""
import pytest

from app import create_app, db
from app.models import Guest, Reservation, Room, RoomType, Staff, User
from app.utils.constants import ALL_PERMISSIONS


@pytest.fixture()
def app():
    """Create an app instance backed by an in-memory SQLite database."""
    application = create_app("testing")

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """A test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture()
def admin_user(app):
    """Create and return an administrator account."""
    user = User(
        username="admin",
        email="admin@test.local",
        full_name="Test Admin",
        role="admin",
    )
    user.set_password("adminpass")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def staff_user(app):
    """Create and return a front-desk staff account with all permissions."""
    user = User(
        username="reception",
        email="reception@test.local",
        full_name="Test Staff",
        role="staff",
    )
    user.set_password("staffpass")
    db.session.add(user)
    db.session.flush()

    db.session.add(
        Staff(
            user_id=user.id,
            job_title="Receptionist",
            is_active=True,
            permissions=",".join(ALL_PERMISSIONS),
        )
    )
    db.session.commit()
    return user


@pytest.fixture()
def guest_user(app):
    """Create and return a plain website guest account."""
    user = User(
        username="guestuser",
        email="guest@test.local",
        full_name="Test Guest",
        role="guest",
    )
    user.set_password("guestpass")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def room_type(app):
    """Create a single room type."""
    room_type = RoomType(
        name="Standard Room",
        slug="standard-room",
        description="A comfortable room.",
        base_price=120,
        capacity=2,
        bed_type="Queen",
        facilities="Wi-Fi,TV",
        is_active=True,
    )
    db.session.add(room_type)
    db.session.commit()
    return room_type


@pytest.fixture()
def room(app, room_type):
    """Create a single bookable room."""
    room = Room(
        room_number="101",
        room_type_id=room_type.id,
        floor=1,
        price=120,
        capacity=2,
        status="available",
        is_active=True,
    )
    db.session.add(room)
    db.session.commit()
    return room


@pytest.fixture()
def guest(app):
    """Create a guest profile."""
    guest = Guest(
        guest_code="GST-TEST",
        full_name="John Smith",
        email="john@test.local",
        phone="+1 555 000 1111",
    )
    db.session.add(guest)
    db.session.commit()
    return guest


def make_reservation(app, room, guest, check_in, check_out, status="confirmed", **kwargs):
    """Create a reservation in the active test application context."""
    nights = (check_out - check_in).days
    reservation = Reservation(
        reservation_code="RES-T" + str(room.id) + str(guest.id),
        guest_id=guest.id,
        room_id=room.id,
        room_type_id=room.room_type_id,
        check_in_date=check_in,
        check_out_date=check_out,
        adults=kwargs.get("adults", 2),
        children=kwargs.get("children", 0),
        room_rate=room.price,
        nights=nights,
        room_charge=room.price * nights,
        total_amount=room.price * nights,
        paid_amount=kwargs.get("paid_amount", 0),
        status=status,
        payment_status=kwargs.get("payment_status", "pending"),
    )
    db.session.add(reservation)
    db.session.commit()
    return reservation
