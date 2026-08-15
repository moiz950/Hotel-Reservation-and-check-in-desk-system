"""Guest model."""
from datetime import datetime
from app import db


class Guest(db.Model):
    __tablename__ = "guests"

    id = db.Column(db.Integer, primary_key=True)
    guest_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False, index=True)
    email = db.Column(db.String(160), nullable=True, index=True)
    phone = db.Column(db.String(30), nullable=True, index=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(80), nullable=True)
    country = db.Column(db.String(80), nullable=True)
    id_type = db.Column(db.String(40), nullable=True)  # Passport / ID Card / Driving License
    id_number = db.Column(db.String(80), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])
    reservations = db.relationship(
        "Reservation", back_populates="guest", lazy="dynamic", foreign_keys="Reservation.guest_id"
    )

    @property
    def current_reservation(self):
        """Return the active (not cancelled/checked-out) reservation, newest first."""
        from app.models.reservation import Reservation

        return (
            self.reservations.order_by(db.desc("id"))
            .filter(Reservation.status.in_(["pending", "confirmed", "checked_in"]))
            .first()
        )

    def __repr__(self):
        return f"<Guest {self.guest_code} {self.full_name}>"
