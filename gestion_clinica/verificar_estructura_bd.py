#!/usr/bin/env python
"""
Script para verificar y corregir la estructura de la base de datos compartida
entre gestion_clinica y cliente_web.

Este script:
1. Verifica que todas las tablas existan
2. Verifica que las ForeignKeys apunten a las tablas correctas
3. Identifica inconsistencias entre modelos y tablas reales
4. Genera un reporte completo
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.db import connection
from django.apps import apps
from collections import defaultdict

def obtener_todas_las_tablas():
    """Obtiene todas las tablas de la base de datos"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        return [row[0] for row in cursor.fetchall()]

def obtener_foreign_keys():
    """Obtiene todas las ForeignKeys de la base de datos"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                tc.table_name AS tabla_origen,
                kcu.column_name AS columna,
                ccu.table_name AS tabla_destino,
                ccu.column_name AS columna_destino,
                tc.constraint_name AS constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name;
        """)
        return cursor.fetchall()

def obtener_modelos_y_tablas():
    """Obtiene todos los modelos y sus tablas correspondientes"""
    modelos_info = {}
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            db_table = model._meta.db_table
            modelos_info[model.__name__] = {
                'app': app_config.name,
                'model': model.__name__,
                'db_table': db_table,
                'full_path': f"{app_config.name}.{model.__name__}"
            }
    return modelos_info

def analizar_estructura():
    """Analiza la estructura completa de la base de datos"""
    print("=" * 80)
    print("ANÁLISIS DE ESTRUCTURA DE BASE DE DATOS COMPARTIDA")
    print("=" * 80)
    print()
    
    # 1. Obtener todas las tablas
    print("1. TABLAS EN LA BASE DE DATOS:")
    print("-" * 80)
    tablas_bd = obtener_todas_las_tablas()
    print(f"Total de tablas: {len(tablas_bd)}")
    for tabla in sorted(tablas_bd):
        print(f"  - {tabla}")
    print()
    
    # 2. Obtener modelos y sus tablas
    print("2. MODELOS Y SUS TABLAS:")
    print("-" * 80)
    modelos_info = obtener_modelos_y_tablas()
    tablas_modelos = set()
    for model_name, info in sorted(modelos_info.items()):
        tablas_modelos.add(info['db_table'])
        print(f"  {info['full_path']:50} -> {info['db_table']}")
    print()
    
    # 3. Verificar tablas sin modelo
    print("3. TABLAS SIN MODELO (posibles tablas huérfanas):")
    print("-" * 80)
    tablas_sin_modelo = set(tablas_bd) - tablas_modelos
    if tablas_sin_modelo:
        for tabla in sorted(tablas_sin_modelo):
            print(f"  ⚠️  {tabla}")
    else:
        print("  ✅ Todas las tablas tienen modelos asociados")
    print()
    
    # 4. Verificar modelos sin tabla
    print("4. MODELOS CUYA TABLA NO EXISTE:")
    print("-" * 80)
    modelos_sin_tabla = []
    for model_name, info in sorted(modelos_info.items()):
        if info['db_table'] not in tablas_bd:
            modelos_sin_tabla.append((model_name, info))
            print(f"  ❌ {info['full_path']:50} -> {info['db_table']} (NO EXISTE)")
    if not modelos_sin_tabla:
        print("  ✅ Todos los modelos tienen tablas asociadas")
    print()
    
    # 5. Analizar ForeignKeys
    print("5. FOREIGN KEYS EN LA BASE DE DATOS:")
    print("-" * 80)
    fks = obtener_foreign_keys()
    fks_por_tabla = defaultdict(list)
    for fk in fks:
        tabla_origen, columna, tabla_destino, columna_destino, constraint_name = fk
        fks_por_tabla[tabla_origen].append({
            'columna': columna,
            'tabla_destino': tabla_destino,
            'columna_destino': columna_destino,
            'constraint_name': constraint_name
        })
        print(f"  {tabla_origen}.{columna} -> {tabla_destino}.{columna_destino} ({constraint_name})")
    print()
    
    # 6. Verificar ForeignKeys problemáticas
    print("6. VERIFICACIÓN DE FOREIGN KEYS CRÍTICAS:")
    print("-" * 80)
    problemas = []
    
    # Verificar citas_cita.cliente_id
    for fk in fks:
        tabla_origen, columna, tabla_destino, columna_destino, constraint_name = fk
        if tabla_origen == 'citas_cita' and columna == 'cliente_id':
            if tabla_destino != 'pacientes_cliente':
                problemas.append({
                    'tipo': 'FK_INCORRECTA',
                    'tabla': tabla_origen,
                    'columna': columna,
                    'actual': tabla_destino,
                    'esperado': 'pacientes_cliente',
                    'constraint': constraint_name
                })
                print(f"  ❌ {tabla_origen}.{columna} apunta a {tabla_destino} (debería ser pacientes_cliente)")
            else:
                print(f"  ✅ {tabla_origen}.{columna} apunta correctamente a {tabla_destino}")
    
    # Verificar otras ForeignKeys críticas
    fks_criticas = [
        ('citas_cita', 'dentista_id', 'personal_perfil'),
        ('citas_cita', 'creada_por_id', 'personal_perfil'),
    ]
    
    for tabla, columna, tabla_esperada in fks_criticas:
        encontrada = False
        for fk in fks:
            if fk[0] == tabla and fk[1] == columna:
                encontrada = True
                if fk[2] != tabla_esperada:
                    problemas.append({
                        'tipo': 'FK_INCORRECTA',
                        'tabla': tabla,
                        'columna': columna,
                        'actual': fk[2],
                        'esperado': tabla_esperada,
                        'constraint': fk[4]
                    })
                    print(f"  ❌ {tabla}.{columna} apunta a {fk[2]} (debería ser {tabla_esperada})")
                else:
                    print(f"  ✅ {tabla}.{columna} apunta correctamente a {fk[2]}")
                break
        if not encontrada:
            print(f"  ⚠️  {tabla}.{columna} no tiene ForeignKey definida")
    
    print()
    
    # 7. Verificar inconsistencias en nombres de tablas
    print("7. INCONSISTENCIAS EN NOMBRES DE TABLAS:")
    print("-" * 80)
    
    # Verificar si existe citas_cliente cuando debería ser pacientes_cliente
    if 'citas_cliente' in tablas_bd and 'pacientes_cliente' in tablas_bd:
        print("  ⚠️  AMBAS tablas existen: citas_cliente Y pacientes_cliente")
        print("     Esto puede causar confusión. Verificar cuál se está usando.")
    elif 'citas_cliente' in tablas_bd:
        print("  ⚠️  Existe citas_cliente pero NO pacientes_cliente")
        print("     El modelo Cliente debería usar pacientes_cliente")
    elif 'pacientes_cliente' in tablas_bd:
        print("  ✅ Solo existe pacientes_cliente (correcto)")
    
    # Verificar modelo ClienteDocumento en cliente_web
    if 'citas_cliente' in tablas_bd:
        print("  ⚠️  cliente_web usa ClienteDocumento con db_table='citas_cliente'")
        print("     pero gestion_clinica usa Cliente con tabla pacientes_cliente")
        print("     ESTO ES UNA INCONSISTENCIA CRÍTICA")
    
    print()
    
    # 8. Resumen de problemas
    print("8. RESUMEN DE PROBLEMAS:")
    print("-" * 80)
    if problemas:
        print(f"  Se encontraron {len(problemas)} problema(s):")
        for i, problema in enumerate(problemas, 1):
            print(f"  {i}. {problema['tipo']}: {problema['tabla']}.{problema['columna']}")
            print(f"     Actual: {problema['actual']}")
            print(f"     Esperado: {problema['esperado']}")
            print(f"     Constraint: {problema['constraint']}")
    else:
        print("  ✅ No se encontraron problemas críticos")
    print()
    
    # 9. Recomendaciones
    print("9. RECOMENDACIONES:")
    print("-" * 80)
    if 'citas_cliente' in tablas_bd and 'pacientes_cliente' in tablas_bd:
        print("  - Eliminar la tabla citas_cliente si no se está usando")
        print("  - Asegurar que todas las ForeignKeys apunten a pacientes_cliente")
    if problemas:
        print("  - Corregir las ForeignKeys identificadas")
        print("  - Ejecutar las migraciones necesarias")
    print("  - Verificar que cliente_web use pacientes_cliente, no citas_cliente")
    print()
    
    print("=" * 80)
    return problemas

if __name__ == '__main__':
    try:
        problemas = analizar_estructura()
        if problemas:
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error al analizar: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


