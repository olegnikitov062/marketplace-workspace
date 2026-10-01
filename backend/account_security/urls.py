from django.urls import path
from . import views

app_name = "account_security"
urlpatterns = [
    path("mfa/login/", views.PersonalLogin.as_view(), name="login"),
    path("mfa/setup/", views.PersonalSetup.as_view(), name="setup"),
    path("mfa/qr/", views.PersonalQR.as_view(), name="qr"),
    path("mfa/recovery/", views.recovery, name="recovery"),
    path("mfa/operator-recovery/", views.recovery, {"operator": True}, name="operator-recovery"),
    path("security/", views.panel, name="panel"),
    path("security/confirm/", views.confirm, name="confirm"),
    path("security/password/", views.password_change, name="password"),
    path("security/logout-all/", views.logout_all, name="logout-all"),
    path("security/sessions/<uuid:session_id>/revoke/", views.revoke_session, name="revoke-session"),
    path("security/devices/<uuid:device_id>/revoke/", views.revoke_device, name="revoke-device"),
    path("security/disable/", views.disable, name="disable"),
    path("security/probe/<uuid:permit_id>/", views.download, name="download"),
]
