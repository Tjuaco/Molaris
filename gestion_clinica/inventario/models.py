from django.db import models
from personal.models import Perfil
from datetime import date, timedelta


class Insumo(models.Model):
    CATEGORIA_CHOICES = (
        ('materiales', 'Materiales Dentales'),
        ('instrumentos', 'Instrumentos'),
        ('medicamentos', 'Medicamentos'),
        ('equipos', 'Equipos'),
        ('consumibles', 'Consumibles'),
        ('otros', 'Otros'),
    )
    
    ESTADO_CHOICES = (
        ('disponible', 'Disponible'),
        ('agotado', 'Agotado'),
        ('vencido', 'Vencido'),
        ('mantenimiento', 'En Mantenimiento'),
    )
    
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to='insumos/imagenes/', null=True, blank=True, verbose_name="Imagen del Insumo")
    cantidad_actual = models.PositiveIntegerField(default=0)
    cantidad_minima = models.PositiveIntegerField(default=1)
    unidad_medida = models.CharField(max_length=50, default='unidad')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proveedor_principal = models.ForeignKey('proveedores.Proveedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='insumos_principales', verbose_name="Proveedor Principal")
    proveedor_texto = models.CharField(max_length=200, blank=True, null=True, verbose_name="Proveedor (Texto Legacy)")
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    
    # Campos de auditoría
    creado_el = models.DateTimeField(auto_now_add=True)
    actualizado_el = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='insumos_creados')
    
    @property
    def stock_bajo(self):
        """Indica si el stock está por debajo del mínimo"""
        return self.cantidad_actual <= self.cantidad_minima
    
    @property
    def proximo_vencimiento(self):
        """Indica si está próximo a vencer (30 días)"""
        if self.fecha_vencimiento:
            return self.fecha_vencimiento <= date.today() + timedelta(days=30)
        return False
    
    def __str__(self):
        return f"{self.nombre} ({self.cantidad_actual} {self.unidad_medida})"
    
    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre']


# Movimientos de stock (entradas y salidas)
class MovimientoInsumo(models.Model):
    TIPO_CHOICES = (
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    )
    
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.PositiveIntegerField()
    cantidad_anterior = models.PositiveIntegerField()
    cantidad_nueva = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200)
    observaciones = models.TextField(blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    realizado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.insumo.nombre} ({self.cantidad})"
    
    class Meta:
        verbose_name = "Movimiento de Insumo"
        verbose_name_plural = "Movimientos de Insumos"
        ordering = ['-fecha_movimiento']
