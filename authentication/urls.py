from django.urls import path
from .views import (
    SignupView,
    LoginView,
    ForgotPasswordView,
    RefreshView,
    SendOTPView,
    VerifyOTPView,
)

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
]