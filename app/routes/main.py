"""Main blueprint.

The public homepage is served directly by ``public_bp.home`` at ``/``, so this
blueprint intentionally has no root route to avoid a redirect loop
(``/`` -> ``public.home`` -> ``/``).
"""
from flask import Blueprint

main_bp = Blueprint("main", __name__)
