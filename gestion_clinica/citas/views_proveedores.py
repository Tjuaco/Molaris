from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from datetime import datetime
from proveedores.models import Proveedor, SolicitudInsumo
from inventario.models import Insumo
from personal.models import Perfil
import unicodedata

def normalizar_texto(texto):
    """Convierte texto con tildes y ñ a versión sin tildes para email"""
    # Normalizar caracteres Unicode
    texto_normalizado = unicodedata.normalize('NFKD', texto)
    # Filtrar solo caracteres ASCII
    texto_ascii = texto_normalizado.encode('ASCII', 'ignore').decode('ASCII')
    return texto_ascii

# Vista principal de gestión de proveedores
@login_required
def gestor_proveedores(request):
    """Vista para gestionar proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    # Filtros de búsqueda
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    
    # Obtener proveedores
    proveedores = Proveedor.objects.all()
    
    # Aplicar filtros
    if search:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search) |
            Q(rut__icontains=search) |
            Q(email__icontains=search) |
            Q(telefono__icontains=search) |
            Q(contacto_nombre__icontains=search)
        )
    
    if estado == 'activo':
        proveedores = proveedores.filter(activo=True)
    elif estado == 'inactivo':
        proveedores = proveedores.filter(activo=False)
    
    proveedores = proveedores.order_by('nombre')
    
    # Obtener insumos para solicitudes y asociaciones
    insumos = Insumo.objects.all().order_by('nombre')
    
    # Obtener solicitudes recientes
    solicitudes_recientes = SolicitudInsumo.objects.select_related('proveedor', 'insumo').order_by('-fecha_solicitud')[:10]
    
    # Estadísticas
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    proveedores_con_insumos = Proveedor.objects.filter(insumos_principales__isnull=False).distinct().count()
    solicitudes_pendientes = SolicitudInsumo.objects.filter(estado='enviada').count()
    
    estadisticas = {
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_con_insumos': proveedores_con_insumos,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
        'insumos': insumos,
        'solicitudes_recientes': solicitudes_recientes,
        'estadisticas': estadisticas,
        'search': search,
        'estado': estado,
    }
    
    return render(request, 'citas/gestor_proveedores.html', context)

# Vista para crear proveedor
@login_required
def crear_proveedor(request):
    """Vista para crear un nuevo proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            rut = request.POST.get('rut', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            direccion = request.POST.get('direccion', '').strip()
            contacto_nombre = request.POST.get('contacto_nombre', '').strip()
            sitio_web = request.POST.get('sitio_web', '').strip()
            notas = request.POST.get('notas', '').strip()
            
            # Validaciones
            if not nombre or not rut or not email or not telefono:
                messages.error(request, 'Los campos nombre, RUT, email y teléfono son obligatorios.')
                return redirect('gestor_proveedores')
            
            # Verificar que el RUT no exista
            if Proveedor.objects.filter(rut=rut).exists():
                messages.error(request, 'Ya existe un proveedor con este RUT.')
                return redirect('gestor_proveedores')
            
            # Crear proveedor
            proveedor = Proveedor.objects.create(
                nombre=nombre,
                rut=rut,
                email=email,
                telefono=telefono,
                direccion=direccion if direccion else None,
                contacto_nombre=contacto_nombre if contacto_nombre else None,
                sitio_web=sitio_web if sitio_web else None,
                notas=notas if notas else None,
                creado_por=perfil
            )
            
            # Asociar insumos seleccionados
            insumos_ids = request.POST.getlist('insumos[]')
            if insumos_ids:
                insumos_asociados = Insumo.objects.filter(id__in=insumos_ids)
                for insumo in insumos_asociados:
                    insumo.proveedor_principal = proveedor
                    insumo.save()
                    
                messages.success(request, f'Proveedor "{nombre}" creado correctamente con {len(insumos_ids)} insumo(s) asociado(s).')
            else:
                messages.success(request, f'Proveedor "{nombre}" creado correctamente.')
            
            return redirect('gestor_proveedores')
            
        except Exception as e:
            messages.error(request, f'Error al crear proveedor: {str(e)}')
            return redirect('gestor_proveedores')
    
    return redirect('gestor_proveedores')

# Vista para editar proveedor
@login_required
def editar_proveedor(request, proveedor_id):
    """Vista para editar un proveedor existente"""
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            proveedor.nombre = request.POST.get('nombre', '').strip()
            nuevo_rut = request.POST.get('rut', '').strip()
            proveedor.email = request.POST.get('email', '').strip()
            proveedor.telefono = request.POST.get('telefono', '').strip()
            proveedor.direccion = request.POST.get('direccion', '').strip()
            proveedor.contacto_nombre = request.POST.get('contacto_nombre', '').strip()
            proveedor.sitio_web = request.POST.get('sitio_web', '').strip()
            proveedor.notas = request.POST.get('notas', '').strip()
            proveedor.activo = request.POST.get('activo') == 'on'
            
            # Validar RUT si cambió
            if nuevo_rut != proveedor.rut:
                if Proveedor.objects.filter(rut=nuevo_rut).exists():
                    messages.error(request, 'Ya existe un proveedor con este RUT.')
                    return redirect('gestor_proveedores')
                proveedor.rut = nuevo_rut
            
            proveedor.save()
            
            messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado correctamente.')
            return redirect('gestor_proveedores')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar proveedor: {str(e)}')
            return redirect('gestor_proveedores')
    
    return redirect('gestor_proveedores')

# Vista para eliminar proveedor
@login_required
def eliminar_proveedor(request, proveedor_id):
    """Vista para eliminar un proveedor"""
    if request.method == 'POST':
        try:
            proveedor = get_object_or_404(Proveedor, id=proveedor_id)
            nombre = proveedor.nombre
            proveedor.delete()
            messages.success(request, f'Proveedor "{nombre}" eliminado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar proveedor: {str(e)}')
    
    return redirect('gestor_proveedores')

# Vista para enviar solicitud de insumo
@login_required
def enviar_solicitud_insumo(request):
    """Vista para crear y enviar una solicitud de insumo por correo"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            
            # Obtener datos del formulario
            proveedor_id = request.POST.get('proveedor_id')
            insumo_id = request.POST.get('insumo_id')
            cantidad = request.POST.get('cantidad')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not all([proveedor_id, insumo_id, cantidad, fecha_entrega]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('gestor_proveedores')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id)
            insumo = get_object_or_404(Insumo, id=insumo_id)
            cantidad = int(cantidad)
            
            # Validar fecha
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect('gestor_proveedores')
            
            # Calcular monto del egreso si está marcado
            monto_egreso = None
            if registrar_como_egreso and insumo.precio_unitario:
                monto_egreso = float(insumo.precio_unitario) * cantidad
            
            # Crear solicitud
            solicitud = SolicitudInsumo.objects.create(
                proveedor=proveedor,
                insumo=insumo,
                cantidad_solicitada=cantidad,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                solicitado_por=perfil,
                registrar_como_egreso=registrar_como_egreso,
                monto_egreso=monto_egreso
            )
            
            # Preparar y enviar correo - Normalizar todos los textos
            # Normalizar datos para evitar problemas de codificación
            nombre_proveedor = normalizar_texto(proveedor.contacto_nombre or proveedor.nombre)
            nombre_insumo = normalizar_texto(insumo.nombre)
            unidad_medida = normalizar_texto(insumo.unidad_medida)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            observaciones_norm = normalizar_texto(observaciones) if observaciones else ''
            
            asunto = f'Solicitud de Insumo - {nombre_insumo}'
            
            # Formatear las fechas
            fecha_entrega_str = fecha_entrega_obj.strftime('%d/%m/%Y')
            fecha_solicitud_str = solicitud.fecha_solicitud.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para solicitar formalmente el siguiente insumo:

================================================================================
DETALLES DE LA SOLICITUD
================================================================================

* Numero de Solicitud: #{solicitud.id}
* Insumo Solicitado: {nombre_insumo}
* Cantidad Requerida: {cantidad} {unidad_medida}
* Fecha de Entrega Esperada: {fecha_entrega_str}
* Fecha de la Solicitud: {fecha_solicitud_str}

{f'* Observaciones: {observaciones_norm}' if observaciones_norm else ''}

================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de esta solicitud y la disponibilidad del 
insumo requerido a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            try:
                # Crear el correo
                email = EmailMessage(
                    subject=asunto,
                    body=mensaje,
                    from_email='clinica@dental.com',  # Email simple sin caracteres especiales
                    to=[proveedor.email],
                )
                
                # Enviar el correo
                email.send(fail_silently=False)
                
                # Actualizar solicitud
                solicitud.correo_enviado = True
                solicitud.fecha_envio_correo = timezone.now()
                solicitud.estado = 'enviada'
                solicitud.save()
                
                messages.success(request, f'Solicitud #{solicitud.id} creada y correo enviado a {proveedor.nombre} ({proveedor.email}).')
                
            except Exception as e:
                # Si falla el envío, marcar como pendiente
                messages.warning(request, f'Solicitud #{solicitud.id} creada, pero hubo un error al enviar el correo: {str(e)}. Verifica la configuración de email.')
            
            return redirect('gestor_proveedores')
            
        except Exception as e:
            messages.error(request, f'Error al procesar solicitud: {str(e)}')
            return redirect('gestor_proveedores')
    
    return redirect('gestor_proveedores')












