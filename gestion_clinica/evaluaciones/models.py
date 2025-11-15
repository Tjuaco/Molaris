from django.db import models
from pacientes.models import Cliente
from personal.models import Perfil
from django.utils import timezone


# Evaluaciones de clientes sobre el sistema
class Evaluacion(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente de Revisión'),
        ('revisada', 'Revisada'),
        ('archivada', 'Archivada'),
    )
    
    # Información del cliente
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='evaluaciones',
        verbose_name="Cliente"
    )
    
    # Email de referencia para validación (debe coincidir con el del cliente)
    email_cliente = models.EmailField(verbose_name="Email del Cliente")
    
    # Calificación con estrellas (1-5)
    estrellas = models.PositiveSmallIntegerField(
        verbose_name="Calificación",
        help_text="Calificación de 1 a 5 estrellas"
    )
    
    # Mensaje de feedback
    comentario = models.TextField(
        max_length=500,
        verbose_name="Comentario",
        help_text="Mensaje de feedback del cliente (máximo 500 caracteres)"
    )
    
    # Estado de la evaluación
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='pendiente',
        verbose_name="Estado"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Envío")
    fecha_revision = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Revisión")
    revisada_por = models.ForeignKey(
        Perfil, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='evaluaciones_revisadas',
        verbose_name="Revisada Por"
    )
    
    # IP del cliente (para seguridad)
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")
    
    def marcar_como_revisada(self, trabajador):
        """Marca la evaluación como revisada"""
        if self.estado == 'pendiente':
            self.estado = 'revisada'
            self.fecha_revision = timezone.now()
            self.revisada_por = trabajador
            self.save()
    
    def archivar(self):
        """Archiva la evaluación"""
        self.estado = 'archivada'
        self.save()
    
    @property
    def estrellas_display(self):
        """Retorna las estrellas en formato visual"""
        return '⭐' * self.estrellas
    
    def __str__(self):
        return f"{self.cliente.nombre_completo} - {self.estrellas} estrellas ({self.fecha_creacion.strftime('%d/%m/%Y')})"
    
    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        ordering = ['-fecha_creacion']
        # Un cliente solo puede dejar una evaluación
        unique_together = ['cliente']
        indexes = [
            models.Index(fields=['-fecha_creacion']),
            models.Index(fields=['estado']),
            models.Index(fields=['estrellas']),
        ]
