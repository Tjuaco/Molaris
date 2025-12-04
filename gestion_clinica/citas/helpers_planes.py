"""
Helper functions para gestión de permisos de Planes de Tratamiento
"""
from django.core.exceptions import PermissionDenied
from personal.models import Perfil
from pacientes.models import Cliente


def verificar_permiso_plan_tratamiento(perfil, plan=None, cliente_id=None):
    """
    Verifica si un perfil tiene permisos para gestionar un plan de tratamiento.
    
    Args:
        perfil: Perfil del usuario
        plan: PlanTratamiento (opcional, para verificar plan existente)
        cliente_id: ID del cliente (opcional, para verificar al crear)
    
    Returns:
        bool: True si tiene permisos
    
    Raises:
        PermissionDenied: Si no tiene permisos
    """
    if not perfil.activo:
        raise PermissionDenied('Tu cuenta está desactivada.')
    
    # Administradores tienen acceso completo
    if perfil.es_administrativo():
        return True
    
    # Dentistas solo pueden gestionar planes de sus clientes
    if perfil.es_dentista():
        pacientes_dentista = perfil.get_pacientes_asignados()
        clientes_ids = [p['id'] for p in pacientes_dentista if 'id' in p and isinstance(p['id'], int)]
        
        if plan:
            # Verificar que el plan es del dentista y del cliente correcto
            if plan.dentista != perfil:
                raise PermissionDenied('Solo puedes gestionar planes donde eres el dentista asignado.')
            if plan.cliente.id not in clientes_ids:
                raise PermissionDenied('Solo puedes gestionar planes de tus pacientes.')
        
        if cliente_id:
            # Verificar que el cliente es del dentista
            if int(cliente_id) not in clientes_ids:
                raise PermissionDenied('Solo puedes crear planes para tus pacientes.')
        
        return True
    
    # Otros roles no tienen acceso
    raise PermissionDenied('No tienes permisos para gestionar planes de tratamiento.')


def obtener_clientes_permitidos(perfil):
    """
    Retorna los clientes que el perfil puede gestionar.
    Administradores: todos los clientes activos
    Dentistas: solo sus pacientes
    """
    if perfil.es_administrativo():
        return Cliente.objects.filter(activo=True).order_by('nombre_completo')
    elif perfil.es_dentista():
        pacientes_dentista = perfil.get_pacientes_asignados()
        clientes_ids = [p['id'] for p in pacientes_dentista if 'id' in p and isinstance(p['id'], int)]
        return Cliente.objects.filter(id__in=clientes_ids, activo=True).order_by('nombre_completo')
    else:
        return Cliente.objects.none()







