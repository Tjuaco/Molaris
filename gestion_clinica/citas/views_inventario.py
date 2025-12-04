from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta, date
from inventario.models import Insumo
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from personal.models import Perfil


@login_required
def gestor_inventario_unificado(request):
    """Vista unificada para gestionar insumos y proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar inventario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Sección activa (por defecto insumos)
    seccion = request.GET.get('seccion', 'insumos')
    
    # ========== DATOS PARA INSUMOS ==========
    search_insumos = request.GET.get('search_insumos', '')
    categoria = request.GET.get('categoria', '')
    estado_insumo = request.GET.get('estado_insumo', '')
    
    insumos = Insumo.objects.all()
    
    if search_insumos:
        insumos = insumos.filter(
            Q(nombre__icontains=search_insumos) |
            Q(descripcion__icontains=search_insumos) |
            Q(proveedor_principal__nombre__icontains=search_insumos) |
            Q(proveedor_texto__icontains=search_insumos) |
            Q(ubicacion__icontains=search_insumos)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado_insumo:
        insumos = insumos.filter(estado=estado_insumo)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación de insumos
    paginator_insumos = Paginator(insumos_list, 10)
    page_insumos = request.GET.get('page_insumos', 1)
    
    try:
        insumos_pag = paginator_insumos.page(page_insumos)
    except PageNotAnInteger:
        insumos_pag = paginator_insumos.page(1)
    except EmptyPage:
        insumos_pag = paginator_insumos.page(paginator_insumos.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas_insumos = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    # ========== DATOS PARA PROVEEDORES ==========
    search_proveedores = request.GET.get('search_proveedores', '')
    estado_proveedor = request.GET.get('estado_proveedor', '')
    
    proveedores = Proveedor.objects.all()
    
    if search_proveedores:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search_proveedores) |
            Q(rut__icontains=search_proveedores) |
            Q(email__icontains=search_proveedores) |
            Q(telefono__icontains=search_proveedores) |
            Q(contacto_nombre__icontains=search_proveedores)
        )
    
    if estado_proveedor == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado_proveedor == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Estadísticas de proveedores
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas_proveedores = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # ========== DATOS PARA PEDIDOS ==========
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').order_by('-fecha_pedido')[:10]
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas_pedidos = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # ========== DATOS PARA SOLICITUDES ==========
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Obtener proveedores activos para formularios
    proveedores_activos = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'seccion': seccion,
        
        # Insumos
        'insumos': insumos_pag,
        'estadisticas_insumos': estadisticas_insumos,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados_insumo': Insumo.ESTADO_CHOICES,
        'search_insumos': search_insumos,
        'categoria': categoria,
        'estado_insumo': estado_insumo,
        
        # Proveedores
        'proveedores': proveedores,
        'estadisticas_proveedores': estadisticas_proveedores,
        'search_proveedores': search_proveedores,
        'estado_proveedor': estado_proveedor,
        'proveedores_activos': proveedores_activos,
        
        # Pedidos
        'pedidos': pedidos,
        'estadisticas_pedidos': estadisticas_pedidos,
        
        # Solicitudes
        'solicitudes_recientes': solicitudes_recientes,
        
        # Insumos para solicitudes
        'insumos_todos': Insumo.objects.all().order_by('nombre'),
        
        # Fecha actual para comparar vencimientos
        'today': date.today(),
        
        'es_admin': True
    }
    
    return render(request, 'citas/inventario/gestor_inventario_unificado.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from inventario.models import Insumo
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from personal.models import Perfil


@login_required
def gestor_inventario_unificado(request):
    """Vista unificada para gestionar insumos y proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar inventario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Sección activa (por defecto insumos)
    seccion = request.GET.get('seccion', 'insumos')
    
    # ========== DATOS PARA INSUMOS ==========
    search_insumos = request.GET.get('search_insumos', '')
    categoria = request.GET.get('categoria', '')
    estado_insumo = request.GET.get('estado_insumo', '')
    
    insumos = Insumo.objects.all()
    
    if search_insumos:
        insumos = insumos.filter(
            Q(nombre__icontains=search_insumos) |
            Q(descripcion__icontains=search_insumos) |
            Q(proveedor_principal__nombre__icontains=search_insumos) |
            Q(proveedor_texto__icontains=search_insumos) |
            Q(ubicacion__icontains=search_insumos)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado_insumo:
        insumos = insumos.filter(estado=estado_insumo)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación de insumos
    paginator_insumos = Paginator(insumos_list, 10)
    page_insumos = request.GET.get('page_insumos', 1)
    
    try:
        insumos_pag = paginator_insumos.page(page_insumos)
    except PageNotAnInteger:
        insumos_pag = paginator_insumos.page(1)
    except EmptyPage:
        insumos_pag = paginator_insumos.page(paginator_insumos.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas_insumos = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    # ========== DATOS PARA PROVEEDORES ==========
    search_proveedores = request.GET.get('search_proveedores', '')
    estado_proveedor = request.GET.get('estado_proveedor', '')
    
    proveedores = Proveedor.objects.all()
    
    if search_proveedores:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search_proveedores) |
            Q(rut__icontains=search_proveedores) |
            Q(email__icontains=search_proveedores) |
            Q(telefono__icontains=search_proveedores) |
            Q(contacto_nombre__icontains=search_proveedores)
        )
    
    if estado_proveedor == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado_proveedor == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Estadísticas de proveedores
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas_proveedores = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # ========== DATOS PARA PEDIDOS ==========
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').order_by('-fecha_pedido')[:10]
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas_pedidos = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # ========== DATOS PARA SOLICITUDES ==========
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Obtener proveedores activos para formularios
    proveedores_activos = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'seccion': seccion,
        
        # Insumos
        'insumos': insumos_pag,
        'estadisticas_insumos': estadisticas_insumos,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados_insumo': Insumo.ESTADO_CHOICES,
        'search_insumos': search_insumos,
        'categoria': categoria,
        'estado_insumo': estado_insumo,
        
        # Proveedores
        'proveedores': proveedores,
        'estadisticas_proveedores': estadisticas_proveedores,
        'search_proveedores': search_proveedores,
        'estado_proveedor': estado_proveedor,
        'proveedores_activos': proveedores_activos,
        
        # Pedidos
        'pedidos': pedidos,
        'estadisticas_pedidos': estadisticas_pedidos,
        
        # Solicitudes
        'solicitudes_recientes': solicitudes_recientes,
        
        # Insumos para solicitudes
        'insumos_todos': Insumo.objects.all().order_by('nombre'),
        
        # Fecha actual para comparar vencimientos
        'today': date.today(),
        
        'es_admin': True
    }
    
    return render(request, 'citas/inventario/gestor_inventario_unificado.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from inventario.models import Insumo
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from personal.models import Perfil


@login_required
def gestor_inventario_unificado(request):
    """Vista unificada para gestionar insumos y proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar inventario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Sección activa (por defecto insumos)
    seccion = request.GET.get('seccion', 'insumos')
    
    # ========== DATOS PARA INSUMOS ==========
    search_insumos = request.GET.get('search_insumos', '')
    categoria = request.GET.get('categoria', '')
    estado_insumo = request.GET.get('estado_insumo', '')
    
    insumos = Insumo.objects.all()
    
    if search_insumos:
        insumos = insumos.filter(
            Q(nombre__icontains=search_insumos) |
            Q(descripcion__icontains=search_insumos) |
            Q(proveedor_principal__nombre__icontains=search_insumos) |
            Q(proveedor_texto__icontains=search_insumos) |
            Q(ubicacion__icontains=search_insumos)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado_insumo:
        insumos = insumos.filter(estado=estado_insumo)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación de insumos
    paginator_insumos = Paginator(insumos_list, 10)
    page_insumos = request.GET.get('page_insumos', 1)
    
    try:
        insumos_pag = paginator_insumos.page(page_insumos)
    except PageNotAnInteger:
        insumos_pag = paginator_insumos.page(1)
    except EmptyPage:
        insumos_pag = paginator_insumos.page(paginator_insumos.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas_insumos = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    # ========== DATOS PARA PROVEEDORES ==========
    search_proveedores = request.GET.get('search_proveedores', '')
    estado_proveedor = request.GET.get('estado_proveedor', '')
    
    proveedores = Proveedor.objects.all()
    
    if search_proveedores:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search_proveedores) |
            Q(rut__icontains=search_proveedores) |
            Q(email__icontains=search_proveedores) |
            Q(telefono__icontains=search_proveedores) |
            Q(contacto_nombre__icontains=search_proveedores)
        )
    
    if estado_proveedor == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado_proveedor == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Estadísticas de proveedores
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas_proveedores = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # ========== DATOS PARA PEDIDOS ==========
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').order_by('-fecha_pedido')[:10]
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas_pedidos = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # ========== DATOS PARA SOLICITUDES ==========
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Obtener proveedores activos para formularios
    proveedores_activos = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'seccion': seccion,
        
        # Insumos
        'insumos': insumos_pag,
        'estadisticas_insumos': estadisticas_insumos,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados_insumo': Insumo.ESTADO_CHOICES,
        'search_insumos': search_insumos,
        'categoria': categoria,
        'estado_insumo': estado_insumo,
        
        # Proveedores
        'proveedores': proveedores,
        'estadisticas_proveedores': estadisticas_proveedores,
        'search_proveedores': search_proveedores,
        'estado_proveedor': estado_proveedor,
        'proveedores_activos': proveedores_activos,
        
        # Pedidos
        'pedidos': pedidos,
        'estadisticas_pedidos': estadisticas_pedidos,
        
        # Solicitudes
        'solicitudes_recientes': solicitudes_recientes,
        
        # Insumos para solicitudes
        'insumos_todos': Insumo.objects.all().order_by('nombre'),
        
        # Fecha actual para comparar vencimientos
        'today': date.today(),
        
        'es_admin': True
    }
    
    return render(request, 'citas/inventario/gestor_inventario_unificado.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from inventario.models import Insumo
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from personal.models import Perfil


@login_required
def gestor_inventario_unificado(request):
    """Vista unificada para gestionar insumos y proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar inventario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Sección activa (por defecto insumos)
    seccion = request.GET.get('seccion', 'insumos')
    
    # ========== DATOS PARA INSUMOS ==========
    search_insumos = request.GET.get('search_insumos', '')
    categoria = request.GET.get('categoria', '')
    estado_insumo = request.GET.get('estado_insumo', '')
    
    insumos = Insumo.objects.all()
    
    if search_insumos:
        insumos = insumos.filter(
            Q(nombre__icontains=search_insumos) |
            Q(descripcion__icontains=search_insumos) |
            Q(proveedor_principal__nombre__icontains=search_insumos) |
            Q(proveedor_texto__icontains=search_insumos) |
            Q(ubicacion__icontains=search_insumos)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado_insumo:
        insumos = insumos.filter(estado=estado_insumo)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación de insumos
    paginator_insumos = Paginator(insumos_list, 10)
    page_insumos = request.GET.get('page_insumos', 1)
    
    try:
        insumos_pag = paginator_insumos.page(page_insumos)
    except PageNotAnInteger:
        insumos_pag = paginator_insumos.page(1)
    except EmptyPage:
        insumos_pag = paginator_insumos.page(paginator_insumos.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas_insumos = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    # ========== DATOS PARA PROVEEDORES ==========
    search_proveedores = request.GET.get('search_proveedores', '')
    estado_proveedor = request.GET.get('estado_proveedor', '')
    
    proveedores = Proveedor.objects.all()
    
    if search_proveedores:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search_proveedores) |
            Q(rut__icontains=search_proveedores) |
            Q(email__icontains=search_proveedores) |
            Q(telefono__icontains=search_proveedores) |
            Q(contacto_nombre__icontains=search_proveedores)
        )
    
    if estado_proveedor == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado_proveedor == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Estadísticas de proveedores
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas_proveedores = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # ========== DATOS PARA PEDIDOS ==========
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').order_by('-fecha_pedido')[:10]
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas_pedidos = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # ========== DATOS PARA SOLICITUDES ==========
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Obtener proveedores activos para formularios
    proveedores_activos = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'seccion': seccion,
        
        # Insumos
        'insumos': insumos_pag,
        'estadisticas_insumos': estadisticas_insumos,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados_insumo': Insumo.ESTADO_CHOICES,
        'search_insumos': search_insumos,
        'categoria': categoria,
        'estado_insumo': estado_insumo,
        
        # Proveedores
        'proveedores': proveedores,
        'estadisticas_proveedores': estadisticas_proveedores,
        'search_proveedores': search_proveedores,
        'estado_proveedor': estado_proveedor,
        'proveedores_activos': proveedores_activos,
        
        # Pedidos
        'pedidos': pedidos,
        'estadisticas_pedidos': estadisticas_pedidos,
        
        # Solicitudes
        'solicitudes_recientes': solicitudes_recientes,
        
        # Insumos para solicitudes
        'insumos_todos': Insumo.objects.all().order_by('nombre'),
        
        # Fecha actual para comparar vencimientos
        'today': date.today(),
        
        'es_admin': True
    }
    
    return render(request, 'citas/inventario/gestor_inventario_unificado.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from inventario.models import Insumo
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from personal.models import Perfil


@login_required
def gestor_inventario_unificado(request):
    """Vista unificada para gestionar insumos y proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar inventario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Sección activa (por defecto insumos)
    seccion = request.GET.get('seccion', 'insumos')
    
    # ========== DATOS PARA INSUMOS ==========
    search_insumos = request.GET.get('search_insumos', '')
    categoria = request.GET.get('categoria', '')
    estado_insumo = request.GET.get('estado_insumo', '')
    
    insumos = Insumo.objects.all()
    
    if search_insumos:
        insumos = insumos.filter(
            Q(nombre__icontains=search_insumos) |
            Q(descripcion__icontains=search_insumos) |
            Q(proveedor_principal__nombre__icontains=search_insumos) |
            Q(proveedor_texto__icontains=search_insumos) |
            Q(ubicacion__icontains=search_insumos)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado_insumo:
        insumos = insumos.filter(estado=estado_insumo)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación de insumos
    paginator_insumos = Paginator(insumos_list, 10)
    page_insumos = request.GET.get('page_insumos', 1)
    
    try:
        insumos_pag = paginator_insumos.page(page_insumos)
    except PageNotAnInteger:
        insumos_pag = paginator_insumos.page(1)
    except EmptyPage:
        insumos_pag = paginator_insumos.page(paginator_insumos.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas_insumos = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    # ========== DATOS PARA PROVEEDORES ==========
    search_proveedores = request.GET.get('search_proveedores', '')
    estado_proveedor = request.GET.get('estado_proveedor', '')
    
    proveedores = Proveedor.objects.all()
    
    if search_proveedores:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search_proveedores) |
            Q(rut__icontains=search_proveedores) |
            Q(email__icontains=search_proveedores) |
            Q(telefono__icontains=search_proveedores) |
            Q(contacto_nombre__icontains=search_proveedores)
        )
    
    if estado_proveedor == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado_proveedor == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Estadísticas de proveedores
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas_proveedores = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # ========== DATOS PARA PEDIDOS ==========
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').order_by('-fecha_pedido')[:10]
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas_pedidos = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # ========== DATOS PARA SOLICITUDES ==========
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Obtener proveedores activos para formularios
    proveedores_activos = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'seccion': seccion,
        
        # Insumos
        'insumos': insumos_pag,
        'estadisticas_insumos': estadisticas_insumos,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados_insumo': Insumo.ESTADO_CHOICES,
        'search_insumos': search_insumos,
        'categoria': categoria,
        'estado_insumo': estado_insumo,
        
        # Proveedores
        'proveedores': proveedores,
        'estadisticas_proveedores': estadisticas_proveedores,
        'search_proveedores': search_proveedores,
        'estado_proveedor': estado_proveedor,
        'proveedores_activos': proveedores_activos,
        
        # Pedidos
        'pedidos': pedidos,
        'estadisticas_pedidos': estadisticas_pedidos,
        
        # Solicitudes
        'solicitudes_recientes': solicitudes_recientes,
        
        # Insumos para solicitudes
        'insumos_todos': Insumo.objects.all().order_by('nombre'),
        
        # Fecha actual para comparar vencimientos
        'today': date.today(),
        
        'es_admin': True
    }
    
    return render(request, 'citas/inventario/gestor_inventario_unificado.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from inventario.models import Insumo
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from personal.models import Perfil


@login_required
def gestor_inventario_unificado(request):
    """Vista unificada para gestionar insumos y proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar inventario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Sección activa (por defecto insumos)
    seccion = request.GET.get('seccion', 'insumos')
    
    # ========== DATOS PARA INSUMOS ==========
    search_insumos = request.GET.get('search_insumos', '')
    categoria = request.GET.get('categoria', '')
    estado_insumo = request.GET.get('estado_insumo', '')
    
    insumos = Insumo.objects.all()
    
    if search_insumos:
        insumos = insumos.filter(
            Q(nombre__icontains=search_insumos) |
            Q(descripcion__icontains=search_insumos) |
            Q(proveedor_principal__nombre__icontains=search_insumos) |
            Q(proveedor_texto__icontains=search_insumos) |
            Q(ubicacion__icontains=search_insumos)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado_insumo:
        insumos = insumos.filter(estado=estado_insumo)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación de insumos
    paginator_insumos = Paginator(insumos_list, 10)
    page_insumos = request.GET.get('page_insumos', 1)
    
    try:
        insumos_pag = paginator_insumos.page(page_insumos)
    except PageNotAnInteger:
        insumos_pag = paginator_insumos.page(1)
    except EmptyPage:
        insumos_pag = paginator_insumos.page(paginator_insumos.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas_insumos = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    # ========== DATOS PARA PROVEEDORES ==========
    search_proveedores = request.GET.get('search_proveedores', '')
    estado_proveedor = request.GET.get('estado_proveedor', '')
    
    proveedores = Proveedor.objects.all()
    
    if search_proveedores:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search_proveedores) |
            Q(rut__icontains=search_proveedores) |
            Q(email__icontains=search_proveedores) |
            Q(telefono__icontains=search_proveedores) |
            Q(contacto_nombre__icontains=search_proveedores)
        )
    
    if estado_proveedor == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado_proveedor == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Estadísticas de proveedores
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas_proveedores = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # ========== DATOS PARA PEDIDOS ==========
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').order_by('-fecha_pedido')[:10]
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas_pedidos = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # ========== DATOS PARA SOLICITUDES ==========
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Obtener proveedores activos para formularios
    proveedores_activos = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'seccion': seccion,
        
        # Insumos
        'insumos': insumos_pag,
        'estadisticas_insumos': estadisticas_insumos,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados_insumo': Insumo.ESTADO_CHOICES,
        'search_insumos': search_insumos,
        'categoria': categoria,
        'estado_insumo': estado_insumo,
        
        # Proveedores
        'proveedores': proveedores,
        'estadisticas_proveedores': estadisticas_proveedores,
        'search_proveedores': search_proveedores,
        'estado_proveedor': estado_proveedor,
        'proveedores_activos': proveedores_activos,
        
        # Pedidos
        'pedidos': pedidos,
        'estadisticas_pedidos': estadisticas_pedidos,
        
        # Solicitudes
        'solicitudes_recientes': solicitudes_recientes,
        
        # Insumos para solicitudes
        'insumos_todos': Insumo.objects.all().order_by('nombre'),
        
        # Fecha actual para comparar vencimientos
        'today': date.today(),
        
        'es_admin': True
    }
    
    return render(request, 'citas/inventario/gestor_inventario_unificado.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from inventario.models import Insumo
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from personal.models import Perfil


@login_required
def gestor_inventario_unificado(request):
    """Vista unificada para gestionar insumos y proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar inventario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Sección activa (por defecto insumos)
    seccion = request.GET.get('seccion', 'insumos')
    
    # ========== DATOS PARA INSUMOS ==========
    search_insumos = request.GET.get('search_insumos', '')
    categoria = request.GET.get('categoria', '')
    estado_insumo = request.GET.get('estado_insumo', '')
    
    insumos = Insumo.objects.all()
    
    if search_insumos:
        insumos = insumos.filter(
            Q(nombre__icontains=search_insumos) |
            Q(descripcion__icontains=search_insumos) |
            Q(proveedor_principal__nombre__icontains=search_insumos) |
            Q(proveedor_texto__icontains=search_insumos) |
            Q(ubicacion__icontains=search_insumos)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado_insumo:
        insumos = insumos.filter(estado=estado_insumo)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación de insumos
    paginator_insumos = Paginator(insumos_list, 10)
    page_insumos = request.GET.get('page_insumos', 1)
    
    try:
        insumos_pag = paginator_insumos.page(page_insumos)
    except PageNotAnInteger:
        insumos_pag = paginator_insumos.page(1)
    except EmptyPage:
        insumos_pag = paginator_insumos.page(paginator_insumos.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas_insumos = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    # ========== DATOS PARA PROVEEDORES ==========
    search_proveedores = request.GET.get('search_proveedores', '')
    estado_proveedor = request.GET.get('estado_proveedor', '')
    
    proveedores = Proveedor.objects.all()
    
    if search_proveedores:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search_proveedores) |
            Q(rut__icontains=search_proveedores) |
            Q(email__icontains=search_proveedores) |
            Q(telefono__icontains=search_proveedores) |
            Q(contacto_nombre__icontains=search_proveedores)
        )
    
    if estado_proveedor == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado_proveedor == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Estadísticas de proveedores
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas_proveedores = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    # ========== DATOS PARA PEDIDOS ==========
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').order_by('-fecha_pedido')[:10]
    
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas_pedidos = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # ========== DATOS PARA SOLICITUDES ==========
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Obtener proveedores activos para formularios
    proveedores_activos = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'seccion': seccion,
        
        # Insumos
        'insumos': insumos_pag,
        'estadisticas_insumos': estadisticas_insumos,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados_insumo': Insumo.ESTADO_CHOICES,
        'search_insumos': search_insumos,
        'categoria': categoria,
        'estado_insumo': estado_insumo,
        
        # Proveedores
        'proveedores': proveedores,
        'estadisticas_proveedores': estadisticas_proveedores,
        'search_proveedores': search_proveedores,
        'estado_proveedor': estado_proveedor,
        'proveedores_activos': proveedores_activos,
        
        # Pedidos
        'pedidos': pedidos,
        'estadisticas_pedidos': estadisticas_pedidos,
        
        # Solicitudes
        'solicitudes_recientes': solicitudes_recientes,
        
        # Insumos para solicitudes
        'insumos_todos': Insumo.objects.all().order_by('nombre'),
        
        # Fecha actual para comparar vencimientos
        'today': date.today(),
        
        'es_admin': True
    }
    
    return render(request, 'citas/inventario/gestor_inventario_unificado.html', context)

