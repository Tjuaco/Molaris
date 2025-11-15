from django.contrib import admin
from .models import Odontograma, EstadoDiente, Radiografia, InsumoOdontograma


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
