"""
Modelos para acceder a las tablas de servicios del sistema de gestión.
"""
from django.db import models

class TipoServicio(models.Model):
    """
    Modelo para acceder a la tabla citas_tiposervicio del sistema de gestión.
    Contiene los tipos de servicios disponibles con sus precios.
    """
    class Meta:
        db_table = 'citas_tiposervicio'
        managed = False  # Django no creará ni eliminará la tabla
        ordering = ['nombre']
    
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(default=True)
    requiere_dentista = models.BooleanField(default=True)
    duracion_estimada = models.IntegerField(blank=True, null=True)  # En minutos
    creado_el = models.DateTimeField(blank=True, null=True)
    actualizado_el = models.DateTimeField(blank=True, null=True)
    creado_por_id = models.BigIntegerField(blank=True, null=True)
    
    def __str__(self):
        precio = f"${self.precio_base:,.0f}" if self.precio_base else "Sin precio"
        return f"{self.nombre} - {precio}"
    
    def get_precio_formateado(self):
        """Retorna el precio formateado como string"""
        if self.precio_base:
            return f"${self.precio_base:,.0f}"
        return "Consultar precio"




