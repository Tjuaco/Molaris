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


# ==========================================
# PLANES DE TRATAMIENTO
# ==========================================

class PlanTratamiento(models.Model):
    ESTADO_CHOICES = (
        ('borrador', 'Borrador'),
        ('pendiente_aprobacion', 'Pendiente Aprobación'),
        ('aprobado', 'Aprobado'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
        ('rechazado', 'Rechazado'),
    )
    
    # Relaciones principales
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='planes_tratamiento',
        verbose_name="Cliente"
    )
    dentista = models.ForeignKey(
        Perfil, 
        on_delete=models.CASCADE, 
        limit_choices_to={'rol': 'dentista'},
        related_name='planes_tratamiento',
        verbose_name="Dentista Asignado"
    )
    odontograma_inicial = models.ForeignKey(
        Odontograma, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='planes_tratamiento',
        verbose_name="Odontograma Inicial"
    )
    
    # Información del plan
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Plan")
    descripcion = models.TextField(verbose_name="Descripción")
    diagnostico = models.TextField(verbose_name="Diagnóstico")
    objetivo = models.TextField(verbose_name="Objetivo del Tratamiento")
    
    # Presupuesto
    presupuesto_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Presupuesto Total"
    )
    descuento = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Descuento"
    )
    precio_final = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Precio Final"
    )
    presupuesto_aceptado = models.BooleanField(
        default=False,
        verbose_name="Presupuesto Aceptado",
        help_text="Indica si el paciente ha aceptado el presupuesto"
    )
    fecha_aceptacion_presupuesto = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aceptación del Presupuesto"
    )
    
    # Estado y fechas
    estado = models.CharField(
        max_length=30, 
        choices=ESTADO_CHOICES, 
        default='borrador',
        verbose_name="Estado"
    )
    fecha_inicio_estimada = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Fecha de Inicio Estimada"
    )
    fecha_fin_estimada = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Fecha de Fin Estimada"
    )
    citas_estimadas = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Citas Estimadas",
        help_text="Número estimado de citas que requerirá este tratamiento"
    )
    fecha_aprobacion = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de Aprobación"
    )
    fecha_completado = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de Completado"
    )
    fecha_cancelacion = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha de Cancelación"
    )
    motivo_cancelacion = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Motivo de Cancelación"
    )
    
    # Auditoría
    creado_por = models.ForeignKey(
        Perfil, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='planes_creados',
        verbose_name="Creado por"
    )
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    
    # Control de eliminación
    eliminado_por = models.ForeignKey(
        Perfil, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='planes_eliminados',
        verbose_name="Eliminado por"
    )
    fecha_eliminacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Eliminación")
    motivo_eliminacion = models.TextField(blank=True, null=True, verbose_name="Motivo de Eliminación")
    
    # Notas
    notas_internas = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notas Internas",
        help_text="Notas solo visibles para el personal administrativo"
    )
    notas_paciente = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notas para el Paciente",
        help_text="Notas que pueden ser visibles para el paciente"
    )
    
    def save(self, *args, **kwargs):
        """Calcula el precio final automáticamente"""
        self.precio_final = self.presupuesto_total - self.descuento
        super().save(*args, **kwargs)
    
    @property
    def progreso_porcentaje(self):
        """Calcula el porcentaje de progreso del plan"""
        fases = self.fases.all()
        if not fases.exists():
            return 0
        
        fases_completadas = fases.filter(completada=True).count()
        total_fases = fases.count()
        
        return int((fases_completadas / total_fases) * 100) if total_fases > 0 else 0
    
    @property
    def total_citas(self):
        """Retorna el total de citas vinculadas al plan"""
        return self.citas.count()
    
    @property
    def citas_completadas(self):
        """Retorna el número de citas completadas"""
        return self.citas.filter(estado='completada').count()
    
    def puede_ser_editado_por(self, perfil):
        """Verifica si un perfil puede editar este plan - Solo administrativos pueden editar"""
        return perfil.es_administrativo()
    
    def puede_ser_eliminado_por(self, perfil):
        """Solo administrativos pueden eliminar definitivamente"""
        return perfil.es_administrativo()
    
    def puede_ser_cancelado_por(self, perfil):
        """Dentistas pueden cancelar sus planes"""
        if perfil.es_administrativo():
            return True
        if perfil.es_dentista() and self.dentista == perfil:
            return self.estado in ['aprobado', 'en_progreso']
        return False
    
    @property
    def total_pagado(self):
        """Calcula el total pagado del tratamiento basado en precios de citas"""
        from decimal import Decimal
        total = Decimal('0.00')
        # Sumar precios de todas las citas del tratamiento
        for cita in self.citas.all():
            if cita.precio_cobrado:
                total += Decimal(str(cita.precio_cobrado))
        return total
    
    @property
    def saldo_pendiente(self):
        """Calcula el saldo pendiente del tratamiento"""
        return self.precio_final - self.total_pagado
    
    @property
    def porcentaje_pagado(self):
        """Calcula el porcentaje del tratamiento que ha sido pagado"""
        if self.precio_final <= 0:
            return 0
        porcentaje = (self.total_pagado / self.precio_final) * 100
        return min(100, float(porcentaje))
    
    def esta_pagado_completamente(self):
        """Verifica si el tratamiento está completamente pagado"""
        return self.saldo_pendiente <= 0
    
    def __str__(self):
        return f"{self.nombre} - {self.cliente.nombre_completo}"
    
    class Meta:
        verbose_name = "Plan de Tratamiento"
        verbose_name_plural = "Planes de Tratamiento"
        ordering = ['-creado_el']
        indexes = [
            models.Index(fields=['-creado_el']),
            models.Index(fields=['estado']),
            models.Index(fields=['dentista', 'estado']),
            models.Index(fields=['cliente']),
        ]


