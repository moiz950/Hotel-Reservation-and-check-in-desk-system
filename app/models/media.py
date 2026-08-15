"""Media and promotional models: room images, special offers, theme settings."""
from datetime import datetime, date

from app import db


class RoomImage(db.Model):
    """An image uploaded by the admin for a specific room (multiple per room)."""

    __tablename__ = "room_images"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False, index=True)
    image = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(160), nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    room = db.relationship(
        "Room",
        back_populates="images",
        lazy="joined",
    )

    def __repr__(self):
        return f"<RoomImage {self.id} room={self.room_id}>"


class SpecialOffer(db.Model):
    """A time-limited promotional offer created and managed by the admin."""

    __tablename__ = "special_offers"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    discount_details = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    badge_text = db.Column(db.String(60), nullable=True)
    cta_text = db.Column(db.String(80), nullable=True)
    cta_url = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_current(self):
        """Return True when the offer is active and within its date window."""
        if not self.is_active:
            return False
        today = date.today()
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

    def __repr__(self):
        return f"<SpecialOffer {self.title}>"


class ThemeSetting(db.Model):
    """Key/value store for the website theme (colors, mode)."""

    __tablename__ = "theme_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ThemeSetting {self.key}={self.value!r}>"
