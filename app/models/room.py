"""Room, RoomType, Housekeeping and Maintenance models."""
from datetime import datetime
from app import db


class RoomType(db.Model):
    __tablename__ = "room_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    bed_type = db.Column(db.String(80), nullable=True)
    facilities = db.Column(db.Text, nullable=True)  # comma separated
    image = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rooms = db.relationship("Room", back_populates="room_type", lazy="dynamic")

    @property
    def facility_list(self):
        if not self.facilities:
            return []
        return [f.strip() for f in self.facilities.split(",") if f.strip()]

    def __repr__(self):
        return f"<RoomType {self.name}>"


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"), nullable=False)
    floor = db.Column(db.Integer, default=1)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    bed_type = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, nullable=True)
    facilities = db.Column(db.Text, nullable=True)
    # available | reserved | occupied | cleaning | maintenance | out_of_service
    status = db.Column(db.String(20), nullable=False, default="available", index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    room_type = db.relationship("RoomType", back_populates="rooms")

    images = db.relationship(
        "RoomImage", back_populates="room", lazy="dynamic", cascade="all, delete-orphan"
    )

    reservations = db.relationship(
        "Reservation", back_populates="room", lazy="dynamic", foreign_keys="Reservation.room_id"
    )
    housekeeping_tasks = db.relationship(
        "HousekeepingTask", back_populates="room", lazy="dynamic"
    )
    maintenance_tasks = db.relationship(
        "MaintenanceTask", back_populates="room", lazy="dynamic"
    )

    @property
    def facility_list(self):
        if not self.facilities:
            return []
        return [f.strip() for f in self.facilities.split(",") if f.strip()]

    @property
    def assignable_statuses(self):
        return ("available", "reserved", "cleaning", "maintenance", "out_of_service")

    def __repr__(self):
        return f"<Room {self.room_number} ({self.status})>"


class HousekeepingTask(db.Model):
    __tablename__ = "housekeeping"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    task_code = db.Column(db.String(20), unique=True, nullable=False)
    # pending | in_progress | completed
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    assigned_to = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(db.String(100), nullable=True)

    room = db.relationship("Room", back_populates="housekeeping_tasks")

    def __repr__(self):
        return f"<HousekeepingTask {self.task_code} {self.status}>"


class MaintenanceTask(db.Model):
    __tablename__ = "maintenance"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    task_code = db.Column(db.String(20), unique=True, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    # open | in_progress | completed
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    requested_by = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    room = db.relationship("Room", back_populates="maintenance_tasks")

    def __repr__(self):
        return f"<MaintenanceTask {self.task_code} {self.status}>"
