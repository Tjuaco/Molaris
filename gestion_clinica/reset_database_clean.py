#!/usr/bin/env python
"""
Script para resetear completamente la base de datos y ejecutar migraciones limpias.

ADVERTENCIA: Este script eliminará TODOS los datos de la base de datos.
Solo usar si no hay datos importantes o en entorno de desarrollo.

Este script:
1. Elimina todas las tablas de la base de datos
2. Resetea el estado de las migraciones
3. Ejecuta todas las migraciones desde cero
4. Verifica que la estructura esté correcta
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

def confirmar_reset():
    """Solicita confirmación antes de resetear"""
    print("=" * 80)
    print("⚠️  ADVERTENCIA: RESET COMPLETO DE BASE DE DATOS")
    print("=" * 80)
    print()
    print("Este script realizará las siguientes acciones:")
    print("  1. Eliminará TODAS las tablas de la base de datos")
    print("  2. Eliminará TODOS los datos existentes")
    print("  3. Resetea el estado de las migraciones")
    print("  4. Ejecutará todas las migraciones desde cero")
    print()
    print("⚠️  ESTA ACCIÓN NO SE PUEDE DESHACER")
    print()
    
    respuesta1 = input("¿Está seguro de que desea continuar? (escriba 'SI' para confirmar): ")
    if respuesta1 != 'SI':
        print("Operación cancelada.")
        return False
    
    print()
    respuesta2 = input("¿Confirma que NO hay datos importantes que perder? (escriba 'CONFIRMO'): ")
    if respuesta2 != 'CONFIRMO':
        print("Operación cancelada.")
        return False
    
    return True

def eliminar_todas_las_tablas():
    """Elimina todas las tablas de la base de datos"""
    print("=" * 80)
    print("1. ELIMINANDO TODAS LAS TABLAS")
    print("=" * 80)
    print()
    
    with connection.cursor() as cursor:
        # Obtener todas las tablas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
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
        
        print()
        print(f"✅ {len(tablas)} tablas eliminadas")

def resetear_migraciones():
    """Resetea el estado de las migraciones"""
    print("=" * 80)
    print("2. RESETEANDO ESTADO DE MIGRACIONES")
    print("=" * 80)
    print()
    
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
    
    print()

def ejecutar_migraciones():
    """Ejecuta todas las migraciones desde cero"""
    print("=" * 80)
    print("3. EJECUTANDO MIGRACIONES DESDE CERO")
    print("=" * 80)
    print()
    
    try:
        # Ejecutar makemigrations para asegurar que todas las migraciones estén actualizadas
        print("  Ejecutando makemigrations...")
        call_command('makemigrations', verbosity=1)
        print("  ✅ makemigrations completado")
        print()
        
        # Ejecutar migrate
        print("  Ejecutando migrate...")
        call_command('migrate', verbosity=2, interactive=False)
        print("  ✅ migrate completado")
        print()
        
    except Exception as e:
        print(f"  ❌ Error al ejecutar migraciones: {e}")
        import traceback
        traceback.print_exc()
        raise

def verificar_estructura():
    """Verifica que la estructura esté correcta"""
    print("=" * 80)
    print("4. VERIFICANDO ESTRUCTURA")
    print("=" * 80)
    print()
    
    from django.apps import apps
    
    # Verificar tablas críticas
    tablas_criticas = [
        'pacientes_cliente',
        'citas_cita',
        'personal_perfil',
        'auth_user',
        'citas_tiposervicio',
    ]
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE';
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
    
    print()
    
    # Verificar que NO existe citas_cliente
    if 'citas_cliente' in tablas_existentes:
        print("  ⚠️  ADVERTENCIA: La tabla citas_cliente existe (no debería)")
        todas_ok = False
    else:
        print("  ✅ La tabla citas_cliente NO existe (correcto)")
    
    print()
    
    # Verificar ForeignKeys críticas
    print("  Verificando ForeignKeys críticas:")
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
    
    print()
    
    if todas_ok:
        print("  ✅ Todas las verificaciones pasaron correctamente")
    else:
        print("  ⚠️  Se encontraron algunos problemas")
    
    return todas_ok

def crear_superusuario():
    """Pregunta si desea crear un superusuario"""
    print("=" * 80)
    print("5. CREAR SUPERUSUARIO")
    print("=" * 80)
    print()
    
    respuesta = input("¿Desea crear un superusuario ahora? (s/n): ")
    if respuesta.lower() == 's':
        try:
            call_command('createsuperuser', interactive=True)
            print("  ✅ Superusuario creado")
        except Exception as e:
            print(f"  ⚠️  Error al crear superusuario: {e}")
    else:
        print("  ℹ️  Puede crear un superusuario más tarde con: python manage.py createsuperuser")
    print()

def main():
    """Función principal"""
    print()
    print("=" * 80)
    print("RESET COMPLETO DE BASE DE DATOS")
    print("=" * 80)
    print()
    
    # Confirmar
    if not confirmar_reset():
        return
    
    print()
    print("Iniciando proceso de reset...")
    print()
    
    try:
        # 1. Eliminar todas las tablas
        eliminar_todas_las_tablas()
        
        # 2. Resetear migraciones
        resetear_migraciones()
        
        # 3. Ejecutar migraciones
        ejecutar_migraciones()
        
        # 4. Verificar estructura
        estructura_ok = verificar_estructura()
        
        # 5. Crear superusuario
        crear_superusuario()
        
        print()
        print("=" * 80)
        print("RESET COMPLETADO")
        print("=" * 80)
        print()
        
        if estructura_ok:
            print("✅ La base de datos ha sido reseteada correctamente")
            print("✅ Todas las verificaciones pasaron")
            print()
            print("PRÓXIMOS PASOS:")
            print("1. Verificar que cliente_web también funcione correctamente")
            print("2. Ejecutar: python verificar_estructura_bd.py para verificación final")
            print("3. Crear datos de prueba si es necesario")
        else:
            print("⚠️  El reset se completó pero se encontraron algunos problemas")
            print("   Revise los mensajes anteriores y corrija si es necesario")
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR DURANTE EL RESET")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("La base de datos puede estar en un estado inconsistente.")
        print("Revise los errores y corrija manualmente si es necesario.")
        sys.exit(1)

if __name__ == '__main__':
    main()


