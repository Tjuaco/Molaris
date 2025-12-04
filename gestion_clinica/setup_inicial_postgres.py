"""
Script para configurar el sistema inicial en PostgreSQL
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.contrib.auth.models import User
from personal.models import Perfil
from configuracion.models import InformacionClinica

print("=" * 60)
print("  CONFIGURACIÓN INICIAL DEL SISTEMA")
print("=" * 60)
print()

# 1. Crear superusuario
print("1. Creando superusuario...")
try:
    # Eliminar usuario si existe
    User.objects.filter(username='admin').delete()
    
    # Crear nuevo superusuario
    user = User.objects.create_superuser(
        username='admin',
        email='admin@clinica.com',
        password='admin123'
    )
    print(f"   ✓ Superusuario creado:")
    print(f"     Usuario: admin")
    print(f"     Contraseña: admin123")
except Exception as e:
    print(f"   ✗ Error: {e}")

print()

# 2. Crear perfil
print("2. Creando perfil administrativo...")
try:
    user = User.objects.get(username='admin')
    perfil, created = Perfil.objects.get_or_create(
        user=user,
        defaults={
            'nombre_completo': 'Administrador',
            'rol': 'administrativo',
            'activo': True,
        }
    )
    if created:
        print(f"   ✓ Perfil creado: {perfil.nombre_completo}")
    else:
        print(f"   ✓ Perfil ya existía: {perfil.nombre_completo}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print()

# 3. Configurar información de la clínica
print("3. Configurando información de la clínica...")
try:
    info = InformacionClinica.obtener()
    info.nombre_clinica = "Clínica Dental San Felipe"
    info.direccion = "Av Manuel Rodriguez #1625, Victoria"
    info.telefono = "+56920589344"
    info.email = "contacto@clinicadentalsanfelipe.cl"
    info.horario_atencion = "Lunes a Viernes: 9:00 - 18:00\nSábados: 9:00 - 13:00"
    info.save()
    print(f"   ✓ Información configurada:")
    print(f"     - Nombre: {info.nombre_clinica}")
    print(f"     - Dirección: {info.direccion}")
    print(f"     - Teléfono: {info.telefono}")
    print(f"     - Email: {info.email}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print()
print("=" * 60)
print("  ✓ CONFIGURACIÓN COMPLETADA")
print("=" * 60)
print()
print("Credenciales de acceso:")
print("  Usuario: admin")
print("  Contraseña: admin123")
print()
print("El sistema está listo para usar con PostgreSQL!")
print()







