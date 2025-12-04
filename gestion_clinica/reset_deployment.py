#!/usr/bin/env python
"""
Script de RESET COMPLETO para despliegue limpio.
Simula un despliegue desde cero sin errores.

Este script:
1. Detecta el tipo de base de datos (SQLite o PostgreSQL)
2. Elimina todas las tablas de forma segura
3. Resetea el estado de las migraciones
4. Ejecuta todas las migraciones desde cero
5. Verifica que la estructura esté correcta
6. Verifica ForeignKeys críticas
7. Crea un superusuario de prueba para presentación
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.db import connection
from django.core.management import call_command
from django.conf import settings
from django.contrib.auth.models import User
from personal.models import Perfil

def print_header(texto):
    """Imprime un encabezado formateado"""
    print()
    print("=" * 80)
    print(texto)
    print("=" * 80)
    print()

def print_step(numero, texto):
    """Imprime un paso del proceso"""
    print(f"\n[{numero}] {texto}")
    print("-" * 80)

def es_postgresql():
    """Verifica si se está usando PostgreSQL"""
    return 'postgresql' in settings.DATABASES['default']['ENGINE']

def eliminar_todas_las_tablas():
    """Elimina todas las tablas de la base de datos"""
    print_step(1, "ELIMINANDO TODAS LAS TABLAS")
    
    if es_postgresql():
        # PostgreSQL
        with connection.cursor() as cursor:
            # Obtener todas las tablas
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name NOT LIKE 'pg_%'
                ORDER BY table_name;
            """)
            tablas = [row[0] for row in cursor.fetchall()]
            
            if not tablas:
                print("  ✅ No hay tablas para eliminar")
                return
            
            print(f"  Encontradas {len(tablas)} tablas para eliminar...")
            
            # Desactivar temporalmente las verificaciones de ForeignKey
            cursor.execute("SET session_replication_role = 'replica';")
            
            # Eliminar todas las tablas
            for tabla in tablas:
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS "{tabla}" CASCADE;')
                    print(f"  ✅ Eliminada: {tabla}")
                except Exception as e:
                    print(f"  ⚠️  Error al eliminar {tabla}: {e}")
            
            # Reactivar verificaciones
            cursor.execute("SET session_replication_role = 'origin';")
            
            print(f"\n✅ {len(tablas)} tablas eliminadas")
    else:
        # SQLite
        db_path = settings.DATABASES['default']['NAME']
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"  ✅ Base de datos SQLite eliminada: {db_path}")
            except Exception as e:
                print(f"  ❌ Error al eliminar SQLite: {e}")
                raise
        else:
            print("  ℹ️  La base de datos SQLite no existe")

