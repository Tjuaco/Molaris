from django.db import models
from django.core.validators import RegexValidator
from personal.models import Perfil


# Información de Contacto de la Clínica
class InformacionClinica(models.Model):
    """
    Modelo singleton para almacenar la información de contacto de la clínica.
    Solo debe existir una instancia de este modelo.
    """
    nombre_clinica = models.CharField(max_length=200, default="Clínica Dental", verbose_name="Nombre de la Clínica")
    direccion = models.TextField(verbose_name="Dirección")
    telefono = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='El número de teléfono debe estar en formato: +999999999. Hasta 15 dígitos permitidos.'
            )
        ],
        verbose_name="Teléfono Principal"
    )
    telefono_secundario = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='El número de teléfono debe estar en formato: +999999999. Hasta 15 dígitos permitidos.'
            )
        ],
        verbose_name="Teléfono Secundario"
    )
    email = models.EmailField(verbose_name="Email de Contacto")
    email_alternativo = models.EmailField(blank=True, null=True, verbose_name="Email Alternativo")
    horario_atencion = models.TextField(
        default="Lunes a Viernes: 9:00 - 18:00\nSábados: 9:00 - 13:00",
        verbose_name="Horario de Atención"
    )
    sitio_web = models.URLField(blank=True, null=True, verbose_name="Sitio Web")
    whatsapp = models.CharField(max_length=20, blank=True, null=True, verbose_name="WhatsApp")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook")
    instagram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Instagram")
    notas_adicionales = models.TextField(blank=True, null=True, verbose_name="Notas Adicionales")
    
    # Campos de auditoría
    actualizado_el = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    actualizado_por = models.ForeignKey(
        Perfil, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='actualizaciones_info_clinica',
        verbose_name="Actualizado Por"
    )
    
    def save(self, *args, **kwargs):
        """Asegura que solo exista una instancia de este modelo"""
        if not self.pk and InformacionClinica.objects.exists():
            # Si ya existe una instancia, actualízala en lugar de crear una nueva
            instance = InformacionClinica.objects.first()
            self.pk = instance.pk
        super().save(*args, **kwargs)
    
    @classmethod
    def obtener(cls):
        """Obtiene o crea la única instancia de información de la clínica"""
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'nombre_clinica': 'Clínica Dental',
                'direccion': 'Ingrese la dirección de la clínica',
                'telefono': '+56912345678',
                'email': 'contacto@clinica.com',
                'horario_atencion': 'Lunes a Viernes: 9:00 - 18:00\nSábados: 9:00 - 13:00',
            }
        )
        return obj
    
    def __str__(self):
        return f"Información de Contacto - {self.nombre_clinica}"
    
    class Meta:
        verbose_name = "Información de la Clínica"
        verbose_name_plural = "Información de la Clínica"
