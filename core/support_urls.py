from django.urls import path

from core.views import ClientSupportFeedbackView

urlpatterns = [
    path("", ClientSupportFeedbackView.as_view(), name="client-support-feedback"),
]
