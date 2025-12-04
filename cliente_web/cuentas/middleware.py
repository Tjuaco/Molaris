"""
Middleware para verificar que los clientes autenticados sigan existiendo en el sistema de gestión.
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from reservas.documentos_models import ClienteDocumento
import logging

logger = logging.getLogger(__name__)

class ClienteActivoMiddleware:
    """
    Middleware que verifica que los clientes autenticados existan y estén activos en pacientes_cliente.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Rutas que no requieren verificación (login, registro, logout, inicio, estáticos)
        self.exempt_paths = [
            '/cuentas/login/',
            '/cuentas/logout/',
            '/cuentas/registro/',
            '/',
            '/inicio/',
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # Solo verificar si el usuario está autenticado y no está en rutas exentas
        if (request.user.is_authenticated and 
            not any(request.path.startswith(path) for path in self.exempt_paths)):
            
            try:
                from .models import PerfilCliente
                perfil = PerfilCliente.objects.get(user=request.user)
                
                # Verificar el estado del cliente en pacientes_cliente del sistema de gestión
                # IMPORTANTE: Solo bloquear si el cliente existe pero está INACTIVO (fue borrado)
                # Si no existe, permitir continuar (puede ser un registro nuevo)
                try:
                    # Buscar por email
                    cliente_doc = ClienteDocumento.objects.filter(email=perfil.email).first()
                    if not cliente_doc:
                        # Si no se encuentra por email, intentar por nombre completo
                        cliente_doc = ClienteDocumento.objects.filter(nombre_completo=perfil.nombre_completo).first()
                    
                    if cliente_doc:
                        # Cliente existe en el sistema de gestión
                        if not cliente_doc.activo:
                            # Cliente fue borrado/desactivado en el sistema de gestión, cerrar sesión
                            logger.warning(f"Cliente {request.user.username} está INACTIVO en pacientes_cliente, cerrando sesión")
                            logout(request)
                            messages.error(request, 'Tu cuenta ha sido desactivada en el sistema de gestión. Por favor, contacta a la clínica.')
                            return redirect('login_cliente')
                        # Si está activo, permitir continuar
                    # Si no existe, permitir continuar (puede ser registro nuevo que aún no se sincronizó)
                except Exception as e:
                    logger.error(f"Error al verificar cliente en middleware: {e}")
                    # En caso de error, permitir continuar para no bloquear a todos los usuarios
                    
            except PerfilCliente.DoesNotExist:
                # Si no tiene perfil, no es un cliente válido
                logger.warning(f"Usuario {request.user.username} no tiene PerfilCliente, cerrando sesión")
                logout(request)
                messages.error(request, 'Tu cuenta no está configurada correctamente. Por favor, contacta al administrador.')
                return redirect('login_cliente')
        
        response = self.get_response(request)
        return response

