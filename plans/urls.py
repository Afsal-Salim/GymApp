from django.urls import path

from . import views

urlpatterns = [
    path("plan_list/", views.PlanListView.as_view(), name="plan-list"),
]