class FaseTratamiento(models.Model):
    plan = models.ForeignKey(
        PlanTratamiento, 
        on_delete=models.CASCADE, 
        related_name='fases',
        verbose_name="Plan de Tratamiento"
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Fase")
    descripcion = models.TextField(verbose_name="Descripción")
    orden = models.PositiveIntegerField(verbose_name="Orden", help_text="Orden de la fase en el plan")
    
    # Presupuesto de la fase
    presupuesto = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Presupuesto de la Fase"
    )
    
    # Estado
    completada = models.BooleanField(default=False, verbose_name="Completada")
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de Fin")
    
    def __str__(self):
        return f"{self.plan.nombre} - {self.nombre}"
    
    class Meta:
        verbose_name = "Fase de Tratamiento"
        verbose_name_plural = "Fases de Tratamiento"
        ordering = ['plan', 'orden']
        unique_together = ['plan', 'orden']


class ItemTratamiento(models.Model):
    fase = models.ForeignKey(
        FaseTratamiento, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Fase"
    )
    servicio = models.ForeignKey(
        'citas.TipoServicio', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='items_tratamiento',
        verbose_name="Servicio"
    )
    descripcion = models.CharField(
        max_length=300,
        verbose_name="Descripción del Item"
    )
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    precio_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Precio Unitario"
    )
    precio_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Precio Total"
    )
    
    # Estado
    completado = models.BooleanField(default=False, verbose_name="Completado")
    fecha_completado = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Completado")
    
    def save(self, *args, **kwargs):
        """Calcula el precio total automáticamente"""
        self.precio_total = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.fase.nombre} - {self.descripcion}"
    
    class Meta:
        verbose_name = "Item de Tratamiento"
        verbose_name_plural = "Items de Tratamiento"
        ordering = ['fase', 'id']


