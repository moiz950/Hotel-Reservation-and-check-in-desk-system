"""Shared constants for the hotel system."""

# --- Room statuses ---
ROOM_STATUSES = [
    ("available", "Available"),
    ("reserved", "Reserved"),
    ("occupied", "Occupied"),
    ("cleaning", "Cleaning"),
    ("maintenance", "Maintenance"),
    ("out_of_service", "Out of Service"),
]

# Statuses that must never be assigned to a new guest.
UNASSIGNABLE_ROOM_STATUSES = {"occupied", "cleaning", "maintenance", "out_of_service"}

# --- Reservation statuses ---
RESERVATION_STATUSES = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("checked_in", "Checked-In"),
    ("checked_out", "Checked-Out"),
    ("cancelled", "Cancelled"),
]

# Statuses counted as "active/blocking" for availability.
BLOCKING_RESERVATION_STATUSES = ["pending", "confirmed", "checked_in"]

# --- Payment statuses ---
PAYMENT_STATUSES = [
    ("pending", "Pending"),
    ("partially_paid", "Partially Paid"),
    ("paid", "Paid"),
]

# --- Payment methods ---
PAYMENT_METHODS = [
    ("cash", "Cash"),
    ("card", "Card"),
    ("bank_transfer", "Bank Transfer"),
    ("online", "Online Payment"),
    ("other", "Other"),
]

# --- Staff permission catalogue ---
PERMISSIONS = {
    "dashboard": {
        "label": "Dashboard",
        "items": {
            "dashboard.view": "View dashboard",
        },
    },
    "rooms": {
        "label": "Rooms",
        "items": {
            "rooms.view": "View rooms",
            "rooms.create": "Create rooms",
            "rooms.edit": "Edit rooms",
            "rooms.delete": "Delete rooms",
        },
    },
    "room_types": {
        "label": "Room Types",
        "items": {
            "room_types.view": "View room types",
            "room_types.manage": "Manage room types",
        },
    },
    "reservations": {
        "label": "Reservations",
        "items": {
            "reservations.view": "View reservations",
            "reservations.create": "Create reservations",
            "reservations.edit": "Edit reservations",
            "reservations.cancel": "Cancel reservations",
            "reservations.delete": "Delete reservations",
        },
    },
    "guests": {
        "label": "Guests",
        "items": {
            "guests.view": "View guests",
            "guests.create": "Create guests",
            "guests.edit": "Edit guests",
            "guests.delete": "Delete guests",
        },
    },
    "front_desk": {
        "label": "Front Desk",
        "items": {
            "checkin.manage": "Manage check-ins",
            "checkout.manage": "Manage check-outs",
            "calendar.view": "View booking calendar",
        },
    },
    "finance": {
        "label": "Finance",
        "items": {
            "payments.view": "View payments",
            "payments.record": "Record payments",
            "invoices.view": "View invoices",
            "invoices.print": "Print invoices",
        },
    },
    "operations": {
        "label": "Operations",
        "items": {
            "housekeeping.manage": "Manage housekeeping",
            "maintenance.manage": "Manage maintenance",
        },
    },
    "reports": {
        "label": "Reports",
        "items": {
            "reports.view": "View reports",
        },
    },
    "management": {
        "label": "Management",
        "items": {
            "staff.manage": "Manage staff",
            "content.manage": "Manage website content",
            "notifications.manage": "Manage notifications",
            "logs.view": "View activity logs",
            "settings.manage": "Manage settings",
        },
    },
}

# Flatten all permission keys for quick checks.
ALL_PERMISSIONS = [
    key for group in PERMISSIONS.values() for key in group["items"].keys()
]

