"""
HTTP request lifecycle logging: each call, view dispatch, completion (and exceptions).
"""

import time
import uuid

from django.utils.deprecation import MiddlewareMixin

from core.logging import app_logger


def _request_id(request) -> str:
    return getattr(request, "_req_log_id", "")


def _should_log_path(path: str) -> bool:
    if path in ("/favicon.ico",):
        return False
    if path.startswith("/static/") or path.startswith("/media/"):
        return False
    return True


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Logs INFO for: request received, view about to run, response sent.
    Logs WARNING if an unhandled exception propagates from a view.
    Place after AuthenticationMiddleware so ``request.user`` is populated.
    """

    def process_request(self, request):
        if not _should_log_path(request.path):
            request._req_log_skip = True
            return None
        request._req_log_skip = False
        request._req_log_id = uuid.uuid4().hex[:12]
        request._req_log_start = time.perf_counter()
        query = request.META.get("QUERY_STRING", "") or ""
        ctx = {
            "request_id": request._req_log_id,
            "method": request.method,
            "path": request.path,
            "remote_addr": request.META.get("REMOTE_ADDR", ""),
            "authorization": (
                "present"
                if request.META.get("HTTP_AUTHORIZATION")
                else "absent"
            ),
        }
        if query:
            ctx["query"] = query
        app_logger.debug("API request received", **ctx)
        app_logger.debug(
            "API request meta",
            request_id=request._req_log_id,
            content_type=request.META.get("CONTENT_TYPE") or "",
            content_length=request.META.get("CONTENT_LENGTH") or "",
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:200],
            referer=(request.META.get("HTTP_REFERER") or "")[:200],
        )
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(request, "_req_log_skip", False):
            return None
        view_name = getattr(view_func, "__qualname__", None) or getattr(
            view_func, "__name__", str(view_func)
        )
        user = getattr(request, "user", None)
        user_label = (
            str(user.pk)
            if user is not None and getattr(user, "is_authenticated", False)
            else "anonymous"
        )
        rm = getattr(request, "resolver_match", None)
        url_name = rm.url_name if rm else None
        app_logger.debug(
            "API dispatch",
            request_id=_request_id(request),
            view=view_name,
            user=user_label,
            url_name=url_name,
        )
        app_logger.debug(
            "API dispatch args",
            request_id=_request_id(request),
            view_args=repr(view_args)[:500],
            view_kwargs=repr(view_kwargs)[:500],
        )
        return None

    def process_response(self, request, response):
        if getattr(request, "_req_log_skip", False):
            return response
        start = getattr(request, "_req_log_start", None)
        duration_ms = (
            int((time.perf_counter() - start) * 1000) if start is not None else None
        )
        status_code = getattr(response, "status_code", None)
        app_logger.info(
            "API response sent",
            request_id=_request_id(request),
            status_code=status_code,
            duration_ms=duration_ms,
        )
        if status_code is not None and status_code >= 500:
            app_logger.error(
                "API response indicates server error",
                request_id=_request_id(request),
                status_code=status_code,
                path=request.path,
                method=request.method,
            )
        elif status_code is not None and status_code >= 400:
            app_logger.debug(
                "API response client error",
                request_id=_request_id(request),
                status_code=status_code,
                path=request.path,
            )
        return response

    def process_exception(self, request, exception):
        if getattr(request, "_req_log_skip", False):
            return None
        rm = getattr(request, "resolver_match", None)
        app_logger.exception(
            "API unhandled exception",
            request_id=_request_id(request),
            method=request.method,
            path=request.path,
            url_name=rm.url_name if rm else None,
            exc_type=type(exception).__name__,
            exc_message=str(exception)[:1000],
        )
        return None
