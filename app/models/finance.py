"""Payment and Invoice models."""
from datetime import datetime
from app import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    payment_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"), nullable=False, index=True)
    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=True, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(40), nullable=False, default="cash")
    # cash | card | bank_transfer | online | other
    reference = db.Column(db.String(120), nullable=True)
    note = db.Column(db.String(255), nullable=True)
    received_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reservation = db.relationship("Reservation", back_populates="payments")
    guest = db.relationship("Guest", foreign_keys=[guest_id])
    staff = db.relationship("User", foreign_keys=[received_by])

    def __repr__(self):
        return f"<Payment {self.payment_code} {self.amount}>"


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"), nullable=False, index=True)
    room_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    additional_charges = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    paid = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="unpaid")
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reservation = db.relationship("Reservation", back_populates="invoices")
    staff = db.relationship("User", foreign_keys=[issued_by])

    @property
    def remaining(self):
        return round(float(self.total) - float(self.paid), 2)

    def __repr__(self):
        return f"<Invoice {self.invoice_number} {self.total}>"
