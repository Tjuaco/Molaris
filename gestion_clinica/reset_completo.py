"""
Script para resetear completamente la base de datos y dejarla lista para pruebas
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User
from personal.models import Perfil
from configuracion.models import InformacionClinica

print("=" * 60)
print("  RESET COMPLETO DEL SISTEMA")
print("=" * 60)
print()

# 1. Eliminar base de datos
print("1. Eliminando base de datos antigua...")
db_path = 'db.sqlite3'
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"   ✓ Base de datos eliminada: {db_path}")
    except Exception as e:
        print(f"   ✗ Error al eliminar: {e}")
        print("   ⚠ Asegúrate de que el servidor de Django esté cerrado")
        sys.exit(1)
else:
    print(f"   ℹ No había base de datos que eliminar")

print()

# 2. Aplicar migraciones
print("2. Aplicando migraciones...")
try:
    # Aplicar migraciones básicas primero
    print("   Aplicando migraciones básicas...")
    call_command('migrate', 'contenttypes', verbosity=0)
    call_command('migrate', 'auth', verbosity=0)
    call_command('migrate', 'admin', verbosity=0)
    call_command('migrate', 'sessions', verbosity=0)
    
    # Aplicar todas las demás migraciones
    print("   Aplicando migraciones de aplicaciones...")
    call_command('migrate', verbosity=0)
    
    # Si hay errores con migraciones específicas, marcarlas como fake
    problematic_migrations = [
        ('citas', '0009_recreate_cita_table'),
        ('citas', '0011_fix_postgresql_table'),
        ('citas', '0013_fix_postgresql_cita_table'),
        ('citas', '0014_create_cita_table_final'),
        ('citas', '0034_horariodentista_remove_egresomanual_creado_por_and_more'),
    ]
    
    for app, migration in problematic_migrations:
        try:
            call_command('migrate', app, migration, fake=True, verbosity=0)
        except:
            pass
    
    # Aplicar migraciones restantes
    call_command('migrate', verbosity=0)
    print("   ✓ Migraciones aplicadas correctamente")
except Exception as e:
    print(f"   ⚠ Advertencia en migraciones: {e}")
    print("   Continuando de todas formas...")

print()

# 3. Crear superusuario
print("3. Creando superusuario...")
try:
    # Eliminar usuario si existe
    User.objects.filter(username='admin').delete()
    
    # Crear nuevo superusuario
    user = User.objects.create_superuser(
        username='admin',
        email='admin@clinica.com',
        password='admin123'  # Contraseña simple para pruebas
    )
    print(f"   ✓ Superusuario creado:")
    print(f"     Usuario: admin")
    print(f"     Contraseña: admin123")
    print(f"     Email: admin@clinica.com")
except Exception as e:
    print(f"   ✗ Error al crear superusuario: {e}")

print()

# 4. Crear perfil para el usuario
print("4. Creando perfil administrativo...")
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
    print(f"   ✗ Error al crear perfil: {e}")

print()

# 5. Configurar información de la clínica
print("5. Configurando información de la clínica...")
try:
    info = InformacionClinica.obtener()
    info.nombre_clinica = "Clínica Dental San Felipe"
    info.direccion = "Av Manuel Rodriguez #1625, Victoria"
    info.telefono = "+56920589344"  # Tu número para pruebas
    info.email = "contacto@clinicadentalsanfelipe.cl"
    info.horario_atencion = "Lunes a Viernes: 9:00 - 18:00\nSábados: 9:00 - 13:00"
    info.save()
    print(f"   ✓ Información de clínica configurada:")
    print(f"     - Nombre: {info.nombre_clinica}")
    print(f"     - Dirección: {info.direccion}")
    print(f"     - Teléfono: {info.telefono}")
    print(f"     - Email: {info.email}")
except Exception as e:
    print(f"   ✗ Error al configurar clínica: {e}")

print()
print("=" * 60)
print("  ✓ RESET COMPLETO FINALIZADO")
print("=" * 60)
print()
print("El sistema está listo para usar. Credenciales:")
print()
print("  URL: http://127.0.0.1:8000/trabajadores/login/")
print("  Usuario: admin")
print("  Contraseña: admin123")
print()
print("Para probar la mensajería:")
print("  1. Inicia sesión")
print("  2. Crea un cliente con teléfono: 20589344")
print("  3. Asigna una cita a ese cliente")
print("  4. El sistema enviará WhatsApp y SMS automáticamente")
print()
print("⚠ IMPORTANTE: Verifica tu número +56920589344 en Twilio")
print("   Dashboard: https://console.twilio.com/us1/develop/phone-numbers/manage/verified")
print()

