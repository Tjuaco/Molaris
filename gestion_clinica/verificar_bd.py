import sqlite3
import os

db_path = 'db.sqlite3'

if os.path.exists(db_path):
    print(f"✓ Base de datos existe: {db_path}")
    size = os.path.getsize(db_path)
    print(f"  Tamaño: {size:,} bytes")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        print(f"\n✓ Tablas encontradas: {len(tables)}")
        for table in tables:
            # Contar registros en cada tabla
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                count = cursor.fetchone()[0]
                print(f"  - {table[0]}: {count} registros")
            except:
                print(f"  - {table[0]}: (error al contar)")
        
        conn.close()
        
        if len(tables) == 0:
            print("\n⚠ ADVERTENCIA: La base de datos existe pero NO tiene tablas.")
            print("  Ejecuta: python manage.py migrate")
        else:
            print(f"\n✓ Base de datos migrada correctamente con {len(tables)} tablas")
            
    except Exception as e:
        print(f"\n✗ Error al leer la base de datos: {e}")
else:
    print(f"✗ Base de datos NO existe: {db_path}")
    print("  Ejecuta: python manage.py migrate")







