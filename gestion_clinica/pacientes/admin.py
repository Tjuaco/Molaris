from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'email', 'rut', 'telefono', 'activo', 'dentista_asignado', 'fecha_registro']
    list_filter = ['activo', 'dentista_asignado', 'fecha_registro']
    search_fields = ['nombre_completo', 'email', 'rut', 'telefono']
    readonly_fields = ['fecha_registro']
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre_completo', 'email', 'rut', 'telefono', 'fecha_nacimiento')
        }),
        ('Información Médica', {
            'fields': ('alergias',)
        }),
        ('Asignación', {
            'fields': ('dentista_asignado',)
        }),
        ('Información Adicional', {
            'fields': ('notas', 'activo', 'fecha_registro')
        }),
    )