class PagoTratamiento(models.Model):
    """Modelo para gestionar pagos parciales de planes de tratamiento"""
    
    METODO_PAGO_CHOICES = (
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('cheque', 'Cheque'),
    )
    
    # Relación con el plan de tratamiento
    plan_tratamiento = models.ForeignKey(
        PlanTratamiento,
        on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name="Plan de Tratamiento"
    )
    
    # Información del pago
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto del Pago"
    )
    fecha_pago = models.DateField(
        verbose_name="Fecha de Pago"
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        verbose_name="Método de Pago"
    )
    
    # Información adicional
    numero_comprobante = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Número de Comprobante",
        help_text="Número de transferencia, cheque, o comprobante"
    )
    notas = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas",
        help_text="Notas adicionales sobre el pago"
    )
    
    # Relación con cita (opcional - si el pago está asociado a una cita específica)
    cita = models.ForeignKey(
        Cita,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos_tratamiento',
        verbose_name="Cita Asociada",
        help_text="Si el pago está asociado a una cita específica del tratamiento"
    )
    
    # Auditoría
    registrado_por = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pagos_registrados',
        verbose_name="Registrado por"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro"
    )
    
    def __str__(self):
        return f"Pago de ${self.monto} - {self.plan_tratamiento.nombre} - {self.fecha_pago}"
    
    class Meta:
        verbose_name = "Pago de Tratamiento"
        verbose_name_plural = "Pagos de Tratamiento"
        ordering = ['-fecha_pago', '-fecha_registro']
        indexes = [
            models.Index(fields=['plan_tratamiento', '-fecha_pago']),
        ]


# ==========================================
# GESTIÓN DE DOCUMENTOS
# ==========================================

class DocumentoCliente(models.Model):
    """Modelo para gestionar documentos generados para clientes"""
    
    TIPO_DOCUMENTO_CHOICES = (
        ('presupuesto', 'Presupuesto/Tratamiento'),
        ('odontograma', 'Ficha Odontológica'),
        ('radiografia', 'Radiografía'),
        ('consentimiento', 'Consentimiento Informado'),
        ('receta', 'Receta Médica'),
        ('factura', 'Factura'),
        ('nota_medica', 'Nota Médica'),
        ('otro', 'Otro'),
    )
    
    # Relación con cliente (opcional - algunos documentos pueden no tener cliente asociado)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name="Cliente",
        null=True,
        blank=True
    )
    
    # Tipo y categoría del documento
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_DOCUMENTO_CHOICES,
        verbose_name="Tipo de Documento"
    )
    
    # Título y descripción
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título del Documento"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )
    
    # Referencias a otros modelos (opcionales)
    plan_tratamiento = models.ForeignKey(
        PlanTratamiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos',
        verbose_name="Plan de Tratamiento"
    )
    odontograma = models.ForeignKey(
        Odontograma,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos',
        verbose_name="Odontograma"
    )
    cita = models.ForeignKey(
        Cita,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos',
        verbose_name="Cita"
    )
    
    # Archivo PDF generado
    archivo_pdf = models.FileField(
        upload_to='documentos/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Archivo PDF"
    )
    
    # Información de generación
    generado_por = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        related_name='documentos_generados',
        verbose_name="Generado por"
    )
    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Generación"
    )
    
    # Información de envío
    enviado_por_correo = models.BooleanField(
        default=False,
        verbose_name="Enviado por Correo"
    )
    fecha_envio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Envío"
    )
    email_destinatario = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email Destinatario"
    )
    
    # Notas adicionales
    notas = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cliente.nombre_completo} ({self.fecha_generacion.strftime('%d/%m/%Y')})"
    
    class Meta:
        verbose_name = "Documento de Cliente"
        verbose_name_plural = "Documentos de Clientes"
        ordering = ['-fecha_generacion']
        indexes = [
            models.Index(fields=['cliente', '-fecha_generacion']),
            models.Index(fields=['tipo', '-fecha_generacion']),
            models.Index(fields=['-fecha_generacion']),
        ]


