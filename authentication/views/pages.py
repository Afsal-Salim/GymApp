from django.conf import settings
from django.views.generic import TemplateView


class LoginPageView(TemplateView):
    """Serves the login page with email/password and Sign in with Google."""

    template_name = "authentication/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["google_client_id"] = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "") or ""
        return ctx


class SignupPageView(TemplateView):
    """Serves the signup page with email signup and Sign up with Google."""

    template_name = "authentication/signup.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["google_client_id"] = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "") or ""
        return ctx
