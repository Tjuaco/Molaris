from django.contrib import admin
from .models import IngresoManual, EgresoManual


@admin.register(IngresoManual)
class IngresoManualAdmin(admin.ModelAdmin):
    list_display = ['monto', 'descripcion', 'fecha', 'creado_por', 'creado_el']
    list_filter = ['fecha', 'creado_por', 'creado_el']
    search_fields = ['descripcion', 'notas']
    readonly_fields = ['creado_el']
    date_hierarchy = 'fecha'


@admin.register(EgresoManual)
class EgresoManualAdmin(admin.ModelAdmin):
    list_display = ['monto', 'descripcion', 'fecha', 'creado_por', 'creado_el']
    list_filter = ['fecha', 'creado_por', 'creado_el']
    search_fields = ['descripcion', 'notas']
    readonly_fields = ['creado_el']
    date_hierarchy = 'fecha'
