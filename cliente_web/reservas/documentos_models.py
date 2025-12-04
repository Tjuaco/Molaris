# reservas/documentos_models.py
"""
Modelos para acceder a las tablas de documentos del sistema de gestión.
Estos modelos están mapeados a tablas existentes en la base de datos.
"""
from django.db import models
from django.contrib.auth.models import User

class ClienteDocumento(models.Model):
    """
    Modelo para acceder a la tabla pacientes_cliente del sistema de gestión.
    Se usa para relacionar usuarios del sistema cliente con sus documentos.
    NOTA: Actualizado para usar pacientes_cliente en lugar de citas_cliente
    """
    class Meta:
        db_table = 'pacientes_cliente'  # CORREGIDO: usar pacientes_cliente en lugar de citas_cliente
        managed = False  # Django no creará ni eliminará la tabla
    
    id = models.BigAutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField(max_length=254)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    
    # Campos nuevos agregados al sistema de gestión
    rut = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        verbose_name="RUT",
        help_text="RUT en formato: 12345678-9 (opcional pero recomendado)"
    )
    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Nacimiento",
        help_text="Fecha de nacimiento del paciente"
    )
    alergias = models.TextField(
        blank=True,
        null=True,
        verbose_name="Alergias",
        help_text="Lista de alergias conocidas (medicamentos, materiales dentales, anestesia, etc.). MUY IMPORTANTE para la seguridad del paciente."
    )
    
    fecha_registro = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    dentista_asignado_id = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre_completo} ({self.email})"


class Odontograma(models.Model):
    """
    Modelo para acceder a la tabla historial_clinico_odontograma.
    Contiene las fichas odontológicas/odontogramas de los pacientes en PDF.
    NOTA: Actualizado para usar historial_clinico_odontograma en lugar de citas_odontograma
    """
    class Meta:
        db_table = 'historial_clinico_odontograma'  # CORREGIDO: usar historial_clinico_odontograma
        managed = False
        ordering = ['-fecha_creacion']
    
    id = models.BigAutoField(primary_key=True)
    paciente_nombre = models.CharField(max_length=150, blank=True, null=True)
    paciente_email = models.EmailField(max_length=254, blank=True, null=True)
    paciente_telefono = models.CharField(max_length=20, blank=True, null=True)
    paciente_fecha_nacimiento = models.DateField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(blank=True, null=True)
    motivo_consulta = models.TextField(blank=True, null=True)
    antecedentes_medicos = models.TextField(blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    medicamentos_actuales = models.TextField(blank=True, null=True)
    higiene_oral = models.CharField(max_length=20, blank=True, null=True)
    estado_general = models.CharField(max_length=20, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    plan_tratamiento = models.TextField(blank=True, null=True)
    proxima_cita = models.DateTimeField(blank=True, null=True)
    dentista_id = models.BigIntegerField(blank=True, null=True)
    cliente_id = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Odontograma de {self.paciente_nombre or self.paciente_email} - {self.fecha_creacion}"


class Radiografia(models.Model):
    """
    Modelo para acceder a la tabla historial_clinico_radiografia.
    Contiene las radiografías de los pacientes.
    NOTA: Actualizado para usar historial_clinico_radiografia en lugar de citas_radiografia
    """
    class Meta:
        db_table = 'historial_clinico_radiografia'  # CORREGIDO: usar historial_clinico_radiografia
        managed = False
        ordering = ['-fecha_carga']
    
    TIPO_CHOICES = [
        ('panoramica', 'Panorámica'),
        ('periapical', 'Periapical'),
        ('oclusal', 'Oclusal'),
        ('interproximal', 'Interproximal'),
        ('lateral', 'Lateral'),
        ('frontal', 'Frontal'),
        ('otra', 'Otra'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    paciente_email = models.EmailField(max_length=254, blank=True, null=True)
    paciente_nombre = models.CharField(max_length=150, blank=True, null=True)
    tipo = models.CharField(max_length=20, blank=True, null=True)
    imagen = models.CharField(max_length=100, blank=True, null=True)  # Ruta al archivo
    descripcion = models.TextField(blank=True, null=True)
    fecha_tomada = models.DateField(blank=True, null=True)
    fecha_carga = models.DateTimeField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(blank=True, null=True)
    dentista_id = models.BigIntegerField(blank=True, null=True)
    cliente_id = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        tipo_display = dict(self.TIPO_CHOICES).get(self.tipo, self.tipo or 'Sin tipo')
        return f"Radiografía {tipo_display} - {self.paciente_nombre or self.paciente_email}"
    
    def get_tipo_display_value(self):
        """Retorna el tipo de radiografía formateado"""
        return dict(self.TIPO_CHOICES).get(self.tipo, self.tipo or 'Sin tipo')


class InformacionClinica(models.Model):
    """
    Modelo para acceder a la tabla configuracion_informacionclinica del sistema de gestión.
    """
    class Meta:
        db_table = 'configuracion_informacionclinica'
        managed = False
        ordering = ['-actualizado_el']
    
    id = models.BigAutoField(primary_key=True)
    nombre_clinica = models.CharField(max_length=200, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    telefono_secundario = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    email_alternativo = models.EmailField(blank=True, null=True)
    horario_atencion = models.TextField(blank=True, null=True)
    sitio_web = models.URLField(blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    instagram = models.CharField(max_length=100, blank=True, null=True)
    notas_adicionales = models.TextField(blank=True, null=True)
    actualizado_el = models.DateTimeField(blank=True, null=True)
    actualizado_por_id = models.BigIntegerField(blank=True, null=True)



