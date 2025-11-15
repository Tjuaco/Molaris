from django.contrib import admin
from .models import Insumo, MovimientoInsumo


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'cantidad_actual', 'cantidad_minima', 'estado', 'proveedor_principal', 'creado_el']
    list_filter = ['categoria', 'estado', 'proveedor_principal', 'creado_el']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['creado_el', 'actualizado_el']


@admin.register(MovimientoInsumo)
class MovimientoInsumoAdmin(admin.ModelAdmin):
    list_display = ['insumo', 'tipo', 'cantidad', 'cantidad_anterior', 'cantidad_nueva', 'realizado_por', 'fecha_movimiento']
    list_filter = ['tipo', 'fecha_movimiento', 'realizado_por']
    search_fields = ['insumo__nombre', 'motivo']
    readonly_fields = ['fecha_movimiento']
    date_hierarchy = 'fecha_movimiento'
