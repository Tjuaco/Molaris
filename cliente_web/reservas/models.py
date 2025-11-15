# reservas/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Cita(models.Model):
    fecha_hora = models.DateTimeField(unique=True)
    paciente_nombre = models.CharField(max_length=150, blank=True, null=True)
    paciente_email = models.EmailField(blank=True, null=True)
    paciente_telefono = models.CharField(max_length=20, blank=True, null=True)

    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)
    creada_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas_creadas'
    )
    dentista = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas_dentista'
    )
    estado = models.CharField(max_length=50, default='disponible')
    notas = models.TextField(blank=True, null=True)
    tipo_consulta = models.CharField(max_length=100, blank=True, null=True)

    # 👇 NUEVO
    whatsapp_message_sid = models.CharField(max_length=100, blank=True, null=True)
    
    # 👇 Campos de servicio y costo (desde la base de datos)
    tipo_servicio_id = models.BigIntegerField(blank=True, null=True)
    precio_cobrado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    @property
    def disponible(self):
        return self.estado == 'disponible'

    @property
    def tomada(self):
        return self.estado != 'disponible'

    def reservar(self, user):
        if self.estado == 'disponible':
            self.paciente_nombre = user.username
            self.paciente_email = user.email
            self.estado = 'reservada'
            self.save()

    def cancelar(self):
        self.paciente_nombre = None
        self.paciente_email = None
        self.paciente_telefono = None
        self.estado = 'disponible'
        self.save()

    def __str__(self):
        if self.estado != 'disponible':
            return f"{self.fecha_hora} - {self.estado.title()} por {self.paciente_nombre}"
        return f"{self.fecha_hora} - Libre"


    class Meta:
        db_table = "citas_cita"


class Evaluacion(models.Model):
    """Modelo para almacenar evaluaciones de clientes del servicio de citas"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Envío'),
        ('enviada', 'Enviada'),
        ('error', 'Error al Enviar'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluaciones')
    email_cliente = models.EmailField()
    estrellas = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación de 1 a 5 estrellas"
    )
    comentario = models.TextField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Estado de envío al sistema de gestión
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    error_mensaje = models.TextField(blank=True, null=True)
    
    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "evaluaciones_cliente"
        ordering = ['-creada_el']
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        # Solo una evaluación por usuario
        unique_together = ['user']
    
    def __str__(self):
        return f"Evaluación de {self.email_cliente} - {self.estrellas} estrellas"