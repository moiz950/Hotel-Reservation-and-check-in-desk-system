"""Billing calculation helpers."""
from decimal import Decimal, ROUND_HALF_UP


def money(value):
    """Normalise to a Decimal with two decimal places."""
    if value is None:
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, ArithmeticError):
        return Decimal("0.00")


def compute_stay(room_rate, nights, additional=0, discount=0, tax_rate=0):
    """Compute a full billing breakdown.

    Returns a dict with room_charge, additional_charges, discount, taxable_base,
    tax_amount, total and total_due (total after discount + tax).
    """
    rate = money(room_rate)
    nights = max(int(nights or 0), 0)
    additional = money(additional)
    discount = money(discount)
    tax_rate = Decimal(str(tax_rate or 0))

    room_charge = rate * nights
    subtotal = room_charge + additional - discount
    subtotal = max(subtotal, Decimal("0.00"))
    tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = subtotal + tax_amount

    return {
        "room_charge": room_charge,
        "additional_charges": additional,
        "discount": discount,
        "taxable_base": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
    }


def derive_payment_status(total, paid):
    """Derive payment status from amounts."""
    total = money(total)
    paid = money(paid)
    if total <= 0 or paid >= total:
        return "paid"
    if paid > 0:
        return "partially_paid"
    return "pending"
