"""Website content models: settings, banners, services, contact messages."""
from datetime import datetime
from app import db


class WebsiteSetting(db.Model):
    """Key/value store for hotel information and website branding.

    Known keys are enumerated in app/utils/constants.py (DEFAULT_SETTINGS).
    """

    __tablename__ = "website_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    label = db.Column(db.String(120), nullable=True)
    group = db.Column(db.String(40), nullable=False, default="general")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<WebsiteSetting {self.key}={self.value!r}>"


class HeroBanner(db.Model):
    __tablename__ = "hero_banners"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)
    cta_text = db.Column(db.String(80), nullable=True)
    cta_url = db.Column(db.String(255), nullable=True)
    cta2_text = db.Column(db.String(80), nullable=True)
    cta2_url = db.Column(db.String(255), nullable=True)
    # fade | slide | zoom | fade_up
    animation = db.Column(db.String(20), nullable=False, default="fade")
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<HeroBanner {self.title}>"


class PromotionalBanner(db.Model):
    __tablename__ = "promotional_banners"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)
    badge_text = db.Column(db.String(60), nullable=True)
    cta_text = db.Column(db.String(80), nullable=True)
    cta_url = db.Column(db.String(255), nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PromotionalBanner {self.title}>"


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(60), nullable=True)  # icon class or emoji
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Service {self.name}>"


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContactMessage {self.name} {self.subject}>"
