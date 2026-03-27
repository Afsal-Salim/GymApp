from django.urls import path
from .views import (
    SignupView,
    LoginView,
    GoogleSignInView,
    ForgotPasswordView,
    VerifyResetOTPView,
    ResetPasswordView,
    RefreshView,
    MeView,
    SendOTPView,
    VerifyOTPView,
)

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("google/", GoogleSignInView.as_view(), name="google_signin"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("verify-reset-otp/", VerifyResetOTPView.as_view(), name="verify_reset_otp"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="auth_me"),
]