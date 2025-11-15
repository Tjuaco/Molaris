from django.contrib import admin
from .models import Cita, Evaluacion


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['fecha_hora', 'estado', 'paciente_nombre', 'paciente_email', 'tipo_consulta', 'dentista']
    list_filter = ['estado', 'tipo_consulta', 'fecha_hora']
    search_fields = ['paciente_nombre', 'paciente_email', 'paciente_telefono']
    date_hierarchy = 'fecha_hora'
    readonly_fields = ['creada_el', 'actualizada_el']
    
    fieldsets = (
        ('Información de la Cita', {
            'fields': ('fecha_hora', 'tipo_consulta', 'estado', 'dentista')
        }),
        ('Información del Paciente', {
            'fields': ('paciente_nombre', 'paciente_email', 'paciente_telefono')
        }),
        ('Información Adicional', {
            'fields': ('notas', 'whatsapp_message_sid', 'creada_por', 'creada_el', 'actualizada_el')
        }),
    )


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = ['email_cliente', 'estrellas', 'estado', 'creada_el', 'get_usuario']
    list_filter = ['estado', 'estrellas', 'creada_el']
    search_fields = ['email_cliente', 'comentario', 'user__username']
    readonly_fields = ['creada_el', 'actualizada_el', 'ip_address']
    date_hierarchy = 'creada_el'
    
    fieldsets = (
        ('Información de la Evaluación', {
            'fields': ('user', 'email_cliente', 'estrellas', 'comentario')
        }),
        ('Estado de Envío', {
            'fields': ('estado', 'error_mensaje')
        }),
        ('Información Técnica', {
            'fields': ('ip_address', 'creada_el', 'actualizada_el'),
            'classes': ('collapse',)
        }),
    )
    
    def get_usuario(self, obj):
        return obj.user.username
    get_usuario.short_description = 'Usuario'
    get_usuario.admin_order_field = 'user__username'
    
    actions = ['marcar_como_enviada', 'reintentar_envio']
    
    def marcar_como_enviada(self, request, queryset):
        count = queryset.update(estado='enviada', error_mensaje=None)
        self.message_user(request, f'{count} evaluaciones marcadas como enviadas.')
    marcar_como_enviada.short_description = 'Marcar como enviada'
    
    def reintentar_envio(self, request, queryset):
        from .api_service import enviar_evaluacion_a_gestion
        
        enviadas = 0
        errores = 0
        
        for evaluacion in queryset:
            success, message = enviar_evaluacion_a_gestion(evaluacion)
            if success:
                evaluacion.estado = 'enviada'
                evaluacion.error_mensaje = None
                evaluacion.save()
                enviadas += 1
            else:
                evaluacion.estado = 'error'
                evaluacion.error_mensaje = message
                evaluacion.save()
                errores += 1
        
        self.message_user(request, f'Enviadas: {enviadas}, Errores: {errores}')
    reintentar_envio.short_description = 'Reintentar envío al sistema de gestión'
