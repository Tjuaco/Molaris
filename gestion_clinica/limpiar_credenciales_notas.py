"""
Script para limpiar credenciales almacenadas en el campo notas de los clientes.

Este script elimina las credenciales (usuario y contraseña) que están guardadas
en texto plano en el campo notas de los clientes, por razones de seguridad.

USO:
    python limpiar_credenciales_notas.py [--dry-run] [--force]

    --dry-run: Solo muestra qué se limpiaría sin hacer cambios
    --force: Limpia sin confirmación (usar con cuidado)
"""
import os
import sys
import django
import argparse
import re

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_clinica.settings')
django.setup()

from pacientes.models import Cliente
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def limpiar_credenciales_de_notas(notas):
    """
    Elimina las credenciales del texto de notas, manteniendo solo la información de que tiene acceso web.
    
    Args:
        notas: Texto de notas que puede contener credenciales
    
    Returns:
        tuple: (notas_limpias, tenia_credenciales)
    """
    if not notas:
        return notas, False
    
    # Patrón para encontrar la sección [ACCESO WEB] con credenciales
    patron = r'\[ACCESO WEB\].*?(?:Usuario:\s*\S+.*?)?(?:Contraseña:\s*[^\n]+.*?)?(?:\([^)]+\))?'
    
    # Verificar si hay credenciales
    tiene_credenciales = bool(re.search(r'Contraseña:\s*[^\n]+', notas, re.IGNORECASE | re.DOTALL))
    
    if not tiene_credenciales:
        # Si no tiene contraseña, verificar si tiene usuario
        tiene_credenciales = bool(re.search(r'Usuario:\s*\S+', notas, re.IGNORECASE))
    
    if tiene_credenciales:
        # Eliminar la sección completa de credenciales
        notas_limpias = re.sub(
            r'\[ACCESO WEB\].*?(?=\n\n|\Z|$)',
            '',
            notas,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()
        
        # Si había una sección [ACCESO WEB], agregar una nueva sin credenciales
        if '[ACCESO WEB]' in notas.upper():
            # Buscar si hay información de fecha
            fecha_match = re.search(r'\(([^)]+)\)', notas)
            fecha_info = fecha_match.group(1) if fecha_match else None
            
            if fecha_info and ('registrado' in fecha_info.lower() or 'actualizado' in fecha_info.lower()):
                # Mantener la fecha pero sin credenciales
                notas_limpias = f"{notas_limpias}\n\n[ACCESO WEB]\nUsuario web {fecha_info}".strip()
            else:
                notas_limpias = f"{notas_limpias}\n\n[ACCESO WEB]\nUsuario web configurado".strip()
        
        return notas_limpias, True
    
    return notas, False


def main():
    parser = argparse.ArgumentParser(description='Limpiar credenciales almacenadas en notas de clientes')
    parser.add_argument('--dry-run', action='store_true', help='Solo mostrar qué se limpiaría sin hacer cambios')
    parser.add_argument('--force', action='store_true', help='Limpiar sin confirmación')
    args = parser.parse_args()
    
    print("=" * 70)
    print("  LIMPIEZA DE CREDENCIALES EN NOTAS DE CLIENTES")
    print("=" * 70)
    
    if args.dry_run:
        print("\n🔍 MODO DRY-RUN: Solo se mostrará qué se limpiaría\n")
    
    # Buscar clientes con credenciales en sus notas
    clientes_con_credenciales = []
    todos_los_clientes = Cliente.objects.all()
    
    for cliente in todos_los_clientes:
        if cliente.notas:
            notas_limpias, tenia_credenciales = limpiar_credenciales_de_notas(cliente.notas)
            if tenia_credenciales:
                clientes_con_credenciales.append({
                    'cliente': cliente,
                    'notas_originales': cliente.notas,
                    'notas_limpias': notas_limpias
                })
    
    print(f"\n📊 Clientes con credenciales en notas: {len(clientes_con_credenciales)}")
    
    if len(clientes_con_credenciales) == 0:
        print("\n✅ No se encontraron credenciales en las notas. Todo está limpio.")
        return
    
    # Mostrar resumen
    print("\n📋 Resumen de clientes a limpiar:")
    for item in clientes_con_credenciales[:10]:  # Mostrar solo los primeros 10
        cliente = item['cliente']
        print(f"   - ID: {cliente.id}, Nombre: {cliente.nombre_completo}, Email: {cliente.email}")
    
    if len(clientes_con_credenciales) > 10:
        print(f"   ... y {len(clientes_con_credenciales) - 10} más")
    
    # Limpiar si no es dry-run
    if not args.dry_run:
        if not args.force:
            respuesta = input(f"\n¿Deseas limpiar las credenciales de {len(clientes_con_credenciales)} cliente(s)? (s/n): ")
            if respuesta.lower() != 's':
                print("\n❌ Operación cancelada.")
                return
        
        print("\n🧹 Limpiando credenciales...")
        
        limpiados = 0
        for item in clientes_con_credenciales:
            try:
                cliente = item['cliente']
                cliente.notas = item['notas_limpias']
                cliente.save()
                limpiados += 1
                logger.info(f"✅ Credenciales limpiadas para cliente {cliente.id} ({cliente.nombre_completo})")
            except Exception as e:
                logger.error(f"❌ Error al limpiar cliente {item['cliente'].id}: {e}")
        
        print(f"\n{'=' * 70}")
        print(f"  ✅ LIMPIEZA COMPLETADA")
        print(f"{'=' * 70}")
        print(f"  Clientes limpiados: {limpiados} de {len(clientes_con_credenciales)}")
        print(f"\n⚠️ IMPORTANTE: Las credenciales ya no se guardarán en las notas.")
        print(f"   Las credenciales se envían por email cuando se crean o actualizan.")
    else:
        print("\n💡 Ejecuta sin --dry-run para limpiar las credenciales.")


if __name__ == '__main__':
    main()