# ==========================================
# CONSENTIMIENTOS INFORMADOS
# ==========================================

class PlantillaConsentimiento(models.Model):
    """Plantillas reutilizables para consentimientos informados"""
    
    TIPO_PROCEDIMIENTO_CHOICES = (
        ('extraccion', 'Extracción Dental'),
        ('endodoncia', 'Endodoncia'),
        ('implante', 'Implante Dental'),
        ('ortodoncia', 'Ortodoncia'),
        ('blanqueamiento', 'Blanqueamiento Dental'),
        ('cirugia', 'Cirugía Oral'),
        ('protesis', 'Prótesis Dental'),
        ('periodoncia', 'Periodoncia'),
        ('restauracion', 'Restauración'),
        ('limpieza', 'Limpieza Dental'),
        ('otro', 'Otro Procedimiento'),
    )
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Plantilla")
    tipo_procedimiento = models.CharField(
        max_length=30,
        choices=TIPO_PROCEDIMIENTO_CHOICES,
        verbose_name="Tipo de Procedimiento"
    )
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    
    # Contenido de la plantilla (estructura según Ley 20.584)
    diagnostico_base = models.TextField(
        blank=True,
        null=True,
        verbose_name="Diagnóstico Base",
        help_text="Texto base para diagnóstico y justificación"
    )
    naturaleza_procedimiento = models.TextField(
        blank=True,
        null=True,
        verbose_name="Naturaleza del Procedimiento",
        help_text="Descripción del procedimiento"
    )
    objetivos_tratamiento = models.TextField(
        blank=True,
        null=True,
        verbose_name="Objetivos del Tratamiento",
        help_text="Objetivos principales"
    )
    contenido = models.TextField(
        verbose_name="Contenido del Consentimiento",
        help_text="Texto del consentimiento. Puede usar variables como {nombre_paciente}, {fecha}, {dentista}, etc."
    )
    
    # Información de riesgos y beneficios
    riesgos = models.TextField(
        blank=True,
        null=True,
        verbose_name="Riesgos y Complicaciones",
        help_text="Lista exhaustiva de riesgos comunes y graves"
    )
    beneficios = models.TextField(
        blank=True,
        null=True,
        verbose_name="Beneficios Esperados",
        help_text="Beneficios del procedimiento"
    )
    alternativas = models.TextField(
        blank=True,
        null=True,
        verbose_name="Alternativas de Tratamiento",
        help_text="Opciones alternativas, incluyendo exodoncia y consecuencias de no tratar"
    )
    pronostico = models.TextField(
        blank=True,
        null=True,
        verbose_name="Pronóstico",
        help_text="Tasa de éxito esperada y necesidad de controles"
    )
    cuidados_postoperatorios = models.TextField(
        blank=True,
        null=True,
        verbose_name="Cuidados Postoperatorios",
        help_text="Indicaciones inmediatas post-tratamiento"
    )
    
    # Estado
    activo = models.BooleanField(default=True, verbose_name="Plantilla Activa")
    
    # Auditoría
    creado_por = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        related_name='plantillas_consentimiento_creadas',
        verbose_name="Creado por"
    )
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_procedimiento_display()})"
    
    class Meta:
        verbose_name = "Plantilla de Consentimiento"
        verbose_name_plural = "Plantillas de Consentimientos"
        ordering = ['tipo_procedimiento', 'nombre']


