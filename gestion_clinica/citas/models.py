from django.db import models
from pacientes.models import Cliente
from personal.models import Perfil

# Importar modelo de auditoría
from .models_auditoria import AuditoriaLog, registrar_auditoria


# Citas disponibles o tomadas
class Cita(models.Model):
    ESTADO_CHOICES = (
        ('disponible', 'Disponible'),
        ('reservada', 'Reservada'),
        ('en_espera', 'En Espera'),
        ('listo_para_atender', 'Listo para Atender'),
        ('en_progreso', 'En Progreso'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
        ('no_show', 'No Llegó'),
    )
    
    fecha_hora = models.DateTimeField(unique=True)
    
    # Información del cliente
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas')
    
    # Campos de respaldo para compatibilidad (se mantienen por si hay citas sin cliente asignado)
    paciente_nombre = models.CharField(max_length=150, blank=True, null=True)
    paciente_email = models.EmailField(blank=True, null=True)
    paciente_telefono = models.CharField(max_length=20, blank=True, null=True)
    
    # Campos adicionales para mejor gestión
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')
    tipo_consulta = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de Consulta (Texto Libre)")
    
    # Relación con Tipo de Servicio (nuevo sistema de servicios)
    tipo_servicio = models.ForeignKey(
        'TipoServicio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas',
        verbose_name="Tipo de Servicio"
    )
    precio_cobrado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio Cobrado",
        help_text="Precio final cobrado (puede diferir del precio base del servicio)"
    )
    
    notas = models.TextField(blank=True, null=True)
    notas_paciente = models.TextField(blank=True, null=True, verbose_name="Notas del Paciente")
    
    # Campo para registrar hora de llegada del paciente
    hora_llegada = models.DateTimeField(blank=True, null=True, verbose_name="Hora de Llegada")
    
    # Campo para registrar motivo de no asistencia
    motivo_no_asistencia = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo de No Asistencia",
        help_text="Razón por la cual el paciente no asistió a la cita"
    )
    
    # Campos de finalización y pago
    METODO_PAGO_CHOICES = (
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Método de Pago"
    )
    motivo_ajuste_precio = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo del Ajuste de Precio",
        help_text="Justificación si el precio difiere del precio base del servicio"
    )
    notas_finalizacion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas de Finalización",
        help_text="Observaciones adicionales al completar la cita"
    )
    
    # Campos de auditoría
    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)
    creada_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas_creadas')
    completada_por = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_completadas',
        verbose_name="Completada por"
    )
    fecha_completada = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Finalización")
    
    # Relación con dentista (si es una cita reservada)
    dentista = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas_asignadas')
    
    # Relación con Plan de Tratamiento
    plan_tratamiento = models.ForeignKey(
        'historial_clinico.PlanTratamiento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas',
        verbose_name="Plan de Tratamiento"
    )
    fase_tratamiento = models.ForeignKey(
        'historial_clinico.FaseTratamiento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas',
        verbose_name="Fase del Tratamiento"
    )
    
    @property
    def disponible(self):
        return self.estado == 'disponible'
    
    @property
    def reservada(self):
        return self.estado == 'reservada'
    
    @property
    def nombre_paciente(self):
        """Obtiene el nombre del paciente de forma segura (cliente o campo de respaldo)"""
        if self.cliente:
            return self.cliente.nombre_completo
        return self.paciente_nombre or 'Sin nombre'
    
    @property
    def email_paciente(self):
        """Obtiene el email del paciente de forma segura (cliente o campo de respaldo)"""
        if self.cliente:
            return self.cliente.email
        return self.paciente_email or ''
    
    @property
    def telefono_paciente(self):
        """Obtiene el teléfono del paciente de forma segura (cliente o campo de respaldo)"""
        if self.cliente:
            return self.cliente.telefono
        return self.paciente_telefono or ''
    
    def reservar(self, cliente=None, paciente_nombre=None, paciente_email=None, paciente_telefono=None, dentista=None):
        """Reserva una cita para un paciente"""
        if self.estado == 'disponible':
            if cliente:
                self.cliente = cliente
                self.paciente_nombre = cliente.nombre_completo
                self.paciente_email = cliente.email
                self.paciente_telefono = cliente.telefono
            else:
                self.paciente_nombre = paciente_nombre
                self.paciente_email = paciente_email
                self.paciente_telefono = paciente_telefono
            self.estado = 'reservada'
            self.dentista = dentista
            self.save()
            return True
        return False
    
    def cancelar(self):
        """Cancela una cita"""
        if self.estado == 'reservada':
            self.estado = 'cancelada'
            # Preservar información del paciente para el historial
            # Asegurar que los datos de respaldo estén guardados antes de eliminar la relación
            if self.cliente:
                # Si tiene cliente, asegurar que los datos de respaldo estén guardados
                if not self.paciente_nombre or self.paciente_nombre != self.cliente.nombre_completo:
                    self.paciente_nombre = self.cliente.nombre_completo
                if not self.paciente_email or self.paciente_email != self.cliente.email:
                    self.paciente_email = self.cliente.email
                if not self.paciente_telefono or (self.cliente.telefono and self.paciente_telefono != self.cliente.telefono):
                    self.paciente_telefono = self.cliente.telefono or self.paciente_telefono
            # Si no tiene cliente pero tiene paciente_nombre, mantenerlo
            # Eliminar solo la relación con cliente, pero mantener dentista y datos de respaldo
            # El dentista se mantiene porque es información histórica importante
            self.cliente = None
            # NO eliminamos el dentista para preservar el historial
            # self.dentista = None  # Comentado para preservar información histórica
            self.save()
            return True
        return False
    
    def completar(self):
        """Marca una cita como completada"""
        if self.estado == 'reservada':
            self.estado = 'completada'
            self.save()
            return True
        return False
    
    def requiere_atencion(self):
        """
        Verifica si la cita requiere atención del administrador.
        Retorna True si:
        - La fecha y hora ya pasó
        - El estado es 'disponible' (no fue tomada) o 'reservada' (no fue iniciada)
        - No está en estados finales (completada, cancelada, no_show)
        """
        from django.utils import timezone
        
        # Si la fecha/hora ya pasó
        if self.fecha_hora < timezone.now():
            # Estados que requieren atención si la cita ya pasó
            estados_requieren_atencion = ['disponible', 'reservada', 'confirmada']
            if self.estado in estados_requieren_atencion:
                return True
        
        return False
    
    def __str__(self):
        if self.estado == 'disponible':
            return f"{self.fecha_hora} - Libre"
        elif self.estado == 'reservada':
            return f"{self.fecha_hora} - Reservada por {self.paciente_nombre}"
        else:
            return f"{self.fecha_hora} - {self.get_estado_display()} - {self.paciente_nombre}"


