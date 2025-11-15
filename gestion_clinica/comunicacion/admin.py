from django.contrib import admin
from .models import Mensaje


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ['remitente', 'destinatario', 'asunto', 'tipo', 'estado', 'fecha_envio']
    list_filter = ['tipo', 'estado', 'fecha_envio']
    search_fields = ['asunto', 'mensaje', 'remitente__nombre_completo', 'destinatario__nombre_completo']
    readonly_fields = ['fecha_envio', 'fecha_lectura']
    date_hierarchy = 'fecha_envio'
