from django.contrib import admin
from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'email', 'rol', 'activo', 'requiere_acceso_sistema', 'fecha_registro']
    list_filter = ['rol', 'activo', 'requiere_acceso_sistema', 'fecha_registro']
    search_fields = ['nombre_completo', 'email', 'telefono']
    readonly_fields = ['fecha_registro']
    fieldsets = (
        ('Información Personal', {
            'fields': ('user', 'nombre_completo', 'email', 'telefono', 'foto', 'rol')
        }),
        ('Acceso al Sistema', {
            'fields': ('requiere_acceso_sistema',)
        }),
        ('Información Profesional (Dentistas)', {
            'fields': ('especialidad', 'numero_colegio'),
            'classes': ('collapse',)
        }),
        ('Permisos', {
            'fields': (
                'puede_gestionar_citas',
                'puede_gestionar_clientes',
                'puede_gestionar_insumos',
                'puede_gestionar_personal',
                'puede_ver_reportes',
                'puede_crear_odontogramas',
            )
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_registro')
        }),
    )
