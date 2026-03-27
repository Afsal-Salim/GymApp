import logging
from typing import Any

from django.conf import settings


def _format_log_message(message: str, context: dict[str, Any]) -> str:
    if not context:
        return message
    tail = " | " + " ".join(f"{k}={v!r}" for k, v in sorted(context.items()))
    return message + tail


class AppLogger:
    """
    Application logger for the ``gymapp`` namespace.

    Handlers and levels are configured in ``settings.LOGGING`` (see ``config/settings.py``).
    Use keyword arguments for structured context; they are appended to the log line.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("gymapp")

    def debug(self, message: str, **kwargs: Any) -> None:
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(_format_log_message(message, kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(_format_log_message(message, kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self._logger.warning(_format_log_message(message, kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(_format_log_message(message, kwargs))

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log at ERROR with exception traceback (call from an ``except`` block or with active exception)."""
        self._logger.error(
            _format_log_message(message, kwargs),
            exc_info=True,
        )


app_logger = AppLogger()
