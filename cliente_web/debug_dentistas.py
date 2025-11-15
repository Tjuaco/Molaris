import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cliente_web.settings')
django.setup()

from django.db import connections

def diagnosticar_citas():
    """Diagnóstico completo de citas y dentistas"""
    print("\n" + "="*80)
    print("DIAGNÓSTICO DE CITAS Y DENTISTAS")
    print("="*80)
    
    with connections['default'].cursor() as cursor:
        # 1. Ver todas las citas disponibles
        print("\n1. CITAS DISPONIBLES EN LA BD:")
        print("-"*80)
        cursor.execute("""
            SELECT id, fecha_hora, estado, dentista_id, tipo_consulta, 
                   paciente_nombre, creada_el
            FROM citas_cita
            WHERE estado = 'disponible'
            ORDER BY fecha_hora
        """)
        
        citas = cursor.fetchall()
        print(f"Total de citas disponibles: {len(citas)}\n")
        
        for cita in citas:
            cita_id, fecha_hora, estado, dentista_id, tipo_consulta, paciente, creada = cita
            print(f"Cita ID: {cita_id}")
            print(f"  Fecha/Hora: {fecha_hora}")
            print(f"  Estado: {estado}")
            print(f"  Tipo: {tipo_consulta or 'No especificado'}")
            print(f"  dentista_id: {dentista_id} {'✅ TIENE DENTISTA' if dentista_id else '❌ SIN DENTISTA'}")
            print(f"  Paciente: {paciente or 'Ninguno'}")
            print()
        
        # 2. Ver todos los perfiles de dentistas
        print("\n2. DENTISTAS EN CITAS_PERFIL:")
        print("-"*80)
        cursor.execute("""
            SELECT id, nombre_completo, rol, especialidad, activo, email
            FROM citas_perfil
            WHERE rol = 'dentista'
            ORDER BY id
        """)
        
        dentistas = cursor.fetchall()
        print(f"Total de dentistas: {len(dentistas)}\n")
        
        for dentista in dentistas:
            d_id, nombre, rol, especialidad, activo, email = dentista
            print(f"Dentista ID: {d_id}")
            print(f"  Nombre: {nombre}")
            print(f"  Rol: {rol}")
            print(f"  Especialidad: {especialidad}")
            print(f"  Activo: {activo}")
            print(f"  Email: {email}")
            print()
        
        # 3. Cruzar datos - ver qué citas tienen dentista y si ese dentista existe
        print("\n3. VERIFICACIÓN CRUZADA:")
        print("-"*80)
        for cita in citas:
            cita_id, fecha_hora, estado, dentista_id, tipo_consulta, paciente, creada = cita
            
            if dentista_id:
                cursor.execute("""
                    SELECT id, nombre_completo, rol, especialidad
                    FROM citas_perfil
                    WHERE id = %s
                """, [dentista_id])
                
                dentista = cursor.fetchone()
                
                print(f"Cita {cita_id} (dentista_id={dentista_id}):")
                if dentista:
                    print(f"  ✅ DENTISTA ENCONTRADO: {dentista[1]} ({dentista[3]})")
                else:
                    print(f"  ❌ DENTISTA NO ENCONTRADO - El ID {dentista_id} no existe en citas_perfil")
                print()
            else:
                print(f"Cita {cita_id}: ⚠️ Sin dentista_id asignado")
                print()
        
        # 4. Verificar tipos de datos de la columna dentista_id
        print("\n4. INFORMACIÓN DE LA COLUMNA dentista_id:")
        print("-"*80)
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'citas_cita' 
            AND column_name = 'dentista_id'
        """)
        
        col_info = cursor.fetchone()
        if col_info:
            print(f"Columna: {col_info[0]}")
            print(f"Tipo de dato: {col_info[1]}")
            print(f"Puede ser NULL: {col_info[2]}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    diagnosticar_citas()

