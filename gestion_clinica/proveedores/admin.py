from django.contrib import admin
from .models import Proveedor, SolicitudInsumo


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'rut', 'email', 'telefono', 'activo', 'creado_el']
    list_filter = ['activo', 'creado_el']
    search_fields = ['nombre', 'rut', 'email', 'telefono']
    readonly_fields = ['creado_el', 'actualizado_el']


@admin.register(SolicitudInsumo)
class SolicitudInsumoAdmin(admin.ModelAdmin):
    list_display = ['proveedor', 'insumo', 'cantidad_solicitada', 'estado', 'fecha_solicitud', 'fecha_entrega_esperada', 'solicitado_por']
    list_filter = ['estado', 'fecha_solicitud', 'proveedor']
    search_fields = ['proveedor__nombre', 'insumo__nombre']
    readonly_fields = ['fecha_solicitud']
    date_hierarchy = 'fecha_solicitud'
