import logging
from pathlib import Path

from django.conf import settings


def _format_log_message(message: str, context: dict) -> str:
    if not context:
        return message
    tail = " | " + " ".join(f"{k}={v!r}" for k, v in sorted(context.items()))
    return message + tail


class AppLogger:
    """
    Simple application-wide logger that writes to a file.

    Usage:
        from core.logging import app_logger
        app_logger.info("message", extra={"context": "value"})
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("gymapp")
        if not self._logger.handlers:
            self._configure()

    def _configure(self) -> None:
        self._logger.setLevel(logging.INFO)

        logs_dir = Path(getattr(settings, "LOGS_DIR", settings.BASE_DIR / "logs"))
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "gymapp.log"

        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s %(message)s"
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def info(self, message: str, **kwargs) -> None:
        self._logger.info(_format_log_message(message, kwargs))

    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(_format_log_message(message, kwargs))

    def error(self, message: str, **kwargs) -> None:
        self._logger.error(_format_log_message(message, kwargs))


app_logger = AppLogger()

