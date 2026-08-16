# Hotel Reservation & Check-In Desk System

A complete, production-style hotel management platform built with **Flask**, featuring a premium customer-facing website and a full-featured admin panel for front-desk staff and administrators.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Getting Started](#getting-started)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Demo Accounts](#demo-accounts)
7. [Project Structure](#project-structure)
8. [User Roles & Permissions](#user-roles--permissions)
9. [Business Rules](#business-rules)
10. [Modules Overview](#modules-overview)
11. [Running Tests](#running-tests)
12. [Security](#security)
13. [Design System](#design-system)

---

## Features

### Customer Website
- **Premium hotel homepage** with animated hero banner slider (fade / slide / zoom / fade-up), reservation search bar, featured rooms, services, promotional offers and "why choose us" sections
- **Rooms & room details** — filter by type, price and capacity
- **Online reservation** with live availability check and instant booking confirmation
- **About, Services and Contact** pages (contact messages go to the admin inbox)
- **Guest registration & sign-in**

### Admin Panel (`/admin`)
- **Dashboard** — live stats (rooms by status, today's arrivals/departures, pending payments, revenue), recent activity and quick actions
- **Room management** — 6 statuses, room types, floors, pricing and facilities
- **Reservations** — full lifecycle (pending → confirmed → checked-in → checked-out / cancelled), conflict-free assignment
- **Guest management** — profiles with ID documents and stay history
- **Check-In / Check-Out desks** — search by code/name, validate availability, generate invoices
- **Billing & payments** — itemised invoices, printable, partial payments supported
- **Housekeeping & maintenance** — task tracking with statuses
- **Booking calendar** — month view with colour-coded reservations
- **Reports** — occupancy, revenue, housekeeping, maintenance, arrivals/departures and more (9 types)
- **Staff management** — permission-based accounts (admin only)
- **Website content management** — hero banners, promo banners, branding/logo, settings, services and contact inbox
- **Notifications & activity logs**

---

## Tech Stack

| Layer      | Technology |
|------------|------------|
| Backend    | Python 3, Flask 3 (application factory + blueprints) |
| Database   | SQLite (local file in `instance/hotel.db`) |
| ORM        | Flask-SQLAlchemy, Flask-Migrate |
| Forms      | WTForms + Flask-WTF (CSRF protected) |
| Auth       | Flask-Login, Werkzeug password hashing |
| Frontend   | HTML5, CSS3, vanilla JavaScript (no frameworks) |
| Testing    | pytest |

---

## Getting Started

### 1. Clone & install

```bash
git clone <repository-url>
cd "Hotel Reservation and Check-in Desk system"
python -m venv venv
```

Activate the virtual environment:

- **Windows (cmd):** `venv\Scripts\activate`
- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source venv/bin/activate`

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy the example `.env` (or create one) — see [Configuration](#configuration):

```bash
FLASK_ENV=development
SECRET_KEY=your-long-random-secret-key
# Database is SQLite (instance/hotel.db) - no DATABASE_URL needed
```

### 3. Initialise the database

```bash
flask init-db        # create all tables (empty)
```

> **Note:** Demo/seed data has been **disabled**. `flask seed` no longer inserts
> any accounts or sample data — the database only ever contains real data you
> enter through the app.

### 4. Create the first admin account

On a fresh deployment (e.g. PythonAnywhere) the database starts **empty**, so
there is no account to log in with. The app handles this automatically:

**Automatic default admin (zero-config).** If the database has **no users at
all** on startup, the app creates a default administrator for you:

```
username: admin
password: admin123
```

> **Security:** Sign in at once and change this password from the admin
> **Account** page. The default admin is only created when the database is
> completely empty — it never overwrites an existing account.

**Option A — custom environment variables (recommended for deploys).** If you
prefer your own credentials, add these to your `.env` and reload the app — the
admin is created/updated automatically on startup (this takes priority over the
default admin above):

```ini
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourhotel.com
ADMIN_PASSWORD=your-strong-password
```

**Option B — CLI command.** Run this in a Bash/terminal with the venv active:

```bash
flask create-admin
```

### 5. Run the application

```bash
python run.py
# or
flask run
```

Open **http://127.0.0.1:5000** for the customer website and **http://127.0.0.1:5000/admin** for the admin panel.

---

## Configuration

All configuration lives in [`config.py`](config.py) and reads from environment variables — **never hard-code credentials**.

| Variable | Purpose | Default |
|----------|---------|---------|
| `FLASK_ENV` | `development`, `production` or `testing` | `development` |
| `SECRET_KEY` | Flask session signing key | dev-only fallback |
| `DATABASE_URL` | _(removed)_ - SQLite is used directly |
| `MAX_CONTENT_LENGTH` | Max upload size (bytes) | 8 MB |
| `HOST` / `PORT` | Server bind address | `127.0.0.1` / `5000` |
| `FLASK_DEBUG` | Debug mode toggle (`1`/`0`) | `1` |
| `ADMIN_USERNAME` | Bootstrap admin username (optional) | unset |
| `ADMIN_EMAIL` | Bootstrap admin email (optional) | unset |
| `ADMIN_PASSWORD` | Bootstrap admin password (optional) | unset |
| `ADMIN_FULL_NAME` | Bootstrap admin display name | `Administrator` |



```ini

```

---

## Database Setup

### CLI Commands

```bash
flask init-db        # create all tables
flask seed           # create tables (if needed) + seed demo data
flask db init        # (optional) enable Flask-Migrate migrations
flask db migrate     # generate a migration after model changes
flask db upgrade     # apply migrations
```

---

## Demo Accounts

> **Demo/seed data has been disabled.** `flask seed` no longer creates any
> accounts. On a fresh database there are no users until you create one.

Create the first administrator with the `flask create-admin` CLI command (or the
`ADMIN_*` environment variables described in [Configuration](#configuration)).
After that, additional staff and guest accounts are created through the app's
registration form and the admin **Staff** panel.

If you are migrating an existing local database, simply upload your
`instance/hotel.db` file to the server — your existing admin and all data will
be available immediately (no need to create a new account).

---

## Project Structure

```
├── app/
│   ├── __init__.py          # Application factory, extensions, error handlers, CLI
│   ├── forms/               # WTForms definitions
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py          # User (admin/staff/guest) + Staff profiles
│   │   ├── guest.py         # Guest profiles
│   │   ├── room.py          # RoomType, Room, HousekeepingTask, MaintenanceTask
│   │   ├── reservation.py   # Reservation, CheckIn, CheckOut
│   │   ├── finance.py       # Payment, Invoice
│   │   ├── content.py       # WebsiteSetting, HeroBanner, PromoBanner, Service, ContactMessage
│   │   └── notification.py  # Notification, ActivityLog
│   ├── routes/
│   │   ├── main.py          # Root redirect
│   │   ├── auth.py          # Login / register / logout
│   │   ├── public.py        # Customer website
│   │   └── admin.py         # Admin panel (url_prefix=/admin)
│   ├── services/
│   │   ├── availability.py  # Double-booking protection
│   │   ├── billing.py       # Billing calculations
│   │   ├── notifications.py # Notifications + activity logs
│   │   └── commit.py        # Commit + log helpers
│   ├── utils/
│   │   ├── constants.py     # Statuses, permissions, default settings
│   │   ├── decorators.py    # staff_required / admin_required / permission_required
│   │   ├── helpers.py       # Money, badges, codes, uploads, dates
│   │   └── seed.py          # Demo data seeder
│   ├── static/
│   │   ├── css/             # public.css, admin.css (design systems)
│   │   ├── js/              # public.js, admin.js (interactivity)
│   │   └── uploads/         # Uploaded images
│   └── templates/           # public/, admin/, auth/, error.html, base.html
├── tests/                   # pytest suite
├── config.py                # Environment-based configuration
├── run.py                   # Entry point
└── requirements.txt
```

---

## User Roles & Permissions

Three account roles backed by a fine-grained permission catalogue:

| Role  | Access |
|-------|--------|
| **Admin** | Everything, implicitly passes every permission check |
| **Staff** | Permission-based access configured per staff profile (e.g. `rooms.view`, `reservations.create`, `checkin.manage`) |
| **Guest** | Customer website only |

Permission decorators:

```python
@admin_bp.route("/rooms")
@permission_required("rooms.view")
def rooms():
    ...
```

- `@staff_required` — any admin or staff member
- `@admin_required` — administrators only (staff management)
- `@permission_required("module.action")` — granular control

The full permission catalogue is defined in [`app/utils/constants.py`](app/utils/constants.py).

---

## Business Rules

The system enforces these rules automatically:

1. **No double booking** — a room can never be assigned to two overlapping active reservations.
2. **Unassignable rooms** — occupied, cleaning, maintenance and out-of-service rooms are never offered.
3. **Date validation** — check-out must be after check-in; check-in cannot be in the past.
4. **Status workflow** — reservations move pending → confirmed → checked-in → checked-out; cancelled/deleted reservations free the room.
5. **Accurate billing** — room charge = rate × nights, plus additional charges, discounts and configurable tax.
6. **Payment tracking** — paid / partially paid / pending derived from amounts received.
7. **Housekeeping loop** — checked-out rooms flow back to available after cleaning.

---

## Modules Overview

| Module | Route prefix | Description |
|--------|--------------|-------------|
| Dashboard | `/admin/` | Stats, today's arrivals/departures, quick actions, activity feed |
| Rooms | `/admin/rooms` | CRUD + status changes + filters |
| Room Types | `/admin/room-types` | Catalogue with pricing, capacity, facilities |
| Reservations | `/admin/reservations` | List, create, edit, confirm, cancel, delete |
| Guests | `/admin/guests` | Profiles, ID docs, history |
| Check-In | `/admin/check-in` | Search reservation → assign room → check in |
| Check-Out | `/admin/check-out` | Search → settle bill → check out → housekeeping |
| Payments | `/admin/payments` | Record and view payments |
| Invoices | `/admin/invoices` | Printable itemised invoices |
| Housekeeping | `/admin/housekeeping` | Task lifecycle |
| Maintenance | `/admin/maintenance` | Task lifecycle |
| Calendar | `/admin/calendar` | Month view, colour-coded by status |
| Reports | `/admin/reports` | 9 report types with date ranges |
| Staff | `/admin/staff` | Accounts + permissions (admin only) |
| Content | `/admin/content` | Banners, branding, services, settings, contact inbox |
| Notifications | `/admin/notifications` | System alerts |
| Activity Logs | `/admin/activity-logs` | Audit trail |

---

## Running Tests

```bash
pip install -r requirements.txt   # includes pytest
pytest -v
```

The suite covers:

- **Availability** — overlap protection, status gating, filters, date validation
- **Billing** — money rounding, tax, discounts, payment status derivation
- **Permissions** — admin/staff/guest access and staff permission checks
- **Routes** — public pages, registration, login, admin access control

Tests use an in-memory SQLite database — no external services required.

---

## Security

- **Password hashing** via Werkzeug (`generate_password_hash`)
- **CSRF protection** on every form (Flask-WTF)
- **Role-based authorization** with per-action permissions
- **Session hardening** — HttpOnly + SameSite cookies; Secure in production
- **Upload validation** — extension allow-list and size limits
- **Input validation** — WTForms validators on all inputs
- **Professional error pages** — friendly 400/403/404/500 pages without stack traces

---

## Design System

**Palette**

| Token | Hex | Usage |
|-------|-----|-------|
| Deep Navy | `#14213D` | Headings, primary surfaces, admin sidebar |
| Royal Blue | `#1F4E79` | Links, secondary accents |
| Champagne Gold | `#C9A227` | CTAs, highlights, branding |
| Warm Ivory | `#FAF8F3` | Section backgrounds |
| White | `#FFFFFF` | Cards, panels |
| Light Gray | `#F4F5F7` | Table headers, muted surfaces |
| Charcoal | `#202124` | Body text |
| Muted Gray | `#6B7280` | Secondary text |

**Typography**

- **Playfair Display** — headings (elegant, hospitality feel)
- **Inter** — body copy (clean, readable)

**Style files**

- [`app/static/css/public.css`](app/static/css/public.css) — customer website design system
- [`app/static/css/admin.css`](app/static/css/admin.css) — admin panel design system
- [`app/static/js/public.js`](app/static/js/public.js) — slider, mobile nav, validation, animations
- [`app/static/js/admin.js`](app/static/js/admin.js) — sidebar toggle, flash handling, auto-print

**Responsive** — the site is fully responsive with a mobile navigation drawer and adaptive grids, from large desktops down to small phones.
"# Hotel-Reservation-and-check-in-desk-system"  
