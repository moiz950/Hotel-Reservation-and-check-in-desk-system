"""Application factory for the Hotel Reservation & Check-In Desk System."""
import os
import click
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

from config import config_by_name

# --- Extensions (initialised without app so they can be imported anywhere) ---
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access that page."
login_manager.login_message_category = "error"

def _ensure_instance_and_db(app):
    """Create the instance/ folder and database tables if they are missing.

    The instance/ directory and hotel.db are gitignored, so on a fresh deploy
    (e.g. PythonAnywhere) they may not exist yet. Without this, SQLite cannot
    create the database file and every request returns a 500 error. This makes
    the app self-healing on startup without manual `flask init-db`.
    """
    # The SQLite URI looks like sqlite:///C:/.../instance/hotel.db
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:///"):
        db_path = uri[len("sqlite:///"):]
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    with app.app_context():
        db.create_all()

def _ensure_admin_user(app):
    """Bootstrap an admin account so a fresh deploy is immediately usable.

    Priority:
      1. If ADMIN_USERNAME and ADMIN_PASSWORD are set in the environment (e.g.
         via the deployed .env file), create or promote that administrator.
      2. Otherwise, if the database has NO users at all (a brand-new deploy such
         as PythonAnywhere where instance/hotel.db was never uploaded), create a
         default admin (admin / admin123) so you are never locked out of login.
         Change this password immediately after your first sign-in.

    This guarantees the "Invalid username or password" problem cannot happen on
    a fresh deployment, while still allowing custom credentials via env vars.
    """
    from app.models import User

    username = app.config.get("ADMIN_USERNAME")
    password = app.config.get("ADMIN_PASSWORD")

    with app.app_context():
        # Case 1: explicit admin credentials supplied via environment.
        if username and password:
            user = User.query.filter(
                (User.username == username)
                | (User.email == (app.config.get("ADMIN_EMAIL") or ""))
            ).first()
            if user:
                user.role = "admin"
                user.is_active_account = True
                action = "promoted to admin"
            else:
                user = User(
                    username=username,
                    email=(app.config.get("ADMIN_EMAIL") or f"{username}@example.com").strip().lower(),
                    full_name=app.config.get("ADMIN_FULL_NAME") or "Administrator",
                    role="admin",
                    is_active_account=True,
                )
                user.set_password(password)
                db.session.add(user)
                action = "created"
            db.session.commit()
            print(f"Admin account '{username}' {action} from environment configuration.")
            return

        # Case 2: no admin env vars -> create a default admin only if the
        # database is completely empty (fresh deploy). Never overwrite an
        # existing account.
        if User.query.count() == 0:
            default_username = "admin"
            default_password = "admin123"
            user = User(
                username=default_username,
                email="admin@hotel.local",
                full_name="Administrator",
                role="admin",
                is_active_account=True,
            )
            user.set_password(default_password)
            db.session.add(user)
            db.session.commit()
            print(
                "WARNING: No users existed, so a default admin was created "
                f"(username='{default_username}', password='{default_password}'). "
                "Please sign in and change this password immediately."
            )

def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # --- Import models so SQLAlchemy knows all tables ---
    from app import models  # noqa: F401
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        """Reload the authenticated user from the session identifier."""
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    # --- Register blueprints ---
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.public import public_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # --- Template globals & context processors ---
    from app.utils.helpers import (
        format_money,
        status_badge_class,
        today_local,
        app_settings,
        theme_dict,
    )

    app.jinja_env.filters["money"] = format_money
    app.jinja_env.filters["badge"] = status_badge_class
    app.jinja_env.globals["today"] = today_local

    @app.context_processor
    def inject_settings():
        return {"settings": app_settings(), "theme": theme_dict()}

    # --- Error handlers ---
    register_error_handlers(app)

    # --- CLI commands ---
    register_cli(app)

    # --- Self-healing: create instance/ folder and tables if missing ---
    _ensure_instance_and_db(app)

    # --- Bootstrap an admin account from env vars if configured ---
    _ensure_admin_user(app)

    return app

def register_error_handlers(app):
    """Professional, non-technical error pages."""

    @app.errorhandler(404)
    def not_found(_e):
        return (
            render_error(
                "404",
                "Page Not Found",
                "The page you are looking for does not exist or has been moved.",
            ),
            404,
        )

    @app.errorhandler(403)
    def forbidden(_e):
        return (
            render_error(
                "403",
                "Access Denied",
                "You do not have permission to view this page.",
            ),
            403,
        )

    @app.errorhandler(500)
    def server_error(_e):
        # Roll back any failed session so the next request is clean.
        try:
            db.session.rollback()
        except Exception:
            pass
        return (
            render_error(
                "500",
                "Something Went Wrong",
                "An unexpected error occurred. Please try again later.",
            ),
            500,
        )

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_error("400", "Session Expired", str(e.description)), 400

def render_error(code, title, message):
    from flask import render_template

    return render_template(
        "error.html", code=code, title=title, message=message
    )

def register_cli(app):
    """Custom CLI commands for database setup and seeding."""

    @app.cli.command("init-db")
    def init_db():
        """Create all database tables (empty)."""
        from app import db as _db

        _db.create_all()
        print("Database tables created.")

    @app.cli.command("seed")
    def seed_cmd():
        """DISABLED: demo/seed data has been removed from this project.

        The seed command no longer inserts fake/demo data. The database
        should only contain real data entered through the application.
        """
        print(
            "The 'seed' command is disabled. Demo/fake data is no longer "
            "added to the database. Use 'flask init-db' to create empty "
            "tables if needed."
        )

    @app.cli.command("create-admin")
    def create_admin_cmd():
        """Create an administrator account (interactive).

        Use this on a fresh deployment (e.g. PythonAnywhere) where no admin
        exists yet. Prompts for username, email, full name and password.
        If the username or email already exists, the existing account is
        promoted to admin instead of creating a duplicate.
        """
        from app.models import User

        username = click.prompt("Admin username", default="admin").strip()
        email = click.prompt("Admin email", default="admin@hotel.com").strip().lower()
        full_name = click.prompt("Admin full name", default="Administrator").strip()
        password = click.prompt(
            "Admin password", default="admin123", hide_input=True,
            confirmation_prompt=True,
        )

        with app.app_context():
            user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            if user:
                user.role = "admin"
                user.is_active_account = True
                action = "promoted to admin"
            else:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role="admin",
                    is_active_account=True,
                )
                user.set_password(password)
                db.session.add(user)
                action = "created"

            db.session.commit()
            print(f"Admin account '{username}' {action} successfully.")
