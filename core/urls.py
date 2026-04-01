from django.urls import path

from core.views import SiteEnquiryCreateView

urlpatterns = [
    path("enquiries/", SiteEnquiryCreateView.as_view(), name="site-enquiry-create"),
]