# Tipos de Servicios Dentales
class TipoServicio(models.Model):
    CATEGORIA_CHOICES = (
        ('preventivo', 'Preventivo'),
        ('restaurador', 'Restaurador'),
        ('endodoncico', 'Endodóncico'),
        ('protesico', 'Protésico'),
        ('quirurgico', 'Quirúrgico'),
        ('estetico', 'Estético'),
        ('ortodontico', 'Ortodóncico'),
        ('otros', 'Otros'),
    )
    
    nombre = models.CharField(max_length=150, unique=True, verbose_name="Nombre del Servicio")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otros', verbose_name="Categoría")
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Base")
    activo = models.BooleanField(default=True, verbose_name="Servicio Activo")
    requiere_dentista = models.BooleanField(default=True, verbose_name="Requiere Dentista", help_text="Si este servicio requiere un dentista específico")
    duracion_estimada = models.IntegerField(
        blank=True, 
        null=True, 
        help_text="Duración estimada en minutos", 
        verbose_name="Duración Estimada"
    )
    
    # Campos de auditoría
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    creado_por = models.ForeignKey(
        Perfil, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='servicios_creados',
        verbose_name="Creado por"
    )
    
    def __str__(self):
        return f"{self.nombre} - ${self.precio_base}"
    
    class Meta:
        verbose_name = "Tipo de Servicio"
        verbose_name_plural = "Tipos de Servicios"
        ordering = ['categoria', 'nombre']


# Horarios de trabajo de los dentistas
class HorarioDentista(models.Model):
    DIA_SEMANA_CHOICES = (
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )
    
    dentista = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        related_name='horarios',
        limit_choices_to={'rol': 'dentista'},
        verbose_name="Dentista"
    )
    dia_semana = models.IntegerField(choices=DIA_SEMANA_CHOICES, verbose_name="Día de la Semana")
    hora_inicio = models.TimeField(verbose_name="Hora de Inicio")
    hora_fin = models.TimeField(verbose_name="Hora de Fin")
    activo = models.BooleanField(default=True, verbose_name="Horario Activo")
    
    # Campos de auditoría
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    class Meta:
        verbose_name = "Horario de Dentista"
        verbose_name_plural = "Horarios de Dentistas"
        ordering = ['dentista', 'dia_semana', 'hora_inicio']
        unique_together = [['dentista', 'dia_semana', 'hora_inicio', 'hora_fin']]
    
    def __str__(self):
        return f"{self.dentista.nombre_completo} - {self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')}-{self.hora_fin.strftime('%H:%M')}"
    
    def clean(self):
        """Validar que hora_fin sea mayor que hora_inicio"""
        from django.core.exceptions import ValidationError
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError('La hora de fin debe ser mayor que la hora de inicio.')
