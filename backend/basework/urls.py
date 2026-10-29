from django.urls import path
from . import views

urlpatterns = [
    path('auth-options', views.auth_options),
    path('bootstrap', views.bootstrap),
    path('faq/items', views.faq_items),
    path('applications/<slug:application_id>', views.application),
    path('logout', views.logout),
    path('logout-all', views.logout, {'all_sessions': True}),
]
