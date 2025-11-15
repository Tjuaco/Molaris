from django.db import models
from personal.models import Perfil


class IngresoManual(models.Model):
    """Registro manual de ingresos en finanzas"""
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    descripcion = models.CharField(max_length=200, verbose_name="Descripción")
    fecha = models.DateField(verbose_name="Fecha")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    creado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingresos_manuales_creados')
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    
    def __str__(self):
        return f"Ingreso Manual - ${self.monto} - {self.fecha}"
    
    class Meta:
        verbose_name = "Ingreso Manual"
        verbose_name_plural = "Ingresos Manuales"
        ordering = ['-fecha', '-creado_el']


class EgresoManual(models.Model):
    """Registro manual de egresos en finanzas"""
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    descripcion = models.CharField(max_length=200, verbose_name="Descripción")
    fecha = models.DateField(verbose_name="Fecha")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    creado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='egresos_manuales_creados')
    creado_el = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    
    def __str__(self):
        return f"Egreso Manual - ${self.monto} - {self.fecha}"
    
    class Meta:
        verbose_name = "Egreso Manual"
        verbose_name_plural = "Egresos Manuales"
        ordering = ['-fecha', '-creado_el']
