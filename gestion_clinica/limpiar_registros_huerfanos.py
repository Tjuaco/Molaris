"""
Script para limpiar registros huérfanos en la base de datos.

Este script identifica y elimina:
1. PerfilCliente que no tienen un Cliente activo asociado
2. User que no tienen un Cliente activo asociado
3. Registros inconsistentes entre los dos sistemas

USO:
    python limpiar_registros_huerfanos.py [--dry-run] [--force]

    --dry-run: Solo muestra qué se eliminaría sin hacer cambios
    --force: Elimina sin confirmación (usar con cuidado)
"""
import os
import sys
import django
import argparse

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import connection
from pacientes.models import Cliente
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def encontrar_perfiles_huerfanos():
    """Encuentra PerfilCliente que no tienen un Cliente activo asociado"""
    huerfanos = []
    
    with connection.cursor() as cursor:
        # Obtener todos los PerfilCliente
        cursor.execute("""
            SELECT id, user_id, email, nombre_completo 
            FROM cuentas_perfilcliente
        """)
        perfiles = cursor.fetchall()
        
        for perfil_id, user_id, email, nombre in perfiles:
            # Verificar si existe un Cliente activo con este email
            cliente_activo = Cliente.objects.filter(
                email__iexact=email,
                activo=True
            ).exists()
            
            if not cliente_activo:
                huerfanos.append({
                    'tipo': 'PerfilCliente',
                    'id': perfil_id,
                    'user_id': user_id,
                    'email': email,
                    'nombre': nombre,
                    'razon': 'No tiene Cliente activo asociado'
                })
    
    return huerfanos


def encontrar_users_huerfanos():
    """Encuentra User que no tienen un Cliente activo asociado"""
    huerfanos = []
    
    # Obtener todos los Users
    users = User.objects.all()
    
    for user in users:
        # Verificar si tiene un Cliente activo asociado
        cliente_activo = Cliente.objects.filter(
            email__iexact=user.email,
            activo=True
        ).exists()
        
        # Verificar si tiene PerfilCliente
        tiene_perfil = False
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM cuentas_perfilcliente WHERE user_id = %s",
                [user.id]
            )
            tiene_perfil = cursor.fetchone() is not None
        
        # Si no tiene Cliente activo y no es staff/admin, es huérfano
        if not cliente_activo and not user.is_staff and not user.is_superuser:
            huerfanos.append({
                'tipo': 'User',
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'tiene_perfil': tiene_perfil,
                'razon': 'No tiene Cliente activo asociado y no es staff/admin'
            })
    
    return huerfanos


def eliminar_perfil_huerfano(perfil_id, user_id, dry_run=False):
    """Elimina un PerfilCliente huérfano y opcionalmente su User"""
    if dry_run:
        logger.info(f"[DRY-RUN] Eliminaría PerfilCliente ID={perfil_id}, User ID={user_id}")
        return True
    
    try:
        with connection.cursor() as cursor:
            # Eliminar PerfilCliente
            cursor.execute(
                "DELETE FROM cuentas_perfilcliente WHERE id = %s",
                [perfil_id]
            )
            logger.info(f"✅ PerfilCliente ID={perfil_id} eliminado")
            
            # Eliminar User si existe
            try:
                user = User.objects.get(id=user_id)
                user.delete()
                logger.info(f"✅ User ID={user_id} ({user.username}) eliminado")
            except User.DoesNotExist:
                logger.warning(f"⚠️ User ID={user_id} no existe")
            
        return True
    except Exception as e:
        logger.error(f"❌ Error al eliminar PerfilCliente ID={perfil_id}: {e}")
        return False


