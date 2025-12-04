from django.db import models
from personal.models import Perfil
from django.utils import timezone


class AuditoriaLog(models.Model):
    """Modelo para registrar movimientos y acciones del sistema"""
    
    ACCION_CHOICES = (
        ('crear', 'Crear'),
        ('actualizar', 'Actualizar'),
        ('editar', 'Editar'),
        ('eliminar', 'Eliminar'),
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('acceso_denegado', 'Acceso Denegado'),
        ('exportar', 'Exportar Datos'),
        ('importar', 'Importar Datos'),
        ('cambio_estado', 'Cambio de Estado'),
        ('otro', 'Otro'),
    )
    
    MODULO_CHOICES = (
        ('citas', 'Citas'),
        ('clientes', 'Clientes'),
        ('personal', 'Personal'),
        ('inventario', 'Inventario'),
        ('proveedores', 'Proveedores'),
        ('finanzas', 'Finanzas'),
        ('documentos', 'Documentos'),
        ('planes_tratamiento', 'Planes de Tratamiento'),
        ('odontogramas', 'Odontogramas'),
        ('radiografias', 'Radiografías'),
        ('servicios', 'Servicios'),
        ('configuracion', 'Configuración'),
        ('auditoria', 'Auditoría'),
        ('sistema', 'Sistema'),
        ('otro', 'Otro'),
    )
    
    # Usuario que realizó la acción
    usuario = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acciones_auditoria',
        verbose_name="Usuario"
    )
    
    # Tipo de acción
    accion = models.CharField(
        max_length=20,
        choices=ACCION_CHOICES,
        verbose_name="Acción"
    )
    
    # Módulo afectado
    modulo = models.CharField(
        max_length=20,
        choices=MODULO_CHOICES,
        verbose_name="Módulo"
    )
    
    # Descripción de la acción
    descripcion = models.CharField(
        max_length=500,
        verbose_name="Descripción"
    )
    
    # Detalles adicionales (JSON o texto)
    detalles = models.TextField(
        blank=True,
        null=True,
        verbose_name="Detalles Adicionales"
    )
    
    # IP del usuario
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP"
    )
    
    # Fecha y hora de la acción
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora"
    )
    
    # Referencia al objeto afectado (opcional)
    objeto_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="ID del Objeto"
    )
    
    # Tipo de objeto afectado
    tipo_objeto = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Tipo de Objeto"
    )
    
    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['-fecha_hora']),
            models.Index(fields=['usuario', '-fecha_hora']),
            models.Index(fields=['modulo', '-fecha_hora']),
            models.Index(fields=['accion', '-fecha_hora']),
        ]
    
    def __str__(self):
        usuario_nombre = self.usuario.nombre_completo if self.usuario else "Sistema"
        return f"{usuario_nombre} - {self.get_accion_display()} - {self.get_modulo_display()} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"


def registrar_auditoria(usuario, accion, modulo, descripcion, detalles=None, ip_address=None, objeto_id=None, tipo_objeto=None, request=None):
    """
    Función helper para registrar acciones en el log de auditoría
    
    Args:
        usuario: Perfil del usuario que realiza la acción (puede ser None)
        accion: Tipo de acción (crear, editar, eliminar, etc.)
        modulo: Módulo afectado (citas, clientes, etc.)
        descripcion: Descripción de la acción
        detalles: Detalles adicionales (opcional)
        ip_address: Dirección IP (opcional, se obtiene del request si se proporciona)
        objeto_id: ID del objeto afectado (opcional)
        tipo_objeto: Tipo del objeto afectado (opcional)
        request: Objeto request de Django (opcional, para obtener IP automáticamente)
    """
    try:
        # Obtener IP del request si está disponible
        if request and not ip_address:
            ip_address = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        
        # Limitar longitud de descripción y detalles
        descripcion = descripcion[:500] if descripcion else ''
        if detalles:
            detalles = detalles[:1000] if len(detalles) > 1000 else detalles
        
        AuditoriaLog.objects.create(
            usuario=usuario,
            accion=accion,
            modulo=modulo,
            descripcion=descripcion,
            detalles=detalles,
            ip_address=ip_address,
            objeto_id=objeto_id,
            tipo_objeto=tipo_objeto
        )
        
        # Limpieza automática de registros antiguos (ejecutar cada 100 registros para no afectar rendimiento)
        # Política: Mantener últimos 12 meses + máximo 100,000 registros
        import random
        if random.randint(1, 100) == 1:  # 1% de probabilidad = ejecutar cada ~100 registros
            limpiar_auditoria_antigua_automatica()
    except Exception as e:
        # No queremos que los errores de auditoría afecten el funcionamiento del sistema
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error al registrar auditoría: {str(e)}")


def limpiar_auditoria_antigua_automatica():
    """
    Limpia automáticamente registros de auditoría antiguos según la política:
    - Mantener los últimos 12 meses (365 días) completos
    - Si hay más de 100,000 registros, mantener solo los 100,000 más recientes
    """
    try:
        from datetime import timedelta
        
        # Calcular fecha límite (12 meses atrás)
        fecha_limite_12_meses = timezone.now() - timedelta(days=365)
        
        # Contar total de registros
        total_registros = AuditoriaLog.objects.count()
        
        # Si hay más de 100,000 registros, mantener solo los 100,000 más recientes
        if total_registros > 100000:
            # Obtener el ID del registro número 100,000 (ordenado por fecha descendente)
            registros_ordenados = AuditoriaLog.objects.order_by('-fecha_hora')[:100000]
            if registros_ordenados:
                # Obtener la fecha del último registro que queremos mantener
                fecha_limite_cantidad = registros_ordenados[99999].fecha_hora
                # Eliminar registros más antiguos que este
                registros_a_eliminar = AuditoriaLog.objects.filter(fecha_hora__lt=fecha_limite_cantidad)
                cantidad_eliminada = registros_a_eliminar.count()
                if cantidad_eliminada > 0:
                    registros_a_eliminar.delete()
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f'Limpieza automática de auditoría: Se eliminaron {cantidad_eliminada} registros antiguos (más de 100,000 registros)')
        else:
            # Si hay menos de 100,000 registros, eliminar solo los más antiguos de 12 meses
            registros_antiguos = AuditoriaLog.objects.filter(fecha_hora__lt=fecha_limite_12_meses)
            cantidad_eliminada = registros_antiguos.count()
            if cantidad_eliminada > 0:
                registros_antiguos.delete()
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'Limpieza automática de auditoría: Se eliminaron {cantidad_eliminada} registros anteriores a 12 meses')
    except Exception as e:
        # No queremos que los errores de limpieza afecten el funcionamiento del sistema
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en limpieza automática de auditoría: {str(e)}")

