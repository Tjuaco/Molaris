from django.contrib import admin
from .models import Cita, TipoServicio


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['fecha_hora', 'estado', 'nombre_paciente', 'email_paciente', 'dentista', 'tipo_servicio', 'precio_cobrado']
    list_filter = ['estado', 'dentista', 'tipo_servicio', 'creada_el']
    search_fields = ['paciente_nombre', 'paciente_email', 'paciente_telefono']
    readonly_fields = ['creada_el', 'actualizada_el']
    date_hierarchy = 'fecha_hora'


@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'precio_base', 'activo', 'creado_el']
    list_filter = ['categoria', 'activo', 'creado_el']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['creado_el', 'actualizado_el']
