from django.urls import path

from . import views

urlpatterns = [
    path("create-order/", views.CreateOrderView.as_view(), name="payments-create-order"),
    path("verify/", views.VerifyPaymentView.as_view(), name="payments-verify"),
]