class ConsentimientoInformado(models.Model):
    """Consentimientos informados firmados por pacientes"""
    
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente de Firma'),
        ('firmado', 'Firmado'),
        ('rechazado', 'Rechazado'),
        ('vencido', 'Vencido'),
    )
    
    # Relación con cliente
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='consentimientos',
        verbose_name="Cliente"
    )
    
    # Relación con plantilla (opcional - puede ser personalizado)
    plantilla = models.ForeignKey(
        PlantillaConsentimiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consentimientos',
        verbose_name="Plantilla Utilizada"
    )
    
    # Relaciones con otros modelos
    cita = models.ForeignKey(
        'citas.Cita',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consentimientos',
        verbose_name="Cita Asociada"
    )
    plan_tratamiento = models.ForeignKey(
        PlanTratamiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consentimientos',
        verbose_name="Plan de Tratamiento"
    )
    
    # Información del consentimiento
    titulo = models.CharField(max_length=200, verbose_name="Título del Consentimiento")
    tipo_procedimiento = models.CharField(
        max_length=30,
        choices=PlantillaConsentimiento.TIPO_PROCEDIMIENTO_CHOICES,
        verbose_name="Tipo de Procedimiento"
    )
    
    # A. Identificación y Antecedentes (Ley 20.584)
    diagnostico = models.TextField(
        blank=True,
        null=True,
        verbose_name="Diagnóstico",
        help_text="Diagnóstico y justificación del procedimiento"
    )
    justificacion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Justificación del Tratamiento",
        help_text="Razón médica que justifica el procedimiento"
    )
    
    # B. Información Detallada del Procedimiento (Ley 20.584)
    naturaleza_procedimiento = models.TextField(
        blank=True,
        null=True,
        verbose_name="Naturaleza del Procedimiento",
        help_text="Descripción clara de qué es el procedimiento"
    )
    objetivos_tratamiento = models.TextField(
        blank=True,
        null=True,
        verbose_name="Objetivos del Tratamiento",
        help_text="Objetivos principales del tratamiento"
    )
    
    # Contenido personalizado (si no usa plantilla)
    contenido = models.TextField(
        verbose_name="Contenido del Consentimiento",
        help_text="Texto completo del consentimiento"
    )
    riesgos = models.TextField(
        blank=True,
        null=True,
        verbose_name="Riesgos y Complicaciones",
        help_text="Lista exhaustiva de riesgos comunes y graves"
    )
    beneficios = models.TextField(
        blank=True,
        null=True,
        verbose_name="Beneficios Esperados",
        help_text="Beneficios del procedimiento"
    )
    alternativas = models.TextField(
        blank=True,
        null=True,
        verbose_name="Alternativas de Tratamiento",
        help_text="Opciones alternativas, incluyendo exodoncia y consecuencias de no tratar"
    )
    pronostico = models.TextField(
        blank=True,
        null=True,
        verbose_name="Pronóstico",
        help_text="Tasa de éxito esperada y necesidad de controles"
    )
    cuidados_postoperatorios = models.TextField(
        blank=True,
        null=True,
        verbose_name="Cuidados Postoperatorios",
        help_text="Indicaciones inmediatas post-tratamiento"
    )
    
    # Información de firma
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name="Estado"
    )
    fecha_firma = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Firma"
    )
    firma_paciente = models.TextField(
        blank=True,
        null=True,
        verbose_name="Firma del Paciente",
        help_text="Firma digital del paciente (texto o imagen codificada)"
    )
    nombre_firmante = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nombre del Firmante"
    )
    rut_firmante = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="RUT del Firmante"
    )
    
    # Testigo (opcional, recomendado por Ley 20.584)
    nombre_testigo = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nombre del Testigo"
    )
    rut_testigo = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="RUT del Testigo"
    )
    firma_testigo = models.TextField(
        blank=True,
        null=True,
        verbose_name="Firma del Testigo"
    )
    
    # Declaración de Comprensión (Ley 20.584)
    declaracion_comprension = models.BooleanField(
        default=False,
        verbose_name="Paciente Declara Comprensión",
        help_text="El paciente declara haber sido informado según Ley 20.584"
    )
    derecho_revocacion = models.BooleanField(
        default=False,
        verbose_name="Conoce Derecho de Revocación",
        help_text="El paciente conoce su derecho a revocar el consentimiento"
    )
    
    # Información del profesional (Ley 20.584)
    dentista = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        related_name='consentimientos_creados',
        limit_choices_to={'rol': 'dentista'},
        verbose_name="Profesional Tratante"
    )
    rut_dentista = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="RUT Profesional Tratante"
    )
    registro_superintendencia = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Registro Superintendencia de Salud",
        help_text="Número de registro del profesional en la Superintendencia de Salud"
    )
    explicado_por = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consentimientos_explicados',
        verbose_name="Profesional Informante"
    )
    rut_explicado_por = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="RUT Profesional Informante"
    )
    
    # Fechas importantes
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Vencimiento",
        help_text="Fecha hasta la cual el consentimiento es válido"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    # Notas adicionales
    notas = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas Adicionales"
    )
    
    # Archivo PDF generado
    archivo_pdf = models.FileField(
        upload_to='consentimientos/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Archivo PDF"
    )
    
    # Información de firma por recepción (según legislación chilena)
    firmado_por_recepcion = models.BooleanField(
        default=False,
        verbose_name="Firmado por Recepción",
        help_text="Indica si el consentimiento fue firmado por recepción con aceptación verbal del paciente"
    )
    recepcionista_firmante = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consentimientos_firmados_recepcion',
        limit_choices_to={'rol': 'administrativo'},
        verbose_name="Recepcionista que Firmó",
        help_text="Recepcionista que firmó el consentimiento en nombre del paciente"
    )
    aceptacion_verbal = models.BooleanField(
        default=False,
        verbose_name="Aceptación Verbal del Paciente",
        help_text="El paciente aceptó verbalmente después de revisar los documentos"
    )
    
    # Documento firmado físicamente (carga de archivo)
    documento_firmado_fisico = models.FileField(
        upload_to='consentimientos/firmados/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Documento Firmado Físicamente",
        help_text="Documento escaneado o fotografiado que demuestra la firma física del paciente (PDF o imagen)"
    )
    subido_por = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consentimientos_subidos',
        verbose_name="Subido por",
        help_text="Personal que subió el documento firmado físicamente"
    )
    fecha_subida = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Subida",
        help_text="Fecha y hora en que se subió el documento firmado"
    )
    
    # Token para firma digital (enlace único para firmar sin autenticación)
    token_firma = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Token de Firma",
        help_text="Token único para permitir la firma del consentimiento sin autenticación"
    )
    fecha_expiracion_token = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Expiración del Token",
        help_text="Fecha hasta la cual el token de firma es válido"
    )
    
    def generar_token_firma(self):
        """Genera un token único para la firma del consentimiento"""
        import uuid
        from django.utils import timezone
        from datetime import timedelta
        
        self.token_firma = uuid.uuid4().hex
        self.fecha_expiracion_token = timezone.now() + timedelta(days=30)  # Válido por 30 días
        self.save(update_fields=['token_firma', 'fecha_expiracion_token'])
        return self.token_firma
    
    def token_es_valido(self):
        """Verifica si el token de firma es válido"""
        if not self.token_firma or not self.fecha_expiracion_token:
            return False
        from django.utils import timezone
        return timezone.now() < self.fecha_expiracion_token and self.estado == 'pendiente'
    
    @property
    def esta_firmado(self):
        """Verifica si el consentimiento está firmado"""
        return self.estado == 'firmado' and self.firma_paciente is not None
    
    @property
    def esta_vencido(self):
        """Verifica si el consentimiento está vencido"""
        if self.fecha_vencimiento:
            return timezone.now().date() > self.fecha_vencimiento
        return False
    
    def __str__(self):
        return f"Consentimiento - {self.cliente.nombre_completo} - {self.titulo}"
    
    class Meta:
        verbose_name = "Consentimiento Informado"
        verbose_name_plural = "Consentimientos Informados"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['cliente', '-fecha_creacion']),
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['tipo_procedimiento']),
            models.Index(fields=['-fecha_creacion']),
        ]
