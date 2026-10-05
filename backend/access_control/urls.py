from django.urls import path
from . import views

tenant = 'organizations/<uuid:organization_id>/'
record = tenant + 'cabinets/<uuid:cabinet_id>/synthetic/<uuid:record_id>/'
urlpatterns = [
    path('platform/status/', views.platform_status),
    path(tenant + 'memberships/', views.memberships),
    path(tenant + 'grants/', views.grant),
    path(tenant + 'grants/<uuid:grant_id>/revoke/', views.revoke),
    path(tenant + 'memberships/<uuid:membership_id>/template/', views.template),
    path(tenant + 'memberships/<uuid:membership_id>/suspend/', views.suspend),
    path(tenant + 'support/', views.support_open),
    path(tenant + 'support/<uuid:window_id>/close/', views.support_close),
    path(record, views.record),
    path(record + 'change/', views.change),
    path(record + 'export/', views.export),
]
