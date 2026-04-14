"""Non-blocking SMTP: run Django send_mail in a daemon thread."""

import threading
from collections.abc import Callable
from typing import Any

from django.core.mail import send_mail

from core.logging import app_logger


def send_mail_in_background(
    *,
    thread_name: str = "send_mail",
    on_sent: Callable[[], None] | None = None,
    **send_mail_kwargs: Any,
) -> None:
    """
    Queue ``send_mail`` on a daemon thread so the HTTP handler returns without
    waiting for SMTP (often multi-second with remote providers).
    Failures are logged at ERROR with traceback; ``on_sent`` runs only after success.
    """

    def _run() -> None:
        try:
            send_mail(**send_mail_kwargs)
        except Exception:
            app_logger.exception(
                "Background send_mail failed",
                thread_name=thread_name,
                subject=send_mail_kwargs.get("subject"),
            )
            return
        if on_sent:
            on_sent()

    threading.Thread(target=_run, daemon=True, name=thread_name).start()


def run_in_background(
    fn: Callable[[], None],
    *,
    thread_name: str = "background_task",
) -> None:
    """
    Run ``fn`` on a daemon thread (e.g. ``EmailMultiAlternatives.send`` or other I/O).
    Exceptions are logged at ERROR with traceback.
    """

    def _run() -> None:
        try:
            fn()
        except Exception:
            app_logger.exception("Background task failed", thread_name=thread_name)

    threading.Thread(target=_run, daemon=True, name=thread_name).start()
