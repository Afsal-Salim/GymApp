"""Shared query filters for owner list APIs (search)."""

from django.db.models import Q


def enquiry_search_q(term: str) -> Q:
    """Match name, email, or message (case-insensitive)."""
    return (
        Q(name__icontains=term)
        | Q(email__icontains=term)
        | Q(message__icontains=term)
    )


def crystal_modal_lead_search_q(term: str) -> Q:
    """
    Match common string fields inside ``payload`` for modal leads.

    Includes ``notes`` (used e.g. on free-trial flow) as a message-like field.
    """
    return (
        Q(payload__name__icontains=term)
        | Q(payload__email__icontains=term)
        | Q(payload__message__icontains=term)
        | Q(payload__notes__icontains=term)
    )
