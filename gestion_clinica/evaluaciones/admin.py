from django.contrib import admin
from .models import Evaluacion


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'email_cliente', 'estrellas', 'estado', 'fecha_creacion', 'revisada_por']
    list_filter = ['estado', 'estrellas', 'fecha_creacion', 'revisada_por']
    search_fields = ['cliente__nombre_completo', 'email_cliente', 'comentario']
    readonly_fields = ['fecha_creacion', 'fecha_revision']
    date_hierarchy = 'fecha_creacion'
