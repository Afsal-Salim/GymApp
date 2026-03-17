from django.urls import path

from . import views

urlpatterns = [
    path("", views.BusinessListCreateView.as_view(), name="business-list-create"),
    path("<slug:slug>/", views.BusinessDetailView.as_view(), name="business-detail"),
    path(
        "<slug:slug>/active-subscription/",
        views.BusinessActiveSubscriptionView.as_view(),
        name="business-active-subscription",
    ),
]
