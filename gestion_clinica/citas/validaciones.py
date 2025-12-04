"""
Funciones de validación centralizadas para clientes y usuarios.

Estas funciones se usan en ambos sistemas (gestion_clinica y cliente_web)
para mantener consistencia en las validaciones.
"""
from django.contrib.auth.models import User
from pacientes.models import Cliente
import logging

logger = logging.getLogger(__name__)


def validar_email_cliente(email, cliente_excluido=None):
    """
    Valida si un email ya existe en un Cliente activo.
    
    Args:
        email: Email a validar
        cliente_excluido: Cliente a excluir de la validación (útil para actualizaciones)
    
    Returns:
        tuple: (existe: bool, mensaje_error: str o None)
    """
    if not email:
        return False, None
    
    email = email.strip().lower()
    
    # Validar formato básico
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
    except ValidationError:
        return False, "El formato del email no es válido"
    
    # Verificar si existe en Cliente ACTIVO
    query = Cliente.objects.filter(email__iexact=email, activo=True)
    if cliente_excluido:
        query = query.exclude(id=cliente_excluido.id)
    
    if query.exists():
        cliente = query.first()
        return True, f"Ya existe un cliente activo con ese email: {cliente.nombre_completo}"
    
    # Verificar si existe en User que tenga un Cliente activo asociado
    usuarios_con_cliente_activo = User.objects.filter(email__iexact=email).filter(
        cliente_asociado__activo=True
    )
    if cliente_excluido and cliente_excluido.user:
        usuarios_con_cliente_activo = usuarios_con_cliente_activo.exclude(id=cliente_excluido.user.id)
    
    if usuarios_con_cliente_activo.exists():
        usuarios_lista = ', '.join([u.username for u in usuarios_con_cliente_activo])
        return True, f"Ya existe un usuario con ese email asociado a un cliente activo. Usuarios: {usuarios_lista}"
    
    return False, None


def validar_rut_cliente(rut, cliente_excluido=None):
    """
    Valida si un RUT ya existe en un Cliente activo.
    
    Args:
        rut: RUT a validar (puede tener puntos y guión)
        cliente_excluido: Cliente a excluir de la validación
    
    Returns:
        tuple: (existe: bool, mensaje_error: str o None)
    """
    if not rut:
        return False, None
    
    rut = rut.strip()
    
    # Limpiar el RUT (quitar puntos y guiones)
    rut_limpio = rut.replace('.', '').replace('-', '').upper()
    
    # Validar formato básico
    if not rut_limpio[:-1].isdigit() or len(rut_limpio) < 8:
        return False, "El formato del RUT no es válido"
    
    # Buscar en Cliente activo (comparar RUTs normalizados)
    query = Cliente.objects.filter(activo=True).exclude(rut__isnull=True).exclude(rut='')
    if cliente_excluido:
        query = query.exclude(id=cliente_excluido.id)
    
    for cliente in query:
        if cliente.rut:
            rut_cliente_limpio = cliente.rut.replace('.', '').replace('-', '').upper()
            if rut_cliente_limpio == rut_limpio:
                return True, f"Ya existe un cliente activo con ese RUT: {cliente.nombre_completo}"
    
    return False, None


def validar_telefono_cliente(telefono, cliente_excluido=None):
    """
    Valida si un teléfono ya existe en un Cliente activo.
    
    Args:
        telefono: Teléfono a validar (debe estar normalizado: +569XXXXXXXX)
        cliente_excluido: Cliente a excluir de la validación
    
    Returns:
        tuple: (existe: bool, mensaje_error: str o None)
    """
    if not telefono:
        return False, None
    
    telefono = telefono.strip()
    
    # Verificar si existe en Cliente ACTIVO
    query = Cliente.objects.filter(telefono=telefono, activo=True)
    if cliente_excluido:
        query = query.exclude(id=cliente_excluido.id)
    
    if query.exists():
        cliente = query.first()
        return True, f"Ya existe un cliente activo con ese teléfono: {cliente.nombre_completo}"
    
    return False, None


def validar_username_disponible(username, user_excluido=None):
    """
    Valida si un username está disponible o tiene un Cliente activo asociado.
    
    Args:
        username: Username a validar
        user_excluido: User a excluir de la validación
    
    Returns:
        tuple: (disponible: bool, mensaje_error: str o None)
    """
    if not username:
        return False, "El username es requerido"
    
    username = username.strip()
    
    try:
        user = User.objects.get(username=username)
        
        # Si es el mismo usuario que estamos excluyendo, está disponible
        if user_excluido and user.id == user_excluido.id:
            return True, None
        
        # Verificar si este User tiene un Cliente activo asociado
        tiene_cliente_activo = Cliente.objects.filter(
            user=user,
            activo=True
        ).exists()
        
        if tiene_cliente_activo:
            return False, f"El nombre de usuario '{username}' ya existe y está asociado a un cliente activo"
        
        # Si el User existe pero no tiene Cliente activo, es huérfano y puede reutilizarse
        # pero es mejor advertir al usuario
        return True, f"El username existe pero no tiene cliente activo. Se reutilizará el usuario existente."
        
    except User.DoesNotExist:
        # El username no existe, está disponible
        return True, None


def validar_datos_cliente_completos(email, rut=None, telefono=None, cliente_excluido=None):
    """
    Valida todos los datos de un cliente de una vez.
    
    Returns:
        dict: {
            'valido': bool,
            'errores': list de mensajes de error,
            'advertencias': list de mensajes de advertencia
        }
    """
    errores = []
    advertencias = []
    
    # Validar email
    email_existe, email_error = validar_email_cliente(email, cliente_excluido)
    if email_existe:
        errores.append(email_error)
    
    # Validar RUT si se proporcionó
    if rut:
        rut_existe, rut_error = validar_rut_cliente(rut, cliente_excluido)
        if rut_existe:
            errores.append(rut_error)
    
    # Validar teléfono si se proporcionó
    if telefono:
        telefono_existe, telefono_error = validar_telefono_cliente(telefono, cliente_excluido)
        if telefono_existe:
            errores.append(telefono_error)
    
    return {
        'valido': len(errores) == 0,
        'errores': errores,
        'advertencias': advertencias
    }






