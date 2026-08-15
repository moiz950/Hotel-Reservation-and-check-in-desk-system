"""Tests for user roles, permissions and staff profiles."""
from app import db
from app.models import User
from app.utils.constants import ALL_PERMISSIONS


def test_admin_has_all_permissions(admin_user):
    assert admin_user.is_admin
    assert admin_user.is_staff_member
    for perm in ALL_PERMISSIONS:
        assert admin_user.has_permission(perm)


def test_staff_permissions(staff_user):
    assert staff_user.is_staff
    assert staff_user.is_staff_member
    for perm in ALL_PERMISSIONS:
        assert staff_user.has_permission(perm)


def test_guest_has_no_staff_permissions(guest_user):
    assert guest_user.role == "guest"
    assert not guest_user.is_staff_member
    assert not guest_user.has_permission("rooms.view")


def test_staff_with_limited_permissions(app):
    with app.app_context():
        user = User(
            username="limited",
            email="limited@test.local",
            full_name="Limited Staff",
            role="staff",
        )
        user.set_password("pass")
        db.session.add(user)
        db.session.flush()

        from app.models import Staff

        db.session.add(
            Staff(
                user_id=user.id,
                job_title="Housekeeper",
                permissions="housekeeping.manage",
                is_active=True,
            )
        )
        db.session.commit()

        assert user.has_permission("housekeeping.manage")
        assert not user.has_permission("rooms.view")
        assert not user.has_permission("reports.view")


def test_inactive_staff_loses_permissions(app):
    with app.app_context():
        user = User(
            username="inactive",
            email="inactive@test.local",
            full_name="Inactive Staff",
            role="staff",
        )
        user.set_password("pass")
        db.session.add(user)
        db.session.flush()

        from app.models import Staff

        db.session.add(
            Staff(
                user_id=user.id,
                job_title="Receptionist",
                permissions=",".join(ALL_PERMISSIONS),
                is_active=False,
            )
        )
        db.session.commit()

        assert not user.has_permission("rooms.view")
