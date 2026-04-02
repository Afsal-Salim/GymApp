"""Normalize phone numbers to exactly 10 digits (Indian mobile, stored without country code)."""

from __future__ import annotations

import re

PHONE_DIGIT_LENGTH = 10


def normalize_phone_10(value) -> str:
    """
    Strip non-digits; accept optional leading ``91`` or single leading ``0``.
    Returns exactly 10 digits.

    Raises:
        ValueError: if the result is not exactly 10 digits.
    """
    if value is None:
        value = ""
    digits = re.sub(r"\D", "", str(value).strip())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != PHONE_DIGIT_LENGTH:
        raise ValueError(
            "Phone must be exactly 10 digits (you may include +91 or one leading 0)."
        )
    return digits


def normalize_phone_10_or_empty(value) -> str:
    """Like ``normalize_phone_10`` but returns ``\"\"`` for blank input."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    return normalize_phone_10(value)
