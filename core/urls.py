from django.urls import path

from core.views import ServiceEnquiryCreateView, SiteEnquiryCreateView

urlpatterns = [
    path("enquiries/", SiteEnquiryCreateView.as_view(), name="site-enquiry-create"),
    path(
        "service-enquiries/",
        ServiceEnquiryCreateView.as_view(),
        name="service-enquiry-create",
    ),
]
