from django.urls import path

from core.admin_views import (
    AdminEnquiryDetailView,
    AdminEnquiryListView,
    AdminSupportFeedbackDetailView,
    AdminSupportFeedbackListView,
    AdminUserDetailView,
    AdminUserListView,
    AdminWebsiteDetailView,
    AdminWebsiteListView,
)

urlpatterns = [
    path(
        "support-feedback/",
        AdminSupportFeedbackListView.as_view(),
        name="admin-support-feedback-list",
    ),
    path(
        "support-feedback/<int:pk>/",
        AdminSupportFeedbackDetailView.as_view(),
        name="admin-support-feedback-detail",
    ),
    path("enquiries/", AdminEnquiryListView.as_view(), name="admin-enquiries-list"),
    path(
        "enquiries/<int:pk>/",
        AdminEnquiryDetailView.as_view(),
        name="admin-enquiries-detail",
    ),
    path("websites/", AdminWebsiteListView.as_view(), name="admin-websites-list"),
    path(
        "websites/<slug:slug>/",
        AdminWebsiteDetailView.as_view(),
        name="admin-websites-detail",
    ),
    path("users/", AdminUserListView.as_view(), name="admin-users-list"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-users-detail"),
]
