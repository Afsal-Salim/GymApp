"""
Authentication HTTP views, split by concern.

Import from ``authentication.views`` (this package) — same public API as before the refactor.
"""

from .google_auth import GoogleSignInView
from .otp import SendOTPView, VerifyOTPView
from .pages import LoginPageView, SignupPageView
from .password_reset import ForgotPasswordView, ResetPasswordView, VerifyResetOTPView
from .registration import LoginView, SignupView
from .session import RefreshView

__all__ = [
    "ForgotPasswordView",
    "GoogleSignInView",
    "LoginPageView",
    "LoginView",
    "RefreshView",
    "ResetPasswordView",
    "SendOTPView",
    "SignupPageView",
    "SignupView",
    "VerifyOTPView",
    "VerifyResetOTPView",
]
