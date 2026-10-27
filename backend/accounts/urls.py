from django.urls import path
from . import views

urlpatterns = [
    path("csrf", views.csrf),
    path("login", views.login),
    path("logout", views.logout),
    path("session", views.session),
    path("invitations", views.invite),
    path("invitations/<uuid:invitation_id>/reinvite", views.reinvite),
    path("invitations/<uuid:invitation_id>/revoke", views.revoke),
    path("invitations/accept", views.accept),
    path("recovery/request", views.recovery_request),
    path("recovery/confirm", views.recovery_confirm),
]
