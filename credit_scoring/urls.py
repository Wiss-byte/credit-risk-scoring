from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dossier/nouveau/', views.nouveau_dossier, name='nouveau_dossier'),
    path('dossier/scanner/', views.scanner_document, name='scanner_document'),
    path('chatbot/<int:dossier_id>/', views.chatbot, name='chatbot'),
    path('dossier/<int:dossier_id>/shap/', views.explication_shap, name='explication_shap'),
    path('register/', views.register, name='register'),
    path('administration/', views.administration, name='administration'),
    path('simulation-seuil/', views.simulation_seuil, name='simulation_seuil'),
    path('monitoring-drift/', views.monitoring_drift, name='monitoring_drift'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]