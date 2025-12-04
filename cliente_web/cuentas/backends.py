"""
Backend de autenticación personalizado para validar que el cliente exista en el sistema de gestión.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from reservas.documentos_models import ClienteDocumento
import logging

logger = logging.getLogger(__name__)

class ClienteBackend(ModelBackend):
    """
    Backend de autenticación que verifica que el cliente exista en pacientes_cliente del sistema de gestión.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica al usuario y verifica que exista en el sistema de gestión.
        """
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            # Intentar autenticar con el backend estándar primero
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Si el usuario no existe, no puede autenticarse
            return None
        
        # Verificar la contraseña
        if not user.check_password(password):
            return None
        
        # Verificar que el usuario tenga un PerfilCliente
        try:
            from .models import PerfilCliente
            perfil = PerfilCliente.objects.get(user=user)
        except PerfilCliente.DoesNotExist:
            # Si no tiene perfil, no es un cliente válido
            logger.warning(f"Usuario {username} intentó iniciar sesión pero no tiene PerfilCliente")
            return None
        
        # Verificar el estado del cliente en pacientes_cliente del sistema de gestión
        # IMPORTANTE: El sistema de gestión es la fuente de verdad
        # - Si el cliente NO existe en pacientes_cliente: Permitir login (puede ser un registro nuevo)
        # - Si el cliente existe pero está INACTIVO: Bloquear login (fue borrado/desactivado)
        # - Si el cliente existe y está ACTIVO: Permitir login
        try:
            # Buscar por email (método principal)
            cliente_doc = ClienteDocumento.objects.filter(email=perfil.email).first()
            if not cliente_doc:
                # Si no se encuentra por email, intentar por nombre completo
                cliente_doc = ClienteDocumento.objects.filter(nombre_completo=perfil.nombre_completo).first()
            
            if cliente_doc:
                # Cliente existe en el sistema de gestión
                if not cliente_doc.activo:
                    # Cliente fue borrado/desactivado en el sistema de gestión
                    logger.warning(f"Usuario {username} intentó iniciar sesión pero está INACTIVO en pacientes_cliente del sistema de gestión")
                    return None
                else:
                    # Cliente existe y está activo
                    logger.info(f"Cliente {username} encontrado y activo en pacientes_cliente del sistema de gestión")
            else:
                # Cliente no existe en pacientes_cliente (puede ser registro nuevo, permitir login)
                logger.info(f"Cliente {username} no encontrado en pacientes_cliente (puede ser registro nuevo), permitiendo login")
        except Exception as e:
            logger.error(f"Error al verificar cliente en pacientes_cliente: {e}")
            # En caso de error de conexión, permitir el login pero registrar el error
            # Esto evita que problemas de conexión bloqueen a todos los usuarios
        
        # Si todo está bien, retornar el usuario autenticado
        return user if self.user_can_authenticate(user) else None

