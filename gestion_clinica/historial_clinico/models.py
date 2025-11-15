from django.db import models
from pacientes.models import Cliente
from personal.models import Perfil
from citas.models import Cita


# Odontograma - Ficha odontológica
class Odontograma(models.Model):
    ESTADO_DIENTE_CHOICES = (
        ('sano', 'Sano'),
        ('cariado', 'Cariado'),
        ('obturado', 'Obturado'),
        ('perdido', 'Perdido'),
        ('endodoncia', 'Endodoncia'),
        ('corona', 'Corona'),
        ('implante', 'Implante'),
        ('puente', 'Puente'),
        ('protesis', 'Prótesis'),
        ('extraccion', 'Extracción'),
    )
    
    CONDICION_CHOICES = (
        ('excelente', 'Excelente'),
        ('buena', 'Buena'),
        ('regular', 'Regular'),
        ('mala', 'Mala'),
        ('critica', 'Crítica'),
    )
    
    # Relación con cliente (opcional - permite historial)
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='odontogramas',
        verbose_name="Cliente del Sistema"
    )
    
    # Relación con cita (opcional - permite saber en qué cita se creó la ficha)
    cita = models.ForeignKey(
        Cita,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='odontogramas',
        verbose_name="Cita Asociada",
        help_text="Cita en la que se creó esta ficha odontológica"
    )
    
    # Información del paciente (campos de texto por compatibilidad)
    paciente_nombre = models.CharField(max_length=150, verbose_name="Nombre del Paciente")
    paciente_email = models.EmailField(verbose_name="Email del Paciente")
    paciente_telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    paciente_fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    
    # Información del dentista
    dentista = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='odontogramas', limit_choices_to={'rol': 'dentista'})
    
    # Fecha de creación y actualización
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Información general del odontograma
    motivo_consulta = models.TextField(verbose_name="Motivo de Consulta")
    antecedentes_medicos = models.TextField(blank=True, null=True, verbose_name="Antecedentes Médicos")
    alergias = models.TextField(blank=True, null=True, verbose_name="Alergias")
    medicamentos_actuales = models.TextField(blank=True, null=True, verbose_name="Medicamentos Actuales")
    
    # Estado general de la boca
    higiene_oral = models.CharField(max_length=20, choices=CONDICION_CHOICES, default='buena', verbose_name="Higiene Oral")
    estado_general = models.CharField(max_length=20, choices=CONDICION_CHOICES, default='buena', verbose_name="Estado General")
    
    # Observaciones generales
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones Generales")
    
    # Plan de tratamiento
    plan_tratamiento = models.TextField(blank=True, null=True, verbose_name="Plan de Tratamiento")
    proxima_cita = models.DateTimeField(blank=True, null=True, verbose_name="Próxima Cita")
    
    def __str__(self):
        return f"Odontograma - {self.paciente_nombre} ({self.fecha_creacion.strftime('%d/%m/%Y')})"
    
    class Meta:
        verbose_name = "Odontograma"
        verbose_name_plural = "Odontogramas"
        ordering = ['-fecha_creacion']


# Estado de cada diente en el odontograma
class EstadoDiente(models.Model):
    odontograma = models.ForeignKey(Odontograma, on_delete=models.CASCADE, related_name='dientes')
    
    # Número del diente (según numeración FDI)
    numero_diente = models.PositiveIntegerField(verbose_name="Número del Diente")
    
    # Estado del diente
    estado = models.CharField(max_length=20, choices=Odontograma.ESTADO_DIENTE_CHOICES, default='sano')
    
    # Información adicional
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones del Diente")
    fecha_tratamiento = models.DateField(blank=True, null=True, verbose_name="Fecha del Tratamiento")
    costo_tratamiento = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Costo del Tratamiento")
    
    def __str__(self):
        return f"Diente {self.numero_diente} - {self.get_estado_display()}"
    
    class Meta:
        verbose_name = "Estado de Diente"
        verbose_name_plural = "Estados de Dientes"
        unique_together = ['odontograma', 'numero_diente']
        ordering = ['numero_diente']


# Insumos utilizados en un odontograma
class InsumoOdontograma(models.Model):
    odontograma = models.ForeignKey(Odontograma, on_delete=models.CASCADE, related_name='insumos_utilizados')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='usos_en_odontogramas')
    cantidad_utilizada = models.PositiveIntegerField(verbose_name="Cantidad Utilizada")
    fecha_uso = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Uso")
    
    def __str__(self):
        return f"{self.insumo.nombre} ({self.cantidad_utilizada} {self.insumo.unidad_medida}) - {self.odontograma.paciente_nombre}"
    
    class Meta:
        verbose_name = "Insumo Utilizado en Odontograma"
        verbose_name_plural = "Insumos Utilizados en Odontogramas"
        ordering = ['-fecha_uso']


# Radiografías de pacientes
class Radiografia(models.Model):
    TIPO_RADIOGRAFIA_CHOICES = (
        ('panoramica', 'Panorámica'),
        ('periapical', 'Periapical'),
        ('bitewing', 'Bite-wing'),
        ('oclusal', 'Oclusal'),
        ('cefalometrica', 'Cefalométrica'),
        ('tomografia', 'Tomografía'),
        ('otra', 'Otra'),
    )
    
    # Relación con cliente (opcional - permite historial)
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='radiografias',
        verbose_name="Cliente del Sistema"
    )
    
    # Información del paciente (campos de texto por compatibilidad)
    paciente_email = models.EmailField(verbose_name="Email del Paciente")
    paciente_nombre = models.CharField(max_length=150, verbose_name="Nombre del Paciente")
    
    # Dentista que agregó la radiografía
    dentista = models.ForeignKey(
        Perfil, 
        on_delete=models.CASCADE, 
        related_name='radiografias_subidas',
        limit_choices_to={'rol': 'dentista'},
        verbose_name="Dentista"
    )
    
    # Asociación con cita (opcional)
    cita = models.ForeignKey(
        Cita,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='radiografias',
        verbose_name="Cita Asociada",
        help_text="Cita en la que se tomó esta radiografía (opcional)"
    )
    
    # Información de la radiografía
    tipo = models.CharField(
        max_length=20, 
        choices=TIPO_RADIOGRAFIA_CHOICES, 
        default='periapical',
        verbose_name="Tipo de Radiografía"
    )
    imagen = models.ImageField(
        upload_to='radiografias/%Y/%m/%d/', 
        verbose_name="Imagen de la Radiografía"
    )
    # Imagen con anotaciones persistentes (guardada como imagen procesada)
    imagen_anotada = models.ImageField(
        upload_to='radiografias/anotadas/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Imagen con Anotaciones",
        help_text="Imagen con las anotaciones guardadas (se genera automáticamente)"
    )
    descripcion = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Descripción"
    )
    fecha_tomada = models.DateField(
        blank=True, 
        null=True, 
        verbose_name="Fecha en que se tomó la radiografía",
        help_text="Fecha en que se tomó la radiografía (si es diferente de la fecha de carga)"
    )
    
    # Campos de auditoría
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Carga")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    
    def __str__(self):
        return f"Radiografía {self.get_tipo_display()} - {self.paciente_nombre} ({self.fecha_carga.strftime('%d/%m/%Y')})"
    
    class Meta:
        verbose_name = "Radiografía"
        verbose_name_plural = "Radiografías"
        ordering = ['-fecha_carga']
        indexes = [
            models.Index(fields=['paciente_email']),
            models.Index(fields=['-fecha_carga']),
            models.Index(fields=['dentista']),
        ]
