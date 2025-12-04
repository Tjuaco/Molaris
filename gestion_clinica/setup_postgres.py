"""
Script para configurar PostgreSQL y aplicar migraciones
"""
import os

print("=" * 60)
print("  CONFIGURACIÓN DE POSTGRESQL")
print("=" * 60)
print()

# Solicitar información
print("Ingresa la información de tu base de datos PostgreSQL:")
print()

db_name = input("Nombre de la base de datos [clinica_db]: ").strip() or "clinica_db"
db_user = input("Usuario [postgres]: ").strip() or "postgres"
db_password = input("Contraseña: ").strip()
db_host = input("Host [localhost]: ").strip() or "localhost"
db_port = input("Puerto [5432]: ").strip() or "5432"

# Crear archivo .env
env_content = f"""# Configuración de Base de Datos
DB_ENGINE=postgresql
DB_NAME={db_name}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_HOST={db_host}
DB_PORT={db_port}

# Configuración de Twilio
TWILIO_ACCOUNT_SID=AC7319b0ea75ab89067722861358686b39
TWILIO_AUTH_TOKEN=cfa7d326a809fd880175c86e59f6a228
TWILIO_PHONE_NUMBER=+15005550006
TWILIO_FROM_SMS=+15005550006
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_FROM_WHATSAPP=whatsapp:+14155238886
TWILIO_WHATSAPP_BUSINESS_NUMBER=whatsapp:+14155238886

# Información de la Clínica
CLINIC_NAME=Clínica Dental San Felipe
CLINIC_ADDRESS=Av Manuel Rodriguez #1625, Victoria
CLINIC_PHONE=+56920589344
CLINIC_EMAIL=contacto@clinicadentalsanfelipe.cl
CLINIC_WEBSITE=
CLINIC_MAP_URL=https://maps.app.goo.gl/be6QjzVein4JcYBn8

# URL del sitio
SITE_URL=http://localhost:8001

# Django Settings
SECRET_KEY=django-insecure-change-this-in-production-28vh&5z1ku08x3e@gwocph(vtcc=k3shq(!6=4@-v1iuw+c)5t
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
"""

try:
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    print()
    print("✓ Archivo .env creado correctamente")
except Exception as e:
    print(f"✗ Error al crear .env: {e}")
    exit(1)

print()
print("=" * 60)
print("  APLICANDO MIGRACIONES")
print("=" * 60)
print()

# Aplicar migraciones
import subprocess
import sys

result = subprocess.run([sys.executable, 'manage.py', 'migrate'], cwd=os.getcwd())

if result.returncode == 0:
    print()
    print("✓ Migraciones aplicadas correctamente")
    print()
    print("=" * 60)
    print("  CREAR SUPERUSUARIO")
    print("=" * 60)
    print()
    print("Ahora ejecuta:")
    print("  python manage.py createsuperuser")
    print()
else:
    print()
    print("✗ Error al aplicar migraciones")
    print("Verifica que:")
    print("  - La base de datos '{}' exista en PostgreSQL".format(db_name))
    print("  - Las credenciales sean correctas")
    print("  - PostgreSQL esté corriendo")







