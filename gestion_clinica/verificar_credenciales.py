"""
Script para verificar la creación de PerfilCliente y configuración de email
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import connection
from django.conf import settings

def verificar_perfil_cliente(username):
    """Verifica si existe un PerfilCliente para un usuario"""
    try:
        user = User.objects.get(username=username)
        print(f"✅ Usuario encontrado: {username} (ID: {user.id})")
        
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre_completo, email, telefono FROM cuentas_perfilcliente WHERE user_id = %s",
                [user.id]
            )
            perfil = cursor.fetchone()
            
            if perfil:
                print(f"✅ PerfilCliente encontrado:")
                print(f"   ID: {perfil[0]}")
                print(f"   Nombre: {perfil[1]}")
                print(f"   Email: {perfil[2]}")
                print(f"   Teléfono: {perfil[3]}")
                return True
            else:
                print(f"❌ No se encontró PerfilCliente para el usuario {username}")
                return False
    except User.DoesNotExist:
        print(f"❌ Usuario {username} no existe")
        return False
    except Exception as e:
        print(f"❌ Error al verificar: {e}")
        return False

def verificar_configuracion_email():
    """Verifica la configuración de email"""
    print("\n=== Verificación de Configuración de Email ===")
    print(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'No configurado')}")
    print(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'No configurado')}")
    print(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'No configurado')}")
    print(f"EMAIL_HOST_USER: {'Configurado' if getattr(settings, 'EMAIL_HOST_USER', '') else '❌ NO CONFIGURADO'}")
    print(f"EMAIL_HOST_PASSWORD: {'Configurado' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else '❌ NO CONFIGURADO'}")
    print(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'No configurado')}")
    
    email_user = getattr(settings, 'EMAIL_HOST_USER', '')
    email_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    
    if email_user and email_pass:
        print("\n✅ Configuración de email completa")
        return True
    else:
        print("\n❌ Configuración de email incompleta")
        print("   Agrega EMAIL_HOST_USER y EMAIL_HOST_PASSWORD al archivo .env")
        return False

if __name__ == '__main__':
    print("=== Verificación de Credenciales ===\n")
    
    # Verificar configuración de email
    email_ok = verificar_configuracion_email()
    
    # Si se proporciona un username como argumento, verificar su PerfilCliente
    if len(sys.argv) > 1:
        username = sys.argv[1]
        print(f"\n=== Verificando PerfilCliente para: {username} ===")
        verificar_perfil_cliente(username)
    else:
        print("\n💡 Uso: python verificar_credenciales.py <username>")
        print("   Ejemplo: python verificar_credenciales.py juan_perez")






