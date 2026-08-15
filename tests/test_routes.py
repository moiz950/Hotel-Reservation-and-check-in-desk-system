"""Route-level integration tests: public pages, auth and admin access control."""
from datetime import date, timedelta

from flask import url_for


def test_homepage_loads(client):
    response = client.get("/")
    assert response.status_code in (200, 302)  # 200 direct, or 302 via main redirect


def test_public_pages_render(client):
    for path in ("/rooms", "/about", "/services", "/contact", "/reservation"):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data or b"login" in response.data.lower()


def test_register_creates_account(client, app):
    with app.app_context():
        from app.models import User, Guest

        response = client.post(
            "/register",
            data={
                "full_name": "New Customer",
                "username": "newcustomer",
                "email": "new@example.com",
                "password": "Secret123!",
                "confirm": "Secret123!",
            },
        )
        # Successful registration redirects to the homepage
        assert response.status_code in (301, 302)
        assert User.query.filter_by(username="newcustomer").first() is not None
        assert Guest.query.filter_by(email="new@example.com").first() is not None


def test_login_invalid_credentials(client):
    response = client.post(
        "/login",
        data={"username": "nobody", "password": "wrongpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_admin_redirects_anonymous_to_login(client):
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code in (301, 302)
    assert "/login" in response.headers.get("Location", "")


def test_guest_cannot_access_admin(client, app, guest_user):
    with app.app_context():
        client.post(
            "/login",
            data={"username": guest_user.username, "password": "guestpass"},
        )
    response = client.get("/admin/")
    assert response.status_code == 403


def test_admin_can_access_dashboard(client, app, admin_user):
    with app.app_context():
        client.post(
            "/login",
            data={"username": admin_user.username, "password": "adminpass"},
        )
    response = client.get("/admin/")
    assert response.status_code == 200


def test_error_page_returns_404(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404
    assert b"404" in response.data
