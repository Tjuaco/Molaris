from django.db import models
from personal.models import Perfil
from historial_clinico.models import Odontograma
from pacientes.models import Cliente
from django.utils import timezone


# Sistema de Mensajería Interna
class Mensaje(models.Model):
    TIPO_CHOICES = (
        ('general', 'Mensaje General'),
        ('odontograma', 'Envío de Odontograma'),
        ('cita', 'Información de Cita'),
        ('urgente', 'Urgente'),
    )
    
    ESTADO_CHOICES = (
        ('no_leido', 'No Leído'),
        ('leido', 'Leído'),
        ('archivado', 'Archivado'),
    )
    
    remitente = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='mensajes_enviados', verbose_name="Remitente")
    destinatario = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='mensajes_recibidos', verbose_name="Destinatario")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='general', verbose_name="Tipo de Mensaje")
    asunto = models.CharField(max_length=200, verbose_name="Asunto")
    mensaje = models.TextField(verbose_name="Mensaje")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='no_leido', verbose_name="Estado")
    
    # Referencias opcionales
    odontograma = models.ForeignKey(Odontograma, on_delete=models.SET_NULL, null=True, blank=True, related_name='mensajes', verbose_name="Odontograma Adjunto")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='mensajes', verbose_name="Cliente Relacionado")
    
    # Archivo adjunto
    archivo_adjunto = models.FileField(upload_to='mensajes/archivos/%Y/%m/', null=True, blank=True, verbose_name="Archivo Adjunto")
    
    # Fechas
    fecha_envio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Envío")
    fecha_lectura = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Lectura")
    
    def __str__(self):
        return f"{self.remitente.nombre_completo} → {self.destinatario.nombre_completo}: {self.asunto}"
    
    def marcar_como_leido(self):
        """Marca el mensaje como leído y registra la fecha"""
        if self.estado == 'no_leido':
            self.estado = 'leido'
            self.fecha_lectura = timezone.now()
            self.save()
    
    def get_extension_archivo(self):
        """Retorna la extensión del archivo adjunto"""
        if self.archivo_adjunto:
            return self.archivo_adjunto.name.split('.')[-1].lower()
        return None
    
    def tiene_archivo(self):
        """Verifica si el mensaje tiene archivo adjunto"""
        return bool(self.archivo_adjunto)
    
    class Meta:
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"
        ordering = ['-fecha_envio']
        indexes = [
            models.Index(fields=['-fecha_envio']),
            models.Index(fields=['destinatario', 'estado']),
        ]
