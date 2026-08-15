"""Tests for the availability service — the core double-booking protection."""
from datetime import date, timedelta

from app.services import availability
from tests.conftest import make_reservation


def test_available_room_returned_when_free(app, room):
    today = date.today()
    results = availability.available_rooms(today + timedelta(days=1), today + timedelta(days=3))
    assert room in results


def test_unavailable_when_overlapping_reservation(app, room, guest):
    today = date.today()
    make_reservation(app, room, guest, today + timedelta(days=1), today + timedelta(days=3))

    results = availability.available_rooms(today + timedelta(days=2), today + timedelta(days=4))
    assert room not in results


def test_available_again_after_reservation_ends(app, room, guest):
    today = date.today()
    make_reservation(app, room, guest, today + timedelta(days=1), today + timedelta(days=3))

    # Non-overlapping period after the stay ends
    results = availability.available_rooms(today + timedelta(days=4), today + timedelta(days=6))
    assert room in results


def test_cancelled_reservation_does_not_block(app, room, guest):
    today = date.today()
    make_reservation(app, room, guest, today + timedelta(days=1), today + timedelta(days=3), status="cancelled")

    results = availability.available_rooms(today + timedelta(days=1), today + timedelta(days=3))
    assert room in results


def test_occupied_room_not_assignable(app, room):
    today = date.today()
    room.status = "occupied"
    results = availability.available_rooms(today + timedelta(days=1), today + timedelta(days=3))
    assert room not in results


def test_cleaning_and_maintenance_not_assignable(app, room):
    today = date.today()
    for status in ("cleaning", "maintenance", "out_of_service"):
        room.status = status
        results = availability.available_rooms(today + timedelta(days=1), today + timedelta(days=3))
        assert room not in results, f"room should not be available when status={status}"


def test_room_type_filter(app, room, room_type):
    today = date.today()
    results = availability.available_rooms(
        today + timedelta(days=1), today + timedelta(days=3), room_type_id=room_type.id
    )
    assert room in results

    results = availability.available_rooms(
        today + timedelta(days=1), today + timedelta(days=3), room_type_id=9999
    )
    assert room not in results


def test_capacity_filter(app, room):
    today = date.today()
    results = availability.available_rooms(
        today + timedelta(days=1), today + timedelta(days=3), capacity=5
    )
    assert room not in results

    results = availability.available_rooms(
        today + timedelta(days=1), today + timedelta(days=3), capacity=2
    )
    assert room in results


def test_date_validation(app):
    today = date.today()
    error, _ = availability.validate_dates(None, None)
    assert error is not None

    error, _ = availability.validate_dates(today + timedelta(days=3), today + timedelta(days=3))
    assert error is not None

    error, _ = availability.validate_dates(today - timedelta(days=1), today + timedelta(days=3))
    assert error is not None

    error, parsed = availability.validate_dates(today + timedelta(days=1), today + timedelta(days=3))
    assert error is None
    assert parsed is not None
