"""Tests for the billing calculation service."""
from decimal import Decimal

from app.services.billing import compute_stay, derive_payment_status, money


def test_money_normalisation():
    assert money(None) == Decimal("0.00")
    assert money("12.345") == Decimal("12.35")  # rounds half-up
    assert money(12) == Decimal("12.00")
    assert money("abc") == Decimal("0.00")


def test_compute_stay_basic():
    result = compute_stay(120, 3)
    assert result["room_charge"] == Decimal("360.00")
    assert result["tax_amount"] == Decimal("0.00")
    assert result["total"] == Decimal("360.00")


def test_compute_stay_with_tax():
    result = compute_stay(100, 2, tax_rate=10)
    assert result["room_charge"] == Decimal("200.00")
    assert result["tax_amount"] == Decimal("20.00")
    assert result["total"] == Decimal("220.00")


def test_compute_stay_with_additional_and_discount():
    result = compute_stay(100, 3, additional=50, discount=30, tax_rate=10)
    # room 300 + additional 50 - discount 30 = 320; tax 32; total 352
    assert result["room_charge"] == Decimal("300.00")
    assert result["tax_amount"] == Decimal("32.00")
    assert result["total"] == Decimal("352.00")


def test_compute_stay_discount_cannot_force_negative():
    result = compute_stay(100, 1, additional=0, discount=500, tax_rate=0)
    assert result["total"] == Decimal("0.00")


def test_derive_payment_status():
    assert derive_payment_status(200, 200) == "paid"
    assert derive_payment_status(200, 250) == "paid"
    assert derive_payment_status(200, 100) == "partially_paid"
    assert derive_payment_status(200, 0) == "pending"
    assert derive_payment_status(0, 0) == "paid"