def eliminar_user_huerfano(user_id, dry_run=False):
    """Elimina un User huérfano y su PerfilCliente si existe"""
    if dry_run:
        logger.info(f"[DRY-RUN] Eliminaría User ID={user_id}")
        return True
    
    try:
        # Eliminar PerfilCliente primero (si existe)
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM cuentas_perfilcliente WHERE user_id = %s",
                [user_id]
            )
            if cursor.rowcount > 0:
                logger.info(f"✅ PerfilCliente asociado eliminado para User ID={user_id}")
        
        # Eliminar User
        user = User.objects.get(id=user_id)
        username = user.username
        user.delete()
        logger.info(f"✅ User ID={user_id} ({username}) eliminado")
        
        return True
    except User.DoesNotExist:
        logger.warning(f"⚠️ User ID={user_id} no existe")
        return False
    except Exception as e:
        logger.error(f"❌ Error al eliminar User ID={user_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Limpiar registros huérfanos en la base de datos')
    parser.add_argument('--dry-run', action='store_true', help='Solo mostrar qué se eliminaría sin hacer cambios')
    parser.add_argument('--force', action='store_true', help='Eliminar sin confirmación')
    args = parser.parse_args()
    
    print("=" * 70)
    print("  LIMPIEZA DE REGISTROS HUÉRFANOS")
    print("=" * 70)
    
    if args.dry_run:
        print("\n🔍 MODO DRY-RUN: Solo se mostrará qué se eliminaría\n")
    
    # 1. Encontrar PerfilCliente huérfanos
    print("\n1. Buscando PerfilCliente huérfanos...")
    perfiles_huerfanos = encontrar_perfiles_huerfanos()
    print(f"   Encontrados: {len(perfiles_huerfanos)}")
    
    for perfil in perfiles_huerfanos:
        print(f"   - ID: {perfil['id']}, Email: {perfil['email']}, Nombre: {perfil['nombre']}")
        print(f"     Razón: {perfil['razon']}")
    
    # 2. Encontrar User huérfanos
    print("\n2. Buscando User huérfanos...")
    users_huerfanos = encontrar_users_huerfanos()
    print(f"   Encontrados: {len(users_huerfanos)}")
    
    for user in users_huerfanos:
        tiene_perfil_texto = "Sí" if user['tiene_perfil'] else "No"
        print(f"   - ID: {user['id']}, Username: {user['username']}, Email: {user['email']}")
        print(f"     Tiene PerfilCliente: {tiene_perfil_texto}, Razón: {user['razon']}")
    
    # 3. Resumen
    total_huerfanos = len(perfiles_huerfanos) + len(users_huerfanos)
    print(f"\n{'=' * 70}")
    print(f"  RESUMEN: {total_huerfanos} registro(s) huérfano(s) encontrado(s)")
    print(f"{'=' * 70}")
    
    if total_huerfanos == 0:
        print("\n✅ No se encontraron registros huérfanos. La base de datos está limpia.")
        return
    
    # 4. Eliminar si no es dry-run
    if not args.dry_run:
        if not args.force:
            respuesta = input(f"\n¿Deseas eliminar estos {total_huerfanos} registro(s) huérfano(s)? (s/n): ")
            if respuesta.lower() != 's':
                print("\n❌ Operación cancelada.")
                return
        
        print("\n3. Eliminando registros huérfanos...")
        
        # Eliminar PerfilCliente huérfanos
        eliminados_perfiles = 0
        for perfil in perfiles_huerfanos:
            if eliminar_perfil_huerfano(perfil['id'], perfil['user_id'], dry_run=False):
                eliminados_perfiles += 1
        
        # Eliminar User huérfanos (solo los que no tienen PerfilCliente, para evitar duplicados)
        eliminados_users = 0
        for user in users_huerfanos:
            if not user['tiene_perfil']:  # Solo eliminar si no tiene PerfilCliente (ya se eliminó arriba)
                if eliminar_user_huerfano(user['id'], dry_run=False):
                    eliminados_users += 1
        
        print(f"\n{'=' * 70}")
        print(f"  ✅ LIMPIEZA COMPLETADA")
        print(f"{'=' * 70}")
        print(f"  PerfilCliente eliminados: {eliminados_perfiles}")
        print(f"  User eliminados: {eliminados_users}")
        print(f"  Total eliminados: {eliminados_perfiles + eliminados_users}")
    else:
        print("\n💡 Ejecuta sin --dry-run para eliminar los registros.")


if __name__ == '__main__':
    main()






