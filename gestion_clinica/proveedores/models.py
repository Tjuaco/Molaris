from django.db import models
from personal.models import Perfil


class Proveedor(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Proveedor")
    rut = models.CharField(max_length=20, unique=True, verbose_name="RUT/NIT")
    email = models.EmailField(verbose_name="Email de Contacto")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    contacto_nombre = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nombre del Contacto")
    sitio_web = models.URLField(blank=True, null=True, verbose_name="Sitio Web")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    # Campos de auditoría
    creado_el = models.DateTimeField(auto_now_add=True)
    actualizado_el = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='proveedores_creados')
    
    def __str__(self):
        return f"{self.nombre} - {self.rut}"
    
    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']


# Solicitudes de insumos a proveedores
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    correo_enviado = models.BooleanField(default=False, verbose_name="Correo Enviado")
    fecha_envio_correo = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío del Correo")
    registrar_como_egreso = models.BooleanField(default=False, verbose_name="Registrar como Egreso en Finanzas")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']
