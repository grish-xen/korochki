"""Маршруты API и собранного сайта."""

from django.urls import path
from portal import views

urlpatterns = [
    path("api/session", views.session),
    path("api/cookie-ack", views.cookie_ack),
    path("api/register", views.register),
    path("api/login", views.login_view),
    path("api/logout", views.logout_view),
    path("api/courses", views.courses),
    path("api/search", views.search),
    path("api/applications", views.applications),
    path("api/applications/<int:pk>/review", views.review),
    path("api/admin/applications", views.admin_applications),
    path("api/admin/applications/<int:pk>/status", views.change_status),
    path("", views.frontend),
    path("<path:path>", views.frontend),
]
