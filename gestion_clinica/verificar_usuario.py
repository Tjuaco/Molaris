import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.contrib.auth.models import User
from personal.models import Perfil

print("=" * 50)
print("VERIFICACIÓN DE USUARIOS Y PERFILES")
print("=" * 50)
print()

# Verificar usuarios
users = User.objects.all()
print(f"Usuarios encontrados: {users.count()}")
for user in users:
    print(f"\n  Usuario: {user.username}")
    print(f"    Email: {user.email}")
    print(f"    Activo: {user.is_active}")
    print(f"    Staff: {user.is_staff}")
    print(f"    Superusuario: {user.is_superuser}")
    print(f"    Tiene contraseña: {'Sí' if user.has_usable_password() else 'No'}")
    
    # Verificar perfil
    try:
        perfil = Perfil.objects.get(user=user)
        print(f"    Perfil: {perfil.nombre_completo}")
        print(f"    Rol: {perfil.rol}")
        print(f"    Activo: {perfil.activo}")
    except Perfil.DoesNotExist:
        print(f"    ⚠ PERFIL NO ENCONTRADO - Este usuario no puede iniciar sesión")
    except Exception as e:
        print(f"    ✗ Error: {e}")

print()
print("=" * 50)
print("VERIFICACIÓN DE INFORMACIÓN DE CLÍNICA")
print("=" * 50)
print()

try:
    from configuracion.models import InformacionClinica
    info = InformacionClinica.obtener()
    print(f"  Nombre: {info.nombre_clinica}")
    print(f"  Dirección: {info.direccion or '(vacía)'}")
    print(f"  Teléfono: {info.telefono or '(vacío)'}")
    print(f"  Email: {info.email or '(vacío)'}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()
print("=" * 50)