# --- Website settings defaults ---
DEFAULT_SETTINGS = {
    # General / branding
    "hotel_name": {"value": "Grand Meridian Hotel", "label": "Hotel Name", "group": "general"},
    "tagline": {
        "value": "Experience Comfort. Discover Luxury.",
        "label": "Tagline",
        "group": "general",
    },
    "hotel_description": {
        "value": "A luxury hotel offering elegant rooms, premium facilities, and exceptional "
        "hospitality in the heart of the city.",
        "label": "Hotel Description",
        "group": "general",
    },
    "logo": {"value": "", "label": "Logo", "group": "branding"},
    "favicon": {"value": "", "label": "Favicon", "group": "branding"},
    "currency": {"value": "Rs.", "label": "Currency Symbol", "group": "general"},
    "tax_rate": {"value": "10", "label": "Default Tax Rate (%)", "group": "finance"},
    # Contact
    "address": {
        "value": "123 Luxury Avenue, Downtown, City",
        "label": "Address",
        "group": "contact",
    },
    "phone": {"value": "+1 (555) 123-4567", "label": "Phone", "group": "contact"},
    "email": {"value": "reservations@grandmeridian.com", "label": "Email", "group": "contact"},
    "check_in_time": {"value": "14:00", "label": "Check-In Time", "group": "contact"},
    "check_out_time": {"value": "12:00", "label": "Check-Out Time", "group": "contact"},
    "front_desk_hours": {
        "value": "Open 24 Hours",
        "label": "Front Desk Hours",
        "group": "contact",
    },
    # Social
    "facebook": {"value": "https://facebook.com", "label": "Facebook URL", "group": "social"},
    "twitter": {"value": "https://twitter.com", "label": "Twitter URL", "group": "social"},
    "instagram": {"value": "https://instagram.com", "label": "Instagram URL", "group": "social"},
    "linkedin": {"value": "https://linkedin.com", "label": "LinkedIn URL", "group": "social"},
    # Policies & text
    "hotel_policies": {
        "value": "Check-in from 2:00 PM. Check-out by 12:00 noon. Pets allowed on request. "
        "Free cancellation up to 24 hours before arrival.",
        "label": "Hotel Policies",
        "group": "policies",
    },
    "homepage_intro_title": {
        "value": "Welcome to Grand Meridian Hotel",
        "label": "Homepage Intro Title",
        "group": "homepage",
    },
    "homepage_intro_text": {
        "value": "Discover a world of refined comfort and impeccable service. Our elegantly "
        "appointed rooms, world-class dining, and thoughtful amenities create the perfect "
        "setting for business and leisure travel.",
        "label": "Homepage Intro Text",
        "group": "homepage",
    },
    "why_choose_title": {
        "value": "Why Choose Us",
        "label": "Why Choose Us Title",
        "group": "homepage",
    },
    "why_choose_text": {
        "value": "From our prime location to our round-the-clock service, every detail is designed "
        "to make your stay effortless and memorable.",
        "label": "Why Choose Us Text",
        "group": "homepage",
    },
    "footer_about": {
        "value": "Grand Meridian Hotel offers an unforgettable stay with elegant rooms, "
        "premium facilities, and exceptional hospitality.",
        "label": "Footer About Text",
        "group": "footer",
    },
    "copyright_text": {
        "value": "© 2025 Grand Meridian Hotel. All rights reserved.",
        "label": "Copyright Text",
        "group": "footer",
    },
    "map_embed": {"value": "", "label": "Map Embed Code", "group": "contact"},
    # Page hero banners (editable images; fall back to gradient when empty)
    "banner_rooms": {"value": "", "label": "Rooms & Suites Page Banner", "group": "page_banners"},
    "banner_about": {"value": "", "label": "About Page Banner", "group": "page_banners"},
    "banner_contact": {"value": "", "label": "Contact Page Banner", "group": "page_banners"},
    "banner_services": {"value": "", "label": "Services Page Banner", "group": "page_banners"},
}

# --- Animation choices for hero banners ---
BANNER_ANIMATIONS = [
    ("fade", "Fade"),
    ("slide", "Slide"),
    ("zoom", "Zoom"),
    ("fade_up", "Fade & Slide Up"),
]
