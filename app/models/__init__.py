"""Database models package.

Importing this module registers every model with SQLAlchemy metadata.
"""
from app.models.user import User, Staff
from app.models.guest import Guest
from app.models.room import RoomType, Room, HousekeepingTask, MaintenanceTask
from app.models.reservation import Reservation, CheckIn, CheckOut
from app.models.finance import Payment, Invoice
from app.models.content import (
    WebsiteSetting,
    HeroBanner,
    PromotionalBanner,
    Service,
    ContactMessage,
)
from app.models.notification import Notification, ActivityLog
from app.models.media import RoomImage, SpecialOffer, ThemeSetting

__all__ = [
    "User",
    "Staff",
    "Guest",
    "RoomType",
    "Room",
    "HousekeepingTask",
    "MaintenanceTask",
    "Reservation",
    "CheckIn",
    "CheckOut",
    "Payment",
    "Invoice",
    "WebsiteSetting",
    "HeroBanner",
    "PromotionalBanner",
    "Service",
    "ContactMessage",
    "Notification",
    "ActivityLog",
    "RoomImage",
    "SpecialOffer",
    "ThemeSetting",
]
