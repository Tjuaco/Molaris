from django.contrib import admin
from .models import InformacionClinica


@admin.register(InformacionClinica)
class InformacionClinicaAdmin(admin.ModelAdmin):
    list_display = ['nombre_clinica', 'telefono', 'email', 'actualizado_el', 'actualizado_por']
    readonly_fields = ['actualizado_el']
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre_clinica', 'direccion')
        }),
        ('Contacto', {
            'fields': ('telefono', 'telefono_secundario', 'email', 'email_alternativo', 'whatsapp')
        }),
        ('Redes Sociales', {
            'fields': ('sitio_web', 'facebook', 'instagram')
        }),
        ('Horarios', {
            'fields': ('horario_atencion',)
        }),
        ('Información Adicional', {
            'fields': ('notas_adicionales',)
        }),
        ('Auditoría', {
            'fields': ('actualizado_el', 'actualizado_por')
        }),
    )
