from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('registro/', views.registro_cliente, name='registro_cliente'),
    # URLs de verificación desactivadas (descomentar si se reactiva la verificación)
    # path('verificar-telefono/', views.verificar_telefono, name='verificar_telefono'),
    # path('reenviar-codigo/', views.reenviar_codigo, name='reenviar_codigo'),
    path('login/', views.login_cliente, name='login_cliente'),
    path('logout/', views.logout_cliente, name='logout_cliente'),
]
