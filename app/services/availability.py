"""Room availability and reservation conflict logic."""
from datetime import date

from app import db
from app.models import Room, Reservation
from app.utils.constants import BLOCKING_RESERVATION_STATUSES, UNASSIGNABLE_ROOM_STATUSES


def room_is_blocked_by_reservations(room_id, check_in, check_out, exclude_reservation_id=None):
    """Return True when an active reservation overlaps the requested period."""
    query = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status.in_(BLOCKING_RESERVATION_STATUSES),
        Reservation.check_in_date < check_out,
        Reservation.check_out_date > check_in,
    )
    if exclude_reservation_id:
        query = query.filter(Reservation.id != exclude_reservation_id)
    return query.first() is not None


def room_available_for_dates(room, check_in, check_out, exclude_reservation_id=None):
    """A room is bookable when its status allows assignment and no reservation overlaps."""
    if room.status in UNASSIGNABLE_ROOM_STATUSES:
        return False
    if not room.is_active:
        return False
    if room_has_blocking_reservation(room.id, check_in, check_out, exclude_reservation_id):
        return False
    return True


def room_has_blocking_reservation(room_id, check_in, check_out, exclude_reservation_id=None):
    return room_is_blocked_by_reservations(room_id, check_in, check_out, exclude_reservation_id)


def available_rooms(check_in, check_out, room_type_id=None, capacity=None, exclude_room_id=None):
    """Return rooms assignable for the given dates.

    Guards against double booking, occupied, cleaning, maintenance and
    out-of-service rooms.
    """
    query = Room.query.filter(Room.is_active.is_(True))
    if room_type_id:
        query = query.filter(Room.room_type_id == room_type_id)
    if capacity:
        query = query.filter(Room.capacity >= capacity)
    if exclude_room_id:
        query = query.filter(Room.id != exclude_room_id)

    rooms = query.all()
    result = []
    for room in rooms:
        if room.status in UNASSIGNABLE_ROOM_STATUSES:
            continue
        if room_has_blocking_reservation(room.id, check_in, check_out):
            continue
        result.append(room)
    return result


def available_room_count(check_in, check_out, room_type_id=None):
    return len(available_rooms(check_in, check_out, room_type_id=room_type_id))


def validate_dates(check_in, check_out):
    """Validate a check-in/check-out pair.

    Returns (error_message, None) or (None, (check_in, check_out)).
    """
    if not check_in or not check_out:
        return "Please provide both check-in and check-out dates.", None
    if check_out <= check_in:
        return "Check-out date must be later than check-in date.", None
    if check_in < date.today():
        return "Check-in date cannot be in the past.", None
    return None, (check_in, check_out)


def find_conflict(room_id, check_in, check_out, exclude_reservation_id=None):
    """Return the conflicting reservation (or None) for display purposes."""
    return room_is_blocked_by_reservations(
        room_id, check_in, check_out, exclude_reservation_id
    ) and (
        Reservation.query.filter(
            Reservation.room_id == room_id,
            Reservation.status.in_(BLOCKING_RESERVATION_STATUSES),
            Reservation.check_in_date < check_out,
            Reservation.check_out_date > check_in,
        )
        .filter(Reservation.id != exclude_reservation_id if exclude_reservation_id else True)
        .first()
    )
