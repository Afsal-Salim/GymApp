from django.urls import path

from . import views

urlpatterns = [
    path("", views.BusinessListCreateView.as_view(), name="business-list-create"),
    path(
        "website-setup/",
        views.CrystalWebsiteSetupView.as_view(),
        name="business-website-setup",
    ),
    path(
        "public/<slug:slug>/crystal-leads/",
        views.CrystalLeadCreateView.as_view(),
        name="business-crystal-leads-create",
    ),
    path(
        "public/<slug:slug>/",
        views.BusinessPublicBySlugView.as_view(),
        name="business-public-by-slug",
    ),
    path(
        "<slug:slug>/crystal-leads/analytics/",
        views.CrystalLeadAnalyticsView.as_view(),
        name="business-crystal-leads-analytics",
    ),
    path("<slug:slug>/", views.BusinessDetailView.as_view(), name="business-detail"),
    path(
        "<slug:slug>/active-subscription/",
        views.BusinessActiveSubscriptionView.as_view(),
        name="business-active-subscription",
    ),
]
