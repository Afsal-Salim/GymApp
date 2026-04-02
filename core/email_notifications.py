"""Email alerts to the Crystal team (new signups, website enquiries)."""

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string

from core.logging import app_logger


def _team_inbox() -> str:
    return (getattr(settings, "CRYSTAL_TEAM_NOTIFY_EMAIL", None) or "").strip()


def notify_new_potential_client(
    *,
    email: str,
    username: str,
    customer_id: int,
    source: str,
) -> None:
    """
    Inform the team when someone new registers (email signup or new Google account).
    Uses Reply-To so you can reply directly to the client. Fails silently; signup still succeeds.
    """
    if not getattr(settings, "NEW_USER_NOTIFY_ENABLED", True):
        return
    to = _team_inbox()
    if not to:
        app_logger.warning("NEW_USER_NOTIFY skipped: CRYSTAL_TEAM_NOTIFY_EMAIL not set")
        return
    from_email = settings.DEFAULT_FROM_EMAIL
    if not from_email:
        app_logger.warning("NEW_USER_NOTIFY skipped: DEFAULT_FROM_EMAIL not set")
        return

    subject = getattr(settings, "NEW_USER_NOTIFY_SUBJECT", "New potential client – Crystal Gym")
    body = (
        f"A new user signed up on Crystal Gym.\n\n"
        f"Treat as: potential client\n"
        f"Source: {source}\n"
        f"Username: {username}\n"
        f"Email: {email}\n"
        f"Customer ID: {customer_id}\n"
    )
    try:
        kwargs = {"subject": subject, "body": body, "from_email": from_email, "to": [to]}
        if email:
            kwargs["reply_to"] = [email]
        msg = EmailMessage(**kwargs)
        msg.send(fail_silently=False)
        app_logger.info("New user notify email sent", customer_id=customer_id, source=source)
    except Exception as e:
        app_logger.warning(
            "New user notify email failed",
            customer_id=customer_id,
            error=str(e),
        )


def notify_site_enquiry(
    *,
    name: str,
    email: str,
    message: str,
    phone: str = "",
    service_topic: str = "",
    enquiry_kind: str = "general",
) -> None:
    """Send website / service enquiry to team inbox. Reply-To is the visitor."""
    to = _team_inbox()
    if not to:
        app_logger.warning("Enquiry email skipped: CRYSTAL_TEAM_NOTIFY_EMAIL not set")
        return
    from_email = settings.DEFAULT_FROM_EMAIL
    if not from_email:
        app_logger.warning("Enquiry email skipped: DEFAULT_FROM_EMAIL not set")
        return

    is_service = enquiry_kind == "service"
    subject = (
        getattr(
            settings,
            "SERVICE_ENQUIRY_EMAIL_SUBJECT",
            "Service enquiry – Crystal Gym",
        )
        if is_service
        else getattr(
            settings,
            "SITE_ENQUIRY_EMAIL_SUBJECT",
            "Website enquiry – Crystal Gym",
        )
    )
    context = {
        "name": name,
        "email": email,
        "message": message,
        "phone": (phone or "").strip(),
        "service_topic": (service_topic or "").strip(),
        "enquiry_kind": enquiry_kind,
        "is_service": is_service,
    }
    html_body = render_to_string("core/email_site_enquiry.html", context)
    plain_lines = [
        (
            "New service enquiry from the Crystal Gym website."
            if is_service
            else "New enquiry from the Crystal Gym website."
        ),
        "",
        f"Name: {name}",
        f"Email: {email}",
    ]
    if context["phone"]:
        plain_lines.append(f"Phone: {context['phone']}")
    if context["service_topic"]:
        plain_lines.append(f"Service / topic: {context['service_topic']}")
    plain_lines.extend(["", "Message:", message])
    plain_body = "\n".join(plain_lines)
    try:
        alt_kwargs = {
            "subject": subject,
            "body": plain_body,
            "from_email": from_email,
            "to": [to],
        }
        if email:
            alt_kwargs["reply_to"] = [email]
        msg = EmailMultiAlternatives(**alt_kwargs)
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        app_logger.info("Site enquiry email sent", enquiry_email=email)
    except Exception as e:
        app_logger.warning("Site enquiry email failed", error=str(e))


def notify_client_support_feedback(
    *,
    customer_email: str,
    customer_username: str,
    customer_id: int,
    kind: str,
    subject: str,
    message: str,
    message_id: int,
) -> None:
    """Email team when a logged-in client submits support or feedback."""
    to = _team_inbox()
    if not to:
        app_logger.warning("Client support email skipped: CRYSTAL_TEAM_NOTIFY_EMAIL not set")
        return
    from_email = settings.DEFAULT_FROM_EMAIL
    if not from_email:
        app_logger.warning("Client support email skipped: DEFAULT_FROM_EMAIL not set")
        return

    kind_label = "Support request" if kind == "support" else "Feedback"
    prefix = getattr(
        settings,
        "CLIENT_SUPPORT_EMAIL_SUBJECT_PREFIX",
        "[Crystal Gym]",
    ).strip() or "[Crystal Gym]"
    email_subject = f"{prefix} {kind_label} from {customer_username}"

    context = {
        "kind_label": kind_label,
        "username": customer_username,
        "customer_email": customer_email,
        "customer_id": customer_id,
        "subject": (subject or "").strip(),
        "message": message,
        "message_id": message_id,
    }
    html_body = render_to_string("core/email_client_support_feedback.html", context)
    plain_lines = [
        f"{kind_label} (Crystal Gym)",
        "",
        f"Client: {customer_username} <{customer_email}>",
        f"Customer ID: {customer_id}",
        f"Submission ID: {message_id}",
    ]
    if subject:
        plain_lines.append(f"Subject: {subject}")
    plain_lines.extend(["", "Message:", message])
    plain_body = "\n".join(plain_lines)

    try:
        alt_kwargs = {
            "subject": email_subject,
            "body": plain_body,
            "from_email": from_email,
            "to": [to],
        }
        if customer_email:
            alt_kwargs["reply_to"] = [customer_email]
        msg = EmailMultiAlternatives(**alt_kwargs)
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        app_logger.info(
            "Client support/feedback email sent",
            customer_id=customer_id,
            kind=kind,
            message_id=message_id,
        )
    except Exception as e:
        app_logger.warning(
            "Client support/feedback email failed",
            customer_id=customer_id,
            error=str(e),
        )
