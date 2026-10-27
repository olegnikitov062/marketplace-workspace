from django.urls import path
from . import views

urlpatterns = [
    path('bootstrap', views.bootstrap),
    path('applications/<slug:application_id>', views.application),
    path('logout', views.logout),
    path('logout-all', views.logout, {'all_sessions': True}),
]
