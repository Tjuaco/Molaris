from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from datetime import date
from personal.models import Perfil
from .models_auditoria import AuditoriaLog


@login_required
def gestor_auditoria(request):
    """Vista para gestionar el historial de auditoría del sistema"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden acceder a la auditoría.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    # Obtener parámetros de filtro
    modulo_filtro = request.GET.get('modulo', '')
    accion_filtro = request.GET.get('accion', '')
    usuario_filtro = request.GET.get('usuario', '')
    buscar = request.GET.get('buscar', '')
    
    # Obtener todos los registros de auditoría (incluyendo dentistas y administrativos)
    # No filtramos por rol, mostramos todos los registros
    registros = AuditoriaLog.objects.all().select_related('usuario').order_by('-fecha_hora')
    
    # Aplicar filtros
    if modulo_filtro:
        registros = registros.filter(modulo=modulo_filtro)
    
    if accion_filtro:
        registros = registros.filter(accion=accion_filtro)
    
    if usuario_filtro:
        registros = registros.filter(usuario_id=usuario_filtro)
    
    if buscar:
        registros = registros.filter(
            Q(descripcion__icontains=buscar) |
            Q(detalles__icontains=buscar) |
            Q(tipo_objeto__icontains=buscar)
        )
    
    # Estadísticas
    total_registros = AuditoriaLog.objects.count()
    registros_hoy = AuditoriaLog.objects.filter(fecha_hora__date=timezone.now().date()).count()
    registros_semana = AuditoriaLog.objects.filter(
        fecha_hora__date__gte=timezone.now().date().replace(day=1)
    ).count()
    
    # Contar por módulo
    registros_por_modulo = {}
    for modulo_val, modulo_nombre in AuditoriaLog.MODULO_CHOICES:
        registros_por_modulo[modulo_val] = AuditoriaLog.objects.filter(modulo=modulo_val).count()
    
    # Contar por acción
    registros_por_accion = {}
    for accion_val, accion_nombre in AuditoriaLog.ACCION_CHOICES:
        registros_por_accion[accion_val] = AuditoriaLog.objects.filter(accion=accion_val).count()
    
    # Paginación
    paginator = Paginator(registros, 50)
    page = request.GET.get('page', 1)
    try:
        registros_pag = paginator.page(page)
    except PageNotAnInteger:
        registros_pag = paginator.page(1)
    except EmptyPage:
        registros_pag = paginator.page(paginator.num_pages)
    
    # Obtener usuarios para el filtro
    usuarios = Perfil.objects.filter(
        user__is_active=True
    ).order_by('nombre_completo')[:100]
    
    context = {
        'perfil': perfil,
        'registros': registros_pag,
        'modulos': AuditoriaLog.MODULO_CHOICES,
        'acciones': AuditoriaLog.ACCION_CHOICES,
        'usuarios': usuarios,
        'modulo_filtro': modulo_filtro,
        'accion_filtro': accion_filtro,
        'usuario_filtro': usuario_filtro,
        'buscar': buscar,
        'total_registros': total_registros,
        'registros_hoy': registros_hoy,
        'registros_semana': registros_semana,
        'registros_por_modulo': registros_por_modulo,
        'registros_por_accion': registros_por_accion,
    }
    
    return render(request, 'citas/auditoria/auditoria.html', context)

