"""Application factory for the Hotel Reservation & Check-In Desk System."""
import os
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
    from app.utils.seed import seed_data

    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        from app import db as _db

        _db.create_all()
        print("Database tables created.")

    @app.cli.command("seed")
    def seed_cmd():
        """Create tables (if needed) and populate demo data."""
        from app import db as _db

        _db.create_all()
        seed_data()
        print("Database seeded with demo data.")
