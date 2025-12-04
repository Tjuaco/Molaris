from django.contrib import admin
from .models import (
    Odontograma, EstadoDiente, Radiografia, InsumoOdontograma,
    PlanTratamiento, FaseTratamiento, ItemTratamiento
)


@admin.register(Odontograma)
class OdontogramaAdmin(admin.ModelAdmin):
    list_display = ['paciente_nombre', 'paciente_email', 'dentista', 'fecha_creacion', 'estado_general', 'higiene_oral']
    list_filter = ['dentista', 'fecha_creacion', 'estado_general', 'higiene_oral']
    search_fields = ['paciente_nombre', 'paciente_email']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    date_hierarchy = 'fecha_creacion'


@admin.register(EstadoDiente)
class EstadoDienteAdmin(admin.ModelAdmin):
    list_display = ['odontograma', 'numero_diente', 'estado', 'fecha_tratamiento']
    list_filter = ['estado', 'fecha_tratamiento']
    search_fields = ['odontograma__paciente_nombre']


@admin.register(Radiografia)
class RadiografiaAdmin(admin.ModelAdmin):
    list_display = ['paciente_nombre', 'paciente_email', 'tipo', 'dentista', 'fecha_carga', 'fecha_tomada']
    list_filter = ['tipo', 'dentista', 'fecha_carga']
    search_fields = ['paciente_nombre', 'paciente_email']
    readonly_fields = ['fecha_carga', 'fecha_actualizacion']
    date_hierarchy = 'fecha_carga'


@admin.register(InsumoOdontograma)
class InsumoOdontogramaAdmin(admin.ModelAdmin):
    list_display = ['odontograma', 'insumo', 'cantidad_utilizada', 'fecha_uso']
    list_filter = ['fecha_uso']
    search_fields = ['odontograma__paciente_nombre', 'insumo__nombre']
    readonly_fields = ['fecha_uso']
    date_hierarchy = 'fecha_uso'


@admin.register(PlanTratamiento)
class PlanTratamientoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'cliente', 'dentista', 'estado', 'precio_final', 'creado_el']
    list_filter = ['estado', 'dentista', 'creado_el']
    search_fields = ['nombre', 'cliente__nombre_completo', 'cliente__email']
    readonly_fields = ['creado_el', 'actualizado_el', 'fecha_aprobacion', 'fecha_completado', 'fecha_cancelacion']
    date_hierarchy = 'creado_el'


@admin.register(FaseTratamiento)
class FaseTratamientoAdmin(admin.ModelAdmin):
    list_display = ['plan', 'nombre', 'orden', 'presupuesto', 'completada']
    list_filter = ['completada', 'plan']
    search_fields = ['plan__nombre', 'nombre']


@admin.register(ItemTratamiento)
class ItemTratamientoAdmin(admin.ModelAdmin):
    list_display = ['fase', 'descripcion', 'cantidad', 'precio_unitario', 'precio_total', 'completado']
    list_filter = ['completado', 'fase__plan']
    search_fields = ['descripcion', 'fase__nombre']
