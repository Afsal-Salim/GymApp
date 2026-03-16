from django.urls import path
from .views import SignupView, LoginView, ForgotPasswordView, RefreshView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
]
