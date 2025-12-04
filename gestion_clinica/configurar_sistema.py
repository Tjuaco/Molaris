import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.contrib.auth.models import User
from personal.models import Perfil
from configuracion.models import InformacionClinica

print("=" * 60)
print("CONFIGURACIÓN DEL SISTEMA")
print("=" * 60)
print()

# 1. Configurar usuario como staff y superusuario
print("1. Configurando usuario...")
try:
    user = User.objects.get(username='j_administrativo')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"   ✓ Usuario '{user.username}' configurado como staff y superusuario")
except User.DoesNotExist:
    print("   ✗ Usuario no encontrado")
except Exception as e:
    print(f"   ✗ Error: {e}")

print()

# 2. Actualizar información de la clínica
print("2. Actualizando información de la clínica...")
try:
    info = InformacionClinica.obtener()
    info.nombre_clinica = "Clínica Dental San Felipe"
    if info.direccion == "Ingrese la dirección de la clínica" or not info.direccion:
        info.direccion = "Av Manuel Rodriguez #1625, Victoria"
    if info.telefono == "+56912345678" or not info.telefono:
        info.telefono = "+56920589344"  # Tu número
    if info.email == "contacto@clinica.com" or not info.email:
        info.email = "contacto@clinicadentalsanfelipe.cl"
    info.save()
    print(f"   ✓ Información actualizada:")
    print(f"     - Nombre: {info.nombre_clinica}")
    print(f"     - Dirección: {info.direccion}")
    print(f"     - Teléfono: {info.telefono}")
    print(f"     - Email: {info.email}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print()
print("=" * 60)
print("✓ Configuración completada")
print("=" * 60)
print()
print("Ahora puedes iniciar sesión con:")
print("  Usuario: j_administrativo")
print("  (Usa la contraseña que configuraste anteriormente)")
print()
print("Si no recuerdas la contraseña, puedes cambiarla con:")
print("  python manage.py changepassword j_administrativo")







