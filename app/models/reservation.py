"""Reservation, CheckIn and CheckOut models."""
from datetime import datetime, date
from app import db


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    reservation_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True, index=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"), nullable=True)

    check_in_date = db.Column(db.Date, nullable=False, index=True)
    check_out_date = db.Column(db.Date, nullable=False, index=True)
    adults = db.Column(db.Integer, nullable=False, default=1)
    children = db.Column(db.Integer, nullable=False, default=0)
    special_request = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(20), nullable=False, default="website")  # website | desk | phone

    # Financial summary
    room_rate = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    nights = db.Column(db.Integer, nullable=False, default=1)
    room_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    additional_charges = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    paid_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # pending | confirmed | checked_in | checked_out | cancelled
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    # pending | paid | partially_paid | refunded
    payment_status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    guest = db.relationship("Guest", back_populates="reservations", foreign_keys=[guest_id])
    room = db.relationship("Room", back_populates="reservations", foreign_keys=[room_id])
    room_type = db.relationship("RoomType", foreign_keys=[room_type_id])
    creator = db.relationship("User", foreign_keys=[created_by])

    check_ins = db.relationship(
        "CheckIn", back_populates="reservation", lazy="dynamic", cascade="all, delete-orphan"
    )
    check_outs = db.relationship(
        "CheckOut", back_populates="reservation", lazy="dynamic", cascade="all, delete-orphan"
    )
    payments = db.relationship(
        "Payment", back_populates="reservation", lazy="dynamic", cascade="all, delete-orphan"
    )
    invoices = db.relationship(
        "Invoice", back_populates="reservation", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def remaining_amount(self):
        return round(float(self.total_amount) - float(self.paid_amount), 2)

    @property
    def is_active(self):
        return self.status in ("pending", "confirmed", "checked_in")

    @property
    def nights_count(self):
        return (self.check_out_date - self.check_in_date).days

    def overlaps(self, check_in, check_out):
        """True when this reservation occupies any night inside [check_in, check_out)."""
        return self.check_in_date < check_out and check_in < self.check_out_date

    def __repr__(self):
        return f"<Reservation {self.reservation_code} {self.status}>"


class CheckIn(db.Model):
    __tablename__ = "check_ins"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(
        db.Integer, db.ForeignKey("reservations.id"), unique=True, nullable=False
    )
    checked_in_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    checked_in_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    reservation = db.relationship("Reservation", back_populates="check_ins")
    staff = db.relationship("User", foreign_keys=[checked_in_by])

    def __repr__(self):
        return f"<CheckIn reservation={self.reservation_id}>"


class CheckOut(db.Model):
    __tablename__ = "check_outs"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(
        db.Integer, db.ForeignKey("reservations.id"), unique=True, nullable=False
    )
    checked_out_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    checked_out_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    final_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    final_paid = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    reservation = db.relationship("Reservation", back_populates="check_outs")
    staff = db.relationship("User", foreign_keys=[checked_out_by])

    def __repr__(self):
        return f"<CheckOut reservation={self.reservation_id}>"
