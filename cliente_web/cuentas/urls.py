from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('registro/', views.registro_cliente, name='registro_cliente'),
    path('verificar-telefono/', views.verificar_telefono, name='verificar_telefono'),
    path('reenviar-codigo/', views.reenviar_codigo, name='reenviar_codigo'),
    path('validar-username/', views.validar_username, name='validar_username'),
    path('validar-email/', views.validar_email, name='validar_email'),
    path('validar-rut/', views.validar_rut, name='validar_rut'),
    path('validar-telefono/', views.validar_telefono, name='validar_telefono'),
    path('login/', views.login_cliente, name='login_cliente'),
    path('logout/', views.logout_cliente, name='logout_cliente'),
]
