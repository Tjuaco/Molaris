"""
Script para configurar PostgreSQL y migrar la base de datos
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.core.management import call_command
from django.db import connection
from django.conf import settings

print("=" * 60)
print("  CONFIGURACIÓN DE POSTGRESQL")
print("=" * 60)
print()

# Verificar configuración actual
print("1. Verificando configuración actual...")
db_config = settings.DATABASES['default']
print(f"   Motor: {db_config['ENGINE']}")
print(f"   Base de datos: {db_config.get('NAME', 'N/A')}")

if 'sqlite3' in db_config['ENGINE']:
    print()
    print("   ⚠ El sistema está usando SQLite, no PostgreSQL")
    print()
    print("   Para usar PostgreSQL, necesitas:")
    print("   1. Crear la base de datos en PostgreSQL")
    print("   2. Configurar variables de entorno")
    print()
    print("   Pasos:")
    print()
    print("   A. Crear base de datos en pgAdmin:")
    print("      - Abre pgAdmin")
    print("      - Click derecho en 'Databases' > 'Create' > 'Database'")
    print("      - Nombre: clinica_db")
    print("      - Owner: postgres (o tu usuario)")
    print("      - Click 'Save'")
    print()
    print("   B. Configurar variables de entorno:")
    print("      En PowerShell ejecuta:")
    print()
    print("      $env:DB_ENGINE='postgresql'")
    print("      $env:DB_NAME='clinica_db'")
    print("      $env:DB_USER='postgres'")
    print("      $env:DB_PASSWORD='tu_contraseña'")
    print("      $env:DB_HOST='localhost'")
    print("      $env:DB_PORT='5432'")
    print()
    print("   C. Aplicar migraciones:")
    print("      python manage.py migrate")
    print()
else:
    print()
    print("   ✓ El sistema está configurado para PostgreSQL")
    print()
    # Intentar conectar
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"   ✓ Conexión exitosa a PostgreSQL")
            print(f"   Versión: {version[:50]}...")
    except Exception as e:
        print(f"   ✗ Error de conexión: {e}")
        print()
        print("   Verifica:")
        print("   - Que PostgreSQL esté corriendo")
        print("   - Que la base de datos 'clinica_db' exista")
        print("   - Que las credenciales sean correctas")

print()
print("=" * 60)







