from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    #path('', views.dashboard, name='home'),
    path('', RedirectView.as_view(url='/dashboard/'), name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('select-client/', views.select_client, name='select_client'),
    path('dev/set-role/<str:role>/', views.set_role, name='set_role'),
]