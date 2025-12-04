#!/usr/bin/env python
"""
Script para corregir la estructura de la base de datos compartida.

Este script:
1. Verifica y migra datos de citas_cliente a pacientes_cliente
2. Corrige todas las ForeignKeys para que apunten a pacientes_cliente
3. Actualiza referencias en cliente_web
4. Elimina la tabla citas_cliente si ya no se usa
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.db import connection, transaction
from pacientes.models import Cliente

def verificar_datos_tablas():
    """Verifica qué datos hay en cada tabla de cliente"""
    with connection.cursor() as cursor:
        # Verificar citas_cliente
        cursor.execute("SELECT COUNT(*) FROM citas_cliente;")
        count_citas_cliente = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, nombre_completo, email FROM citas_cliente LIMIT 5;")
        datos_citas_cliente = cursor.fetchall()
        
        # Verificar pacientes_cliente
        count_pacientes_cliente = Cliente.objects.count()
        datos_pacientes_cliente = list(Cliente.objects.values_list('id', 'nombre_completo', 'email')[:5])
        
        return {
            'citas_cliente': {
                'count': count_citas_cliente,
                'datos': datos_citas_cliente
            },
            'pacientes_cliente': {
                'count': count_pacientes_cliente,
                'datos': datos_pacientes_cliente
            }
        }

def migrar_datos_citas_cliente_a_pacientes_cliente():
    """Migra datos de citas_cliente a pacientes_cliente si es necesario"""
    print("=" * 80)
    print("MIGRACIÓN DE DATOS DE citas_cliente A pacientes_cliente")
    print("=" * 80)
    print()
    
    with connection.cursor() as cursor:
        # Verificar si hay datos en citas_cliente que no estén en pacientes_cliente
        cursor.execute("""
            SELECT c.id, c.nombre_completo, c.email, c.telefono
            FROM citas_cliente c
            WHERE NOT EXISTS (
                SELECT 1 FROM pacientes_cliente p 
                WHERE p.email = c.email OR p.id = c.id
            );
        """)
        datos_a_migrar = cursor.fetchall()
        
        if not datos_a_migrar:
            print("✅ No hay datos en citas_cliente que necesiten migración")
            return 0
        
        print(f"⚠️  Se encontraron {len(datos_a_migrar)} registros en citas_cliente que no están en pacientes_cliente")
        print("   Estos registros se migrarán automáticamente...")
        print()
        
        migrados = 0
        for registro in datos_a_migrar:
            cliente_id, nombre, email, telefono = registro
            try:
                # Intentar crear el cliente en pacientes_cliente
                Cliente.objects.get_or_create(
                    email=email,
                    defaults={
                        'nombre_completo': nombre or 'Sin nombre',
                        'telefono': telefono or '+56900000000',
                        'activo': True
                    }
                )
                migrados += 1
                print(f"  ✅ Migrado: {nombre} ({email})")
            except Exception as e:
                print(f"  ❌ Error al migrar {nombre} ({email}): {e}")
        
        print()
        print(f"✅ Migración completada: {migrados} registros migrados")
        return migrados

def corregir_foreign_keys():
    """Corrige todas las ForeignKeys que apuntan a citas_cliente"""
    print("=" * 80)
    print("CORRECCIÓN DE FOREIGN KEYS")
    print("=" * 80)
    print()
    
    # ForeignKeys que necesitan corrección
    fks_a_corregir = [
        ('citas_mensaje', 'cliente_id', 'citas_mensaje_cliente_id_d89a66ce_fk_citas_cliente_id'),
        ('citas_odontograma', 'cliente_id', 'citas_odontograma_cliente_id_ceaa33a7_fk_citas_cliente_id'),
        ('citas_radiografia', 'cliente_id', 'citas_radiografia_cliente_id_6fb3e33a_fk_citas_cliente_id'),
    ]
    
    with connection.cursor() as cursor:
        for tabla, columna, constraint_name in fks_a_corregir:
            try:
                # Verificar si la constraint existe
                cursor.execute("""
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = %s;
                """, [constraint_name])
                
                if cursor.fetchone():
                    print(f"  Corrigiendo {tabla}.{columna}...")
                    
                    # Eliminar la constraint antigua
                    cursor.execute(f"""
                        ALTER TABLE {tabla} 
                        DROP CONSTRAINT IF EXISTS {constraint_name};
                    """)
                    
                    # Crear la nueva constraint apuntando a pacientes_cliente
                    nuevo_constraint = constraint_name.replace('citas_cliente', 'pacientes_cliente')
                    cursor.execute(f"""
                        ALTER TABLE {tabla}
                        ADD CONSTRAINT {nuevo_constraint}
                        FOREIGN KEY ({columna}) 
                        REFERENCES pacientes_cliente(id) 
                        ON DELETE SET NULL 
                        DEFERRABLE INITIALLY DEFERRED;
                    """)
                    
                    print(f"  ✅ {tabla}.{columna} corregida")
                else:
                    print(f"  ⚠️  {tabla}.{columna} no tiene la constraint esperada, verificando...")
                    
                    # Verificar si ya apunta a pacientes_cliente
                    cursor.execute("""
                        SELECT ccu.table_name
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                            ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.table_name = %s
                        AND kcu.column_name = %s
                        AND tc.constraint_type = 'FOREIGN KEY';
                    """, [tabla, columna])
                    
                    resultado = cursor.fetchone()
                    if resultado:
                        tabla_destino = resultado[0]
                        if tabla_destino == 'pacientes_cliente':
                            print(f"  ✅ {tabla}.{columna} ya apunta correctamente a pacientes_cliente")
                        else:
                            print(f"  ⚠️  {tabla}.{columna} apunta a {tabla_destino} (debería ser pacientes_cliente)")
                    else:
                        print(f"  ⚠️  {tabla}.{columna} no tiene ForeignKey definida")
                        
            except Exception as e:
                print(f"  ❌ Error al corregir {tabla}.{columna}: {e}")
    
    print()
    print("✅ Corrección de ForeignKeys completada")

def verificar_tabla_citas_cliente_vacia():
    """Verifica si la tabla citas_cliente está vacía y puede eliminarse"""
    print("=" * 80)
    print("VERIFICACIÓN DE TABLA citas_cliente")
    print("=" * 80)
    print()
    
    with connection.cursor() as cursor:
        # Verificar si hay datos
        cursor.execute("SELECT COUNT(*) FROM citas_cliente;")
        count = cursor.fetchone()[0]
        
        # Verificar si hay ForeignKeys que apunten a citas_cliente
        cursor.execute("""
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE ccu.table_name = 'citas_cliente'
            AND tc.constraint_type = 'FOREIGN KEY';
        """)
        fks_apuntando = cursor.fetchall()
        
        if count == 0 and not fks_apuntando:
            print("✅ La tabla citas_cliente está vacía y no tiene ForeignKeys apuntando a ella")
            print("   Puede eliminarse de forma segura")
            return True
        elif count > 0:
            print(f"⚠️  La tabla citas_cliente tiene {count} registros")
            print("   No se puede eliminar automáticamente")
        elif fks_apuntando:
            print(f"⚠️  Hay {len(fks_apuntando)} ForeignKey(s) apuntando a citas_cliente:")
            for tabla, columna in fks_apuntando:
                print(f"   - {tabla}.{columna}")
            print("   Estas deben corregirse antes de eliminar la tabla")
        
        return False

def main():
    """Función principal"""
    print("=" * 80)
    print("CORRECCIÓN DE ESTRUCTURA DE BASE DE DATOS")
    print("=" * 80)
    print()
    
    # 1. Verificar datos
    print("1. VERIFICANDO DATOS EN AMBAS TABLAS...")
    print("-" * 80)
    datos = verificar_datos_tablas()
    print(f"   citas_cliente: {datos['citas_cliente']['count']} registros")
    print(f"   pacientes_cliente: {datos['pacientes_cliente']['count']} registros")
    print()
    
    # 2. Migrar datos si es necesario
    if datos['citas_cliente']['count'] > 0:
        respuesta = input("¿Desea migrar datos de citas_cliente a pacientes_cliente? (s/n): ")
        if respuesta.lower() == 's':
            with transaction.atomic():
                migrar_datos_citas_cliente_a_pacientes_cliente()
        else:
            print("   Migración cancelada por el usuario")
        print()
    
    # 3. Corregir ForeignKeys
    print("2. CORRIGIENDO FOREIGN KEYS...")
    print("-" * 80)
    respuesta = input("¿Desea corregir las ForeignKeys automáticamente? (s/n): ")
    if respuesta.lower() == 's':
        with transaction.atomic():
            corregir_foreign_keys()
    else:
        print("   Corrección cancelada por el usuario")
    print()
    
    # 4. Verificar si se puede eliminar citas_cliente
    print("3. VERIFICANDO SI SE PUEDE ELIMINAR citas_cliente...")
    print("-" * 80)
    puede_eliminar = verificar_tabla_citas_cliente_vacia()
    print()
    
    if puede_eliminar:
        respuesta = input("¿Desea eliminar la tabla citas_cliente? (s/n): ")
        if respuesta.lower() == 's':
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS citas_cliente CASCADE;")
                print("✅ Tabla citas_cliente eliminada")
        else:
            print("   Eliminación cancelada por el usuario")
    
    print()
    print("=" * 80)
    print("PROCESO COMPLETADO")
    print("=" * 80)
    print()
    print("PRÓXIMOS PASOS:")
    print("1. Actualizar cliente_web/reservas/documentos_models.py para usar pacientes_cliente")
    print("2. Ejecutar migraciones en cliente_web si es necesario")
    print("3. Verificar que todo funcione correctamente")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