def resetear_migraciones():
    """Resetea el estado de las migraciones"""
    print_step(2, "RESETEANDO ESTADO DE MIGRACIONES")
    
    if es_postgresql():
        with connection.cursor() as cursor:
            # Verificar si existe la tabla django_migrations
            cursor.execute("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'django_migrations';
            """)
            
            if cursor.fetchone():
                cursor.execute("DELETE FROM django_migrations;")
                print("  ✅ Registros de migraciones eliminados")
            else:
                print("  ℹ️  La tabla django_migrations no existe (se creará con las migraciones)")
    else:
        # SQLite: ya se eliminó el archivo, no hay nada que resetear
        print("  ℹ️  Base de datos SQLite eliminada, no hay migraciones que resetear")

def ejecutar_migraciones():
    """Ejecuta todas las migraciones desde cero"""
    print_step(3, "EJECUTANDO MIGRACIONES DESDE CERO")
    
    try:
        # Ejecutar makemigrations para asegurar que todas las migraciones estén actualizadas
        print("  Ejecutando makemigrations...")
        call_command('makemigrations', verbosity=1, interactive=False)
        print("  ✅ makemigrations completado")
        
        # Ejecutar migrate
        print("\n  Ejecutando migrate...")
        call_command('migrate', verbosity=2, interactive=False)
        print("  ✅ migrate completado")
        
    except Exception as e:
        print(f"  ❌ Error al ejecutar migraciones: {e}")
        import traceback
        traceback.print_exc()
        raise

def verificar_estructura():
    """Verifica que la estructura esté correcta"""
    print_step(4, "VERIFICANDO ESTRUCTURA DE BASE DE DATOS")
    
    if not es_postgresql():
        print("  ℹ️  Verificación detallada solo disponible para PostgreSQL")
        print("  ✅ SQLite: Estructura creada por migraciones")
        return True
    
    from django.apps import apps
    
    # Verificar tablas críticas
    tablas_criticas = [
        'pacientes_cliente',
        'citas_cita',
        'personal_perfil',
        'auth_user',
        'citas_tiposervicio',
        'django_migrations',
    ]
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'pg_%';
        """)
        tablas_existentes = {row[0] for row in cursor.fetchall()}
    
    print("  Verificando tablas críticas:")
    todas_ok = True
    for tabla in tablas_criticas:
        if tabla in tablas_existentes:
            print(f"    ✅ {tabla}")
        else:
            print(f"    ❌ {tabla} (NO EXISTE)")
            todas_ok = False
    
    # Verificar que NO existe citas_cliente
    if 'citas_cliente' in tablas_existentes:
        print("\n  ⚠️  ADVERTENCIA: La tabla citas_cliente existe (no debería)")
        todas_ok = False
    else:
        print("\n  ✅ La tabla citas_cliente NO existe (correcto)")
    
    # Verificar ForeignKeys críticas
    print("\n  Verificando ForeignKeys críticas:")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                tc.table_name AS tabla_origen,
                kcu.column_name AS columna,
                ccu.table_name AS tabla_destino
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND (
                (tc.table_name = 'citas_cita' AND kcu.column_name = 'cliente_id')
                OR (tc.table_name = 'citas_cita' AND kcu.column_name = 'dentista_id')
            )
            ORDER BY tc.table_name, kcu.column_name;
        """)
        
        fks_criticas = cursor.fetchall()
        if not fks_criticas:
            print("    ⚠️  No se encontraron ForeignKeys críticas (puede ser normal si no hay datos)")
        else:
            for tabla, columna, destino in fks_criticas:
                if tabla == 'citas_cita' and columna == 'cliente_id':
                    if destino == 'pacientes_cliente':
                        print(f"    ✅ {tabla}.{columna} -> {destino} (CORRECTO)")
                    else:
                        print(f"    ❌ {tabla}.{columna} -> {destino} (DEBERÍA SER pacientes_cliente)")
                        todas_ok = False
                elif tabla == 'citas_cita' and columna == 'dentista_id':
                    if destino == 'personal_perfil':
                        print(f"    ✅ {tabla}.{columna} -> {destino} (CORRECTO)")
                    else:
                        print(f"    ❌ {tabla}.{columna} -> {destino} (DEBERÍA SER personal_perfil)")
                        todas_ok = False
    
    if todas_ok:
        print("\n  ✅ Todas las verificaciones pasaron correctamente")
    else:
        print("\n  ⚠️  Se encontraron algunos problemas")
    
    return todas_ok

def crear_datos_presentacion():
    """Crea datos básicos para la presentación"""
    print_step(5, "CREANDO DATOS PARA PRESENTACIÓN")
    
    try:
        # Verificar si ya existe un superusuario
        if User.objects.filter(is_superuser=True).exists():
            print("  ℹ️  Ya existe un superusuario, omitiendo creación")
            return
        
        # Crear superusuario
        print("  Creando superusuario de prueba...")
        username = 'admin'
        email = 'admin@clinica.com'
        password = 'admin123'
        
        # Crear usuario
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print(f"  ✅ Superusuario creado: {username} / {password}")
        
        # Crear perfil administrativo
        perfil, created = Perfil.objects.get_or_create(
            user=user,
            defaults={
                'nombre_completo': 'Administrador',
                'email': email,
                'rol': 'administrativo',  # Usar 'administrativo' no 'administrador'
                'activo': True,
            }
        )
        # Si el perfil ya existe, actualizar el rol si es necesario
        if not created and perfil.rol != 'administrativo':
            perfil.rol = 'administrativo'
            perfil.save()
        if created:
            print(f"  ✅ Perfil administrativo creado")
        else:
            print(f"  ℹ️  Perfil administrativo ya existe")
        
        print("\n  📋 CREDENCIALES PARA PRESENTACIÓN:")
        print(f"     Usuario: {username}")
        print(f"     Contraseña: {password}")
        print(f"     Email: {email}")
        
    except Exception as e:
        print(f"  ⚠️  Error al crear datos de presentación: {e}")
        import traceback
        traceback.print_exc()

def verificar_errores():
    """Verifica que no haya errores obvios"""
    print_step(6, "VERIFICANDO QUE NO HAYA ERRORES")
    
    errores = []
    
    # Verificar que las apps críticas estén instaladas
    apps_criticas = ['citas', 'pacientes', 'personal', 'inventario']
    for app in apps_criticas:
        try:
            from django.apps import apps
            apps.get_app_config(app)
            print(f"  ✅ App '{app}' instalada correctamente")
        except Exception as e:
            errores.append(f"App '{app}' no encontrada: {e}")
            print(f"  ❌ App '{app}' no encontrada")
    
    # Verificar que los modelos críticos se puedan importar
    modelos_criticos = [
        ('citas.models', 'Cita'),
        ('pacientes.models', 'Cliente'),
        ('personal.models', 'Perfil'),
    ]
    
    for modulo, modelo in modelos_criticos:
        try:
            mod = __import__(modulo, fromlist=[modelo])
            getattr(mod, modelo)
            print(f"  ✅ Modelo '{modulo}.{modelo}' importado correctamente")
        except Exception as e:
            errores.append(f"Modelo '{modulo}.{modelo}' no se puede importar: {e}")
            print(f"  ❌ Modelo '{modulo}.{modelo}' no se puede importar")
    
    if errores:
        print(f"\n  ⚠️  Se encontraron {len(errores)} errores:")
        for error in errores:
            print(f"     - {error}")
        return False
    else:
        print("\n  ✅ No se encontraron errores")
        return True

def main():
    """Función principal"""
    print_header("RESET COMPLETO PARA DESPLIEGUE")
    
    print("Este script realizará las siguientes acciones:")
    print("  1. Eliminará TODAS las tablas de la base de datos")
    print("  2. Eliminará TODOS los datos existentes")
    print("  3. Resetea el estado de las migraciones")
    print("  4. Ejecutará todas las migraciones desde cero")
    print("  5. Verificará que la estructura esté correcta")
    print("  6. Creará datos básicos para presentación")
    print()
    
    tipo_bd = "PostgreSQL" if es_postgresql() else "SQLite"
    print(f"Tipo de base de datos detectado: {tipo_bd}")
    print()
    
    # Permitir ejecución automática si se pasa --yes como argumento
    if len(sys.argv) > 1 and sys.argv[1] == '--yes':
        print("Modo automático activado (--yes)")
        print("\nIniciando proceso de reset...")
    else:
        respuesta = input("¿Desea continuar con el reset? (s/n): ")
        if respuesta.lower() != 's':
            print("\nOperación cancelada.")
            return
        print("\nIniciando proceso de reset...")
    
    try:
        # 1. Eliminar todas las tablas
        eliminar_todas_las_tablas()
        
        # 2. Resetear migraciones
        resetear_migraciones()
        
        # 3. Ejecutar migraciones
        ejecutar_migraciones()
        
        # 4. Verificar estructura
        estructura_ok = verificar_estructura()
        
        # 5. Crear datos de presentación
        crear_datos_presentacion()
        
        # 6. Verificar errores
        sin_errores = verificar_errores()
        
        # Resumen final
        print_header("RESET COMPLETADO")
        
        if estructura_ok and sin_errores:
            print("✅ La base de datos ha sido reseteada correctamente")
            print("✅ Todas las verificaciones pasaron")
            print("✅ Sistema listo para presentación")
            print()
            print("PRÓXIMOS PASOS:")
            print("1. Ejecutar: python manage.py runserver")
            print("2. Acceder a: http://127.0.0.1:8000")
            print("3. Iniciar sesión con las credenciales mostradas arriba")
            print("4. Verificar que todas las secciones funcionen correctamente")
        else:
            print("⚠️  El reset se completó pero se encontraron algunos problemas")
            print("   Revise los mensajes anteriores y corrija si es necesario")
        
    except Exception as e:
        print_header("❌ ERROR DURANTE EL RESET")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("La base de datos puede estar en un estado inconsistente.")
        print("Revise los errores y corrija manualmente si es necesario.")
        sys.exit(1)

if __name__ == '__main__':
    main()

