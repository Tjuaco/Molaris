from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from datetime import datetime
from decimal import Decimal
from proveedores.models import Proveedor, SolicitudInsumo, Pedido
from inventario.models import Insumo, MovimientoInsumo
from personal.models import Perfil
from finanzas.models import EgresoManual
import unicodedata
import re

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
    
    return render(request, 'citas/proveedores/gestor_proveedores.html', context)

# Vista para crear proveedor
@login_required
def crear_proveedor(request):
    """Vista para crear un nuevo proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            
            # Verificar si es petición AJAX
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
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
            if not nombre:
                error_msg = 'El nombre del proveedor es obligatorio. Por favor, ingrese un nombre.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            if len(nombre) < 3:
                error_msg = 'El nombre del proveedor debe tener al menos 3 caracteres.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            if not rut:
                error_msg = 'El RUT/NIT es obligatorio. Por favor, ingrese el RUT del proveedor.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            # Validar formato de email
            if not email:
                error_msg = 'El email es obligatorio. Por favor, ingrese un email de contacto.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                error_msg = 'El formato del email no es válido. Por favor, ingrese un email válido (ejemplo: proveedor@ejemplo.com).'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            if not telefono:
                error_msg = 'El teléfono es obligatorio. Por favor, ingrese un número de teléfono de contacto.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            # Validar formato de teléfono (al menos 8 dígitos)
            telefono_limpio = re.sub(r'[^\d]', '', telefono)
            if len(telefono_limpio) < 8:
                error_msg = 'El teléfono debe tener al menos 8 dígitos. Por favor, ingrese un número válido.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            # Validar URL del sitio web si se proporciona
            if sitio_web:
                url_pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?$'
                if not re.match(url_pattern, sitio_web):
                    error_msg = 'El formato del sitio web no es válido. Debe comenzar con http:// o https://'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': error_msg}, status=400)
                    messages.error(request, error_msg)
                    return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            # Verificar que el RUT no exista
            if Proveedor.objects.filter(rut=rut).exists():
                error_msg = f'Ya existe un proveedor con el RUT "{rut}". Por favor, verifique el RUT o edite el proveedor existente.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            # Verificar que el nombre no exista (case-insensitive)
            if Proveedor.objects.filter(nombre__iexact=nombre).exists():
                error_msg = f'Ya existe un proveedor con el nombre "{nombre}". Por favor, elija un nombre diferente.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
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
            insumos_count = 0
            if insumos_ids:
                insumos_asociados = Insumo.objects.filter(id__in=insumos_ids)
                for insumo in insumos_asociados:
                    insumo.proveedor_principal = proveedor
                    insumo.save()
                insumos_count = len(insumos_asociados)
            
            if insumos_count > 0:
                success_msg = f'✅ Proveedor "{nombre}" creado correctamente con {insumos_count} insumo(s) asociado(s).'
            else:
                success_msg = f'✅ Proveedor "{nombre}" creado correctamente.'
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_msg,
                    'proveedor': {
                        'id': proveedor.id,
                        'nombre': proveedor.nombre,
                        'rut': proveedor.rut,
                        'email': proveedor.email,
                    }
                })
            
            messages.success(request, success_msg)
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
        except Exception as e:
            error_msg = f'❌ Error inesperado al crear el proveedor. Por favor, intente nuevamente. Si el problema persiste, contacte al administrador del sistema. Detalles: {str(e)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_msg}, status=500)
            messages.error(request, error_msg)
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
    
    # Si es GET, mostrar el formulario para crear proveedor
    try:
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Obtener insumos sin proveedor para asociarlos opcionalmente
    insumos_sin_proveedor = Insumo.objects.filter(proveedor_principal__isnull=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'insumos_sin_proveedor': insumos_sin_proveedor,
        'form_data': request.POST if request.method == 'POST' else {}
    }
    
    return render(request, 'citas/proveedores/crear_proveedor.html', context)

# Vista para editar proveedor
@login_required
def editar_proveedor(request, proveedor_id):
    """Vista para editar un proveedor existente"""
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    
    if request.method == 'GET':
        # Renderizar el formulario de edición con los datos del proveedor
        context = {
            'proveedor': proveedor,
        }
        return render(request, 'citas/proveedores/editar_proveedor.html', context)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            nuevo_rut = request.POST.get('rut', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            direccion = request.POST.get('direccion', '').strip()
            contacto_nombre = request.POST.get('contacto_nombre', '').strip()
            sitio_web = request.POST.get('sitio_web', '').strip()
            notas = request.POST.get('notas', '').strip()
            activo = request.POST.get('activo') == 'on' or request.POST.get('activo') == 'true'
            
            # Validaciones
            if not nombre:
                messages.error(request, 'El nombre del proveedor es obligatorio. Por favor, ingrese un nombre.')
                context = {'proveedor': proveedor}
                return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            if len(nombre) < 3:
                messages.error(request, 'El nombre del proveedor debe tener al menos 3 caracteres.')
                context = {'proveedor': proveedor}
                return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            if not nuevo_rut:
                messages.error(request, 'El RUT/NIT es obligatorio. Por favor, ingrese el RUT del proveedor.')
                context = {'proveedor': proveedor}
                return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            # Validar formato de email
            if not email:
                messages.error(request, 'El email es obligatorio. Por favor, ingrese un email de contacto.')
                context = {'proveedor': proveedor}
                return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                messages.error(request, 'El formato del email no es válido. Por favor, ingrese un email válido (ejemplo: proveedor@ejemplo.com).')
                context = {'proveedor': proveedor}
                return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            if not telefono:
                messages.error(request, 'El teléfono es obligatorio. Por favor, ingrese un número de teléfono de contacto.')
                context = {'proveedor': proveedor}
                return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            # Validar formato de teléfono
            telefono_limpio = re.sub(r'[^\d]', '', telefono)
            if len(telefono_limpio) < 8:
                messages.error(request, 'El teléfono debe tener al menos 8 dígitos. Por favor, ingrese un número válido.')
                context = {'proveedor': proveedor}
                return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            # Validar URL del sitio web si se proporciona
            if sitio_web:
                url_pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?$'
                if not re.match(url_pattern, sitio_web):
                    messages.error(request, 'El formato del sitio web no es válido. Debe comenzar con http:// o https://')
                    context = {'proveedor': proveedor}
                    return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            # Validar RUT si cambió
            if nuevo_rut != proveedor.rut:
                if Proveedor.objects.filter(rut=nuevo_rut).exists():
                    messages.error(request, f'Ya existe otro proveedor con el RUT "{nuevo_rut}". Por favor, verifique el RUT.')
                    context = {'proveedor': proveedor}
                    return render(request, 'citas/proveedores/editar_proveedor.html', context)
                proveedor.rut = nuevo_rut
            
            # Validar nombre si cambió
            if nombre.lower() != proveedor.nombre.lower():
                if Proveedor.objects.filter(nombre__iexact=nombre).exclude(id=proveedor_id).exists():
                    messages.error(request, f'Ya existe otro proveedor con el nombre "{nombre}". Por favor, elija un nombre diferente.')
                    context = {'proveedor': proveedor}
                    return render(request, 'citas/proveedores/editar_proveedor.html', context)
            
            # Actualizar campos
            proveedor.nombre = nombre
            proveedor.email = email
            proveedor.telefono = telefono
            proveedor.direccion = direccion if direccion else None
            proveedor.contacto_nombre = contacto_nombre if contacto_nombre else None
            proveedor.sitio_web = sitio_web if sitio_web else None
            proveedor.notas = notas if notas else None
            proveedor.activo = activo
            
            proveedor.save()
            
            messages.success(request, f'✅ Proveedor "{proveedor.nombre}" actualizado correctamente.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'❌ Error inesperado al actualizar el proveedor. Por favor, intente nuevamente. Si el problema persiste, contacte al administrador del sistema. Detalles: {str(e)}')
            context = {'proveedor': proveedor}
            return render(request, 'citas/proveedores/editar_proveedor.html', context)
    
    return redirect('gestor_inventario_unificado')

# Vista para eliminar proveedor
@login_required
def eliminar_proveedor(request, proveedor_id):
    """Vista para eliminar un proveedor"""
    if request.method == 'POST':
        try:
            proveedor = get_object_or_404(Proveedor, id=proveedor_id)
            nombre = proveedor.nombre
            
            # Verificar si tiene insumos asociados
            insumos_asociados = Insumo.objects.filter(proveedor_principal=proveedor).count()
            if insumos_asociados > 0:
                messages.warning(request, f'⚠️ El proveedor "{nombre}" tiene {insumos_asociados} insumo(s) asociado(s). Se recomienda desasociar los insumos antes de eliminar el proveedor.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=proveedores')
            
            proveedor.delete()
            messages.success(request, f'✅ Proveedor "{nombre}" eliminado correctamente.')
        except Exception as e:
            messages.error(request, f'❌ Error inesperado al eliminar el proveedor. Por favor, intente nuevamente. Si el problema persiste, contacte al administrador del sistema. Detalles: {str(e)}')
    
    return redirect('gestor_inventario_unificado')

# Vista para enviar solicitud de insumos (simplificada - múltiples insumos)
@login_required
def enviar_solicitud_insumo(request):
    """Vista para crear y enviar solicitudes de insumos por correo (múltiples insumos en una solicitud)"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            
            # Obtener datos del formulario
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            insumos_seleccionados = request.POST.getlist('insumos[]')
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')
            
            if not insumos_seleccionados:
                messages.error(request, 'Debes seleccionar al menos un insumo.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            # Validar fecha
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')
            
            # Crear solicitudes para cada insumo seleccionado
            solicitudes_creadas = []
            insumos_data = []
            
            for insumo_id in insumos_seleccionados:
                cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                try:
                    cantidad_int = int(cantidad)
                    if cantidad_int > 0:
                        insumo = get_object_or_404(Insumo, id=insumo_id)
                        
                        # Crear solicitud (asegurarse de que el estado sea 'pendiente')
                        solicitud = SolicitudInsumo.objects.create(
                            proveedor=proveedor,
                            insumo=insumo,
                            cantidad_solicitada=cantidad_int,
                            fecha_entrega_esperada=fecha_entrega_obj,
                            observaciones=observaciones,
                            solicitado_por=perfil,
                            estado='pendiente'  # Asegurar explícitamente que sea pendiente
                        )
                        # Verificar que el estado sea correcto después de crear
                        if solicitud.estado != 'pendiente':
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f'Solicitud {solicitud.id} creada con estado incorrecto: {solicitud.estado}. Corrigiendo a pendiente.')
                            solicitud.estado = 'pendiente'
                            solicitud.save()
                        solicitudes_creadas.append(solicitud)
                        
                        # Establecer precio unitario en la solicitud si el insumo lo tiene
                        precio_unitario = None
                        if insumo.precio_unitario:
                            try:
                                precio_unitario = float(insumo.precio_unitario)
                                # Actualizar la solicitud con el precio unitario para que se calcule el monto
                                solicitud.precio_unitario = precio_unitario
                                solicitud.save()  # Esto activará el cálculo automático del monto_egreso
                            except (ValueError, TypeError):
                                precio_unitario = None
                        
                        insumos_data.append({
                            'nombre': normalizar_texto(insumo.nombre),
                            'categoria': insumo.get_categoria_display(),
                            'cantidad': cantidad_int,
                            'unidad_medida': normalizar_texto(insumo.unidad_medida),
                            'precio_unitario': precio_unitario,
                        })
                except (ValueError, Insumo.DoesNotExist) as e:
                    continue
            
            if not solicitudes_creadas:
                messages.error(request, 'No se pudieron crear las solicitudes. Verifica los datos ingresados.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')
            
            # Preparar datos para el correo
            nombre_proveedor = normalizar_texto(proveedor.contacto_nombre or proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            observaciones_norm = normalizar_texto(observaciones) if observaciones else None
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Renderizar template HTML con múltiples insumos
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/solicitud_insumo.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_solicitud': f"#{solicitudes_creadas[0].id}" + (f" - #{solicitudes_creadas[-1].id}" if len(solicitudes_creadas) > 1 else ""),
                'insumos': insumos_data,
                'fecha_entrega_esperada': fecha_entrega_obj,
                'fecha_solicitud': solicitudes_creadas[0].fecha_solicitud,
                'observaciones': observaciones_norm,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            asunto = f'Solicitud de Insumos - {nombre_clinica}'
            
            try:
                # Crear el correo con contenido HTML
                from django.core.mail import EmailMultiAlternatives
                import logging
                logger = logging.getLogger(__name__)
                
                logger.info(f'Intentando enviar correo a {proveedor.email} para {len(solicitudes_creadas)} solicitud(es)')
                
                email = EmailMultiAlternatives(
                    subject=asunto,
                    body='',  # Versión texto vacía
                    from_email=email_clinica,
                    to=[proveedor.email],
                )
                email.attach_alternative(mensaje_html, "text/html")
                
                # Enviar el correo
                email.send(fail_silently=False)
                
                logger.info(f'Correo enviado exitosamente a {proveedor.email}')
                
                # Las solicitudes se quedan como "pendiente" hasta que se marquen como recibidas
                # No se cambian a "enviada" automáticamente
                
                messages.success(request, f'✅ {len(solicitudes_creadas)} solicitud(es) creada(s) y correo enviado a {proveedor.nombre} ({proveedor.email}). Las solicitudes quedaron como pendientes hasta su recepción.')
                
            except Exception as e:
                # Si falla el envío, NO marcar como enviada, dejar como pendiente
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f'Error al enviar correo a {proveedor.email}: {str(e)}\n{traceback.format_exc()}')
                
                # Las solicitudes se quedan como 'pendiente' (estado por defecto)
                # NO las marcamos como 'enviada' si falló el correo
                messages.warning(request, f'⚠️ {len(solicitudes_creadas)} solicitud(es) creada(s), pero hubo un error al enviar el correo: {str(e)}. Verifica la configuración de email. Las solicitudes quedaron como pendientes.')
            
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')
            
        except Exception as e:
            import traceback
            messages.error(request, f'❌ Error inesperado al procesar la solicitud. Por favor, intente nuevamente. Si el problema persiste, contacte al administrador del sistema. Detalles: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')
    
    return redirect(reverse('gestor_inventario_unificado') + '?seccion=solicitudes')


# ========== GESTIÓN DE PEDIDOS ==========

@login_required
def gestor_pedidos(request):
    """Vista principal para gestionar pedidos a proveedores - Redirige al gestor unificado"""
    # Redirigir al gestor unificado con la sección de pedidos activa
    return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Estadísticas
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # Obtener proveedores para filtro
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'proveedores': proveedores,
        'search': search,
        'estado': estado,
        'proveedor_id': proveedor_id,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'citas/proveedores/gestor_pedidos.html', context)


@login_required
def obtener_insumos_proveedor(request, proveedor_id):
    """Vista AJAX para obtener los insumos de un proveedor"""
    try:
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
        insumos = Insumo.objects.filter(proveedor_principal=proveedor).order_by('nombre')
        
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.id,
                'nombre': insumo.nombre,
                'categoria': insumo.get_categoria_display(),
                'precio_unitario': str(insumo.precio_unitario) if insumo.precio_unitario else None,
                'unidad_medida': insumo.unidad_medida,
                'stock_actual': insumo.cantidad_actual,
            })
        
        return JsonResponse({
            'success': True,
            'insumos': insumos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def crear_pedido(request):
    """Vista para crear un nuevo pedido"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            # Crear pedido
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                estado='borrador',
                registrar_como_egreso=registrar_como_egreso,
                creado_por=perfil
            )
            
            # Procesar insumos seleccionados
            insumos_seleccionados = request.POST.getlist('insumos[]')
            if insumos_seleccionados:
                from proveedores.models import SolicitudInsumo
                for insumo_id in insumos_seleccionados:
                    cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                    try:
                        cantidad_int = int(cantidad)
                        if cantidad_int > 0:
                            insumo = get_object_or_404(Insumo, id=insumo_id)
                            SolicitudInsumo.objects.create(
                                pedido=pedido,
                                proveedor=proveedor,
                                insumo=insumo,
                                cantidad_solicitada=cantidad_int,
                                fecha_entrega_esperada=fecha_entrega_obj,
                                precio_unitario=insumo.precio_unitario or None,
                                solicitado_por=perfil
                            )
                    except (ValueError, Insumo.DoesNotExist) as e:
                        # Log del error pero continuar con los demás insumos
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error al agregar insumo {insumo_id} al pedido: {str(e)}')
                        continue
            
            if insumos_seleccionados:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente con {len(insumos_seleccionados)} insumo(s).')
            else:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente. Ahora puedes agregar insumos al pedido.')
            
            return redirect('detalle_pedido', pedido_id=pedido.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
    }
    
    return render(request, 'citas/proveedores/crear_pedido.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver y gestionar un pedido específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes__insumo'), id=pedido_id)
    
    # Obtener insumos disponibles para agregar (priorizar los del proveedor)
    insumos_proveedor = Insumo.objects.filter(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos_otros = Insumo.objects.exclude(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos = list(insumos_proveedor) + list(insumos_otros)
    
    context = {
        'perfil': perfil,
        'pedido': pedido,
        'insumos': insumos,
    }
    
    return render(request, 'citas/proveedores/detalle_pedido.html', context)


@login_required
def agregar_insumo_pedido(request, pedido_id):
    """Vista AJAX para agregar un insumo a un pedido"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.estado != 'borrador':
            return JsonResponse({'success': False, 'message': 'Solo se pueden agregar insumos a pedidos en estado borrador.'}, status=400)
        
        insumo_id = request.POST.get('insumo_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario', '')
        observaciones = request.POST.get('observaciones', '').strip()
        
        if not insumo_id or not cantidad:
            return JsonResponse({'success': False, 'message': 'El insumo y la cantidad son obligatorios.'}, status=400)
        
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                return JsonResponse({'success': False, 'message': 'La cantidad debe ser mayor a 0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'La cantidad debe ser un número válido.'}, status=400)
        
        insumo = get_object_or_404(Insumo, id=insumo_id)
        
        # Precio unitario
        precio_unitario_decimal = None
        if precio_unitario:
            try:
                precio_unitario_decimal = Decimal(str(precio_unitario))
            except:
                precio_unitario_decimal = insumo.precio_unitario
        else:
            precio_unitario_decimal = insumo.precio_unitario
        
        # Crear solicitud
        solicitud = SolicitudInsumo.objects.create(
            pedido=pedido,
            proveedor=pedido.proveedor,
            insumo=insumo,
            cantidad_solicitada=cantidad_int,
            fecha_entrega_esperada=pedido.fecha_entrega_esperada,
            observaciones=observaciones,
            precio_unitario=precio_unitario_decimal,
            solicitado_por=perfil
        )
        
        # Recalcular monto total del pedido
        pedido.monto_total = pedido.calcular_monto_total()
        pedido.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Insumo "{insumo.nombre}" agregado al pedido correctamente.',
            'solicitud_id': solicitud.id
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def enviar_pedido_correo(request, pedido_id):
    """Vista para enviar el pedido por correo al proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido.objects.prefetch_related('solicitudes__insumo'), id=pedido_id)
        
        if not pedido.solicitudes.exists():
            return JsonResponse({'success': False, 'message': 'El pedido no tiene insumos. Agrega insumos antes de enviarlo.'}, status=400)
        
        if pedido.estado not in ['borrador', 'pendiente']:
            return JsonResponse({'success': False, 'message': 'Solo se pueden enviar pedidos en estado borrador o pendiente.'}, status=400)
        
        try:
            # Construir mensaje del correo
            nombre_proveedor = normalizar_texto(pedido.proveedor.contacto_nombre or pedido.proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            
            asunto = f'Pedido de Insumos - {pedido.numero_pedido}'
            
            # Detalles del pedido
            fecha_entrega_str = pedido.fecha_entrega_esperada.strftime('%d/%m/%Y')
            fecha_pedido_str = pedido.fecha_pedido.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para realizar el siguiente pedido de insumos:

================================================================================
DETALLES DEL PEDIDO
================================================================================

* Numero de Pedido: {pedido.numero_pedido}
* Fecha del Pedido: {fecha_pedido_str}
* Fecha de Entrega Esperada: {fecha_entrega_str}

================================================================================
INSUMOS SOLICITADOS
================================================================================

"""
            
            # Agregar cada insumo
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                mensaje += f"* {nombre_insumo}\n"
                mensaje += f"  - Cantidad: {solicitud.cantidad_solicitada} {unidad_medida}\n"
                mensaje += f"  - Precio Unitario: {precio_str}\n"
                mensaje += f"  - Monto Total: {monto_str}\n"
                if solicitud.observaciones:
                    obs_norm = normalizar_texto(solicitud.observaciones)
                    mensaje += f"  - Observaciones: {obs_norm}\n"
                mensaje += "\n"
            
            # Monto total del pedido
            if pedido.monto_total:
                mensaje += f"================================================================================\n"
                mensaje += f"MONTO TOTAL DEL PEDIDO: ${pedido.monto_total:,.0f}\n"
                mensaje += f"================================================================================\n\n"
            
            # Observaciones generales
            if pedido.observaciones:
                obs_gen = normalizar_texto(pedido.observaciones)
                mensaje += f"Observaciones Generales:\n{obs_gen}\n\n"
            
            mensaje += f"""================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de este pedido y la disponibilidad de los 
insumos requeridos a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Preparar lista de insumos para el template
            insumos_list = []
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                insumos_list.append({
                    'nombre': nombre_insumo,
                    'cantidad': solicitud.cantidad_solicitada,
                    'unidad': unidad_medida,
                    'precio_unitario': precio_str,
                    'monto_total': monto_str,
                    'observaciones': normalizar_texto(solicitud.observaciones) if solicitud.observaciones else None,
                })
            
            # Renderizar template HTML
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/pedido_proveedor.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_pedido': pedido.numero_pedido,
                'fecha_pedido': pedido.fecha_pedido,
                'fecha_entrega_esperada': pedido.fecha_entrega_esperada,
                'insumos': insumos_list,
                'monto_total': f"${pedido.monto_total:,.0f}" if pedido.monto_total else None,
                'observaciones_generales': normalizar_texto(pedido.observaciones) if pedido.observaciones else None,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            # Enviar correo
            email = EmailMessage(
                subject=asunto,
                body=mensaje_html,
                from_email=email_clinica,
                to=[pedido.proveedor.email],
            )
            email.content_subtype = "html"  # Indicar que es HTML
            
            email.send(fail_silently=False)
            
            # Actualizar pedido
            pedido.correo_enviado = True
            pedido.fecha_envio_correo = timezone.now()
            pedido.estado = 'enviado'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido {pedido.numero_pedido} enviado correctamente a {pedido.proveedor.email}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al enviar el correo: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)









def gestor_pedidos(request):
    """Vista principal para gestionar pedidos a proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar pedidos.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Filtros
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    proveedor_id = request.GET.get('proveedor_id', '')
    
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').all()
    
    if search:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=search) |
            Q(proveedor__nombre__icontains=search) |
            Q(proveedor__rut__icontains=search)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    if proveedor_id:
        pedidos = pedidos.filter(proveedor_id=proveedor_id)
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Estadísticas
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # Obtener proveedores para filtro
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'proveedores': proveedores,
        'search': search,
        'estado': estado,
        'proveedor_id': proveedor_id,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'citas/proveedores/gestor_pedidos.html', context)


@login_required
def obtener_insumos_proveedor(request, proveedor_id):
    """Vista AJAX para obtener los insumos de un proveedor"""
    try:
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
        insumos = Insumo.objects.filter(proveedor_principal=proveedor).order_by('nombre')
        
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.id,
                'nombre': insumo.nombre,
                'categoria': insumo.get_categoria_display(),
                'precio_unitario': str(insumo.precio_unitario) if insumo.precio_unitario else None,
                'unidad_medida': insumo.unidad_medida,
                'stock_actual': insumo.cantidad_actual,
            })
        
        return JsonResponse({
            'success': True,
            'insumos': insumos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def crear_pedido(request):
    """Vista para crear un nuevo pedido"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            # Crear pedido
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                estado='borrador',
                registrar_como_egreso=registrar_como_egreso,
                creado_por=perfil
            )
            
            # Procesar insumos seleccionados
            insumos_seleccionados = request.POST.getlist('insumos[]')
            if insumos_seleccionados:
                from proveedores.models import SolicitudInsumo
                for insumo_id in insumos_seleccionados:
                    cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                    try:
                        cantidad_int = int(cantidad)
                        if cantidad_int > 0:
                            insumo = get_object_or_404(Insumo, id=insumo_id)
                            SolicitudInsumo.objects.create(
                                pedido=pedido,
                                proveedor=proveedor,
                                insumo=insumo,
                                cantidad_solicitada=cantidad_int,
                                fecha_entrega_esperada=fecha_entrega_obj,
                                precio_unitario=insumo.precio_unitario or None,
                                solicitado_por=perfil
                            )
                    except (ValueError, Insumo.DoesNotExist) as e:
                        # Log del error pero continuar con los demás insumos
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error al agregar insumo {insumo_id} al pedido: {str(e)}')
                        continue
            
            if insumos_seleccionados:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente con {len(insumos_seleccionados)} insumo(s).')
            else:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente. Ahora puedes agregar insumos al pedido.')
            
            return redirect('detalle_pedido', pedido_id=pedido.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
    }
    
    return render(request, 'citas/proveedores/crear_pedido.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver y gestionar un pedido específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes__insumo'), id=pedido_id)
    
    # Obtener insumos disponibles para agregar (priorizar los del proveedor)
    insumos_proveedor = Insumo.objects.filter(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos_otros = Insumo.objects.exclude(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos = list(insumos_proveedor) + list(insumos_otros)
    
    context = {
        'perfil': perfil,
        'pedido': pedido,
        'insumos': insumos,
    }
    
    return render(request, 'citas/proveedores/detalle_pedido.html', context)


@login_required
def agregar_insumo_pedido(request, pedido_id):
    """Vista AJAX para agregar un insumo a un pedido"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.estado != 'borrador':
            return JsonResponse({'success': False, 'message': 'Solo se pueden agregar insumos a pedidos en estado borrador.'}, status=400)
        
        insumo_id = request.POST.get('insumo_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario', '')
        observaciones = request.POST.get('observaciones', '').strip()
        
        if not insumo_id or not cantidad:
            return JsonResponse({'success': False, 'message': 'El insumo y la cantidad son obligatorios.'}, status=400)
        
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                return JsonResponse({'success': False, 'message': 'La cantidad debe ser mayor a 0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'La cantidad debe ser un número válido.'}, status=400)
        
        insumo = get_object_or_404(Insumo, id=insumo_id)
        
        # Precio unitario
        precio_unitario_decimal = None
        if precio_unitario:
            try:
                precio_unitario_decimal = Decimal(str(precio_unitario))
            except:
                precio_unitario_decimal = insumo.precio_unitario
        else:
            precio_unitario_decimal = insumo.precio_unitario
        
        # Crear solicitud
        solicitud = SolicitudInsumo.objects.create(
            pedido=pedido,
            proveedor=pedido.proveedor,
            insumo=insumo,
            cantidad_solicitada=cantidad_int,
            fecha_entrega_esperada=pedido.fecha_entrega_esperada,
            observaciones=observaciones,
            precio_unitario=precio_unitario_decimal,
            solicitado_por=perfil
        )
        
        # Recalcular monto total del pedido
        pedido.monto_total = pedido.calcular_monto_total()
        pedido.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Insumo "{insumo.nombre}" agregado al pedido correctamente.',
            'solicitud_id': solicitud.id
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def enviar_pedido_correo(request, pedido_id):
    """Vista para enviar el pedido por correo al proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido.objects.prefetch_related('solicitudes__insumo'), id=pedido_id)
        
        if not pedido.solicitudes.exists():
            return JsonResponse({'success': False, 'message': 'El pedido no tiene insumos. Agrega insumos antes de enviarlo.'}, status=400)
        
        if pedido.estado not in ['borrador', 'pendiente']:
            return JsonResponse({'success': False, 'message': 'Solo se pueden enviar pedidos en estado borrador o pendiente.'}, status=400)
        
        try:
            # Construir mensaje del correo
            nombre_proveedor = normalizar_texto(pedido.proveedor.contacto_nombre or pedido.proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            
            asunto = f'Pedido de Insumos - {pedido.numero_pedido}'
            
            # Detalles del pedido
            fecha_entrega_str = pedido.fecha_entrega_esperada.strftime('%d/%m/%Y')
            fecha_pedido_str = pedido.fecha_pedido.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para realizar el siguiente pedido de insumos:

================================================================================
DETALLES DEL PEDIDO
================================================================================

* Numero de Pedido: {pedido.numero_pedido}
* Fecha del Pedido: {fecha_pedido_str}
* Fecha de Entrega Esperada: {fecha_entrega_str}

================================================================================
INSUMOS SOLICITADOS
================================================================================

"""
            
            # Agregar cada insumo
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                mensaje += f"* {nombre_insumo}\n"
                mensaje += f"  - Cantidad: {solicitud.cantidad_solicitada} {unidad_medida}\n"
                mensaje += f"  - Precio Unitario: {precio_str}\n"
                mensaje += f"  - Monto Total: {monto_str}\n"
                if solicitud.observaciones:
                    obs_norm = normalizar_texto(solicitud.observaciones)
                    mensaje += f"  - Observaciones: {obs_norm}\n"
                mensaje += "\n"
            
            # Monto total del pedido
            if pedido.monto_total:
                mensaje += f"================================================================================\n"
                mensaje += f"MONTO TOTAL DEL PEDIDO: ${pedido.monto_total:,.0f}\n"
                mensaje += f"================================================================================\n\n"
            
            # Observaciones generales
            if pedido.observaciones:
                obs_gen = normalizar_texto(pedido.observaciones)
                mensaje += f"Observaciones Generales:\n{obs_gen}\n\n"
            
            mensaje += f"""================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de este pedido y la disponibilidad de los 
insumos requeridos a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Preparar lista de insumos para el template
            insumos_list = []
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                insumos_list.append({
                    'nombre': nombre_insumo,
                    'cantidad': solicitud.cantidad_solicitada,
                    'unidad': unidad_medida,
                    'precio_unitario': precio_str,
                    'monto_total': monto_str,
                    'observaciones': normalizar_texto(solicitud.observaciones) if solicitud.observaciones else None,
                })
            
            # Renderizar template HTML
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/pedido_proveedor.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_pedido': pedido.numero_pedido,
                'fecha_pedido': pedido.fecha_pedido,
                'fecha_entrega_esperada': pedido.fecha_entrega_esperada,
                'insumos': insumos_list,
                'monto_total': f"${pedido.monto_total:,.0f}" if pedido.monto_total else None,
                'observaciones_generales': normalizar_texto(pedido.observaciones) if pedido.observaciones else None,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            # Enviar correo
            email = EmailMessage(
                subject=asunto,
                body=mensaje_html,
                from_email=email_clinica,
                to=[pedido.proveedor.email],
            )
            email.content_subtype = "html"  # Indicar que es HTML
            
            email.send(fail_silently=False)
            
            # Actualizar pedido
            pedido.correo_enviado = True
            pedido.fecha_envio_correo = timezone.now()
            pedido.estado = 'enviado'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido {pedido.numero_pedido} enviado correctamente a {pedido.proveedor.email}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al enviar el correo: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)









def gestor_pedidos(request):
    """Vista principal para gestionar pedidos a proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar pedidos.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Filtros
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    proveedor_id = request.GET.get('proveedor_id', '')
    
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').all()
    
    if search:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=search) |
            Q(proveedor__nombre__icontains=search) |
            Q(proveedor__rut__icontains=search)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    if proveedor_id:
        pedidos = pedidos.filter(proveedor_id=proveedor_id)
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Estadísticas
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # Obtener proveedores para filtro
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'proveedores': proveedores,
        'search': search,
        'estado': estado,
        'proveedor_id': proveedor_id,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'citas/proveedores/gestor_pedidos.html', context)


@login_required
def obtener_insumos_proveedor(request, proveedor_id):
    """Vista AJAX para obtener los insumos de un proveedor"""
    try:
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
        insumos = Insumo.objects.filter(proveedor_principal=proveedor).order_by('nombre')
        
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.id,
                'nombre': insumo.nombre,
                'categoria': insumo.get_categoria_display(),
                'precio_unitario': str(insumo.precio_unitario) if insumo.precio_unitario else None,
                'unidad_medida': insumo.unidad_medida,
                'stock_actual': insumo.cantidad_actual,
            })
        
        return JsonResponse({
            'success': True,
            'insumos': insumos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def crear_pedido(request):
    """Vista para crear un nuevo pedido"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            # Crear pedido
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                estado='borrador',
                registrar_como_egreso=registrar_como_egreso,
                creado_por=perfil
            )
            
            # Procesar insumos seleccionados
            insumos_seleccionados = request.POST.getlist('insumos[]')
            if insumos_seleccionados:
                from proveedores.models import SolicitudInsumo
                for insumo_id in insumos_seleccionados:
                    cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                    try:
                        cantidad_int = int(cantidad)
                        if cantidad_int > 0:
                            insumo = get_object_or_404(Insumo, id=insumo_id)
                            SolicitudInsumo.objects.create(
                                pedido=pedido,
                                proveedor=proveedor,
                                insumo=insumo,
                                cantidad_solicitada=cantidad_int,
                                fecha_entrega_esperada=fecha_entrega_obj,
                                precio_unitario=insumo.precio_unitario or None,
                                solicitado_por=perfil
                            )
                    except (ValueError, Insumo.DoesNotExist) as e:
                        # Log del error pero continuar con los demás insumos
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error al agregar insumo {insumo_id} al pedido: {str(e)}')
                        continue
            
            if insumos_seleccionados:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente con {len(insumos_seleccionados)} insumo(s).')
            else:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente. Ahora puedes agregar insumos al pedido.')
            
            return redirect('detalle_pedido', pedido_id=pedido.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
    }
    
    return render(request, 'citas/proveedores/crear_pedido.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver y gestionar un pedido específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes__insumo'), id=pedido_id)
    
    # Obtener insumos disponibles para agregar (priorizar los del proveedor)
    insumos_proveedor = Insumo.objects.filter(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos_otros = Insumo.objects.exclude(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos = list(insumos_proveedor) + list(insumos_otros)
    
    context = {
        'perfil': perfil,
        'pedido': pedido,
        'insumos': insumos,
    }
    
    return render(request, 'citas/proveedores/detalle_pedido.html', context)


@login_required
def agregar_insumo_pedido(request, pedido_id):
    """Vista AJAX para agregar un insumo a un pedido"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.estado != 'borrador':
            return JsonResponse({'success': False, 'message': 'Solo se pueden agregar insumos a pedidos en estado borrador.'}, status=400)
        
        insumo_id = request.POST.get('insumo_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario', '')
        observaciones = request.POST.get('observaciones', '').strip()
        
        if not insumo_id or not cantidad:
            return JsonResponse({'success': False, 'message': 'El insumo y la cantidad son obligatorios.'}, status=400)
        
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                return JsonResponse({'success': False, 'message': 'La cantidad debe ser mayor a 0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'La cantidad debe ser un número válido.'}, status=400)
        
        insumo = get_object_or_404(Insumo, id=insumo_id)
        
        # Precio unitario
        precio_unitario_decimal = None
        if precio_unitario:
            try:
                precio_unitario_decimal = Decimal(str(precio_unitario))
            except:
                precio_unitario_decimal = insumo.precio_unitario
        else:
            precio_unitario_decimal = insumo.precio_unitario
        
        # Crear solicitud
        solicitud = SolicitudInsumo.objects.create(
            pedido=pedido,
            proveedor=pedido.proveedor,
            insumo=insumo,
            cantidad_solicitada=cantidad_int,
            fecha_entrega_esperada=pedido.fecha_entrega_esperada,
            observaciones=observaciones,
            precio_unitario=precio_unitario_decimal,
            solicitado_por=perfil
        )
        
        # Recalcular monto total del pedido
        pedido.monto_total = pedido.calcular_monto_total()
        pedido.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Insumo "{insumo.nombre}" agregado al pedido correctamente.',
            'solicitud_id': solicitud.id
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def enviar_pedido_correo(request, pedido_id):
    """Vista para enviar el pedido por correo al proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido.objects.prefetch_related('solicitudes__insumo'), id=pedido_id)
        
        if not pedido.solicitudes.exists():
            return JsonResponse({'success': False, 'message': 'El pedido no tiene insumos. Agrega insumos antes de enviarlo.'}, status=400)
        
        if pedido.estado not in ['borrador', 'pendiente']:
            return JsonResponse({'success': False, 'message': 'Solo se pueden enviar pedidos en estado borrador o pendiente.'}, status=400)
        
        try:
            # Construir mensaje del correo
            nombre_proveedor = normalizar_texto(pedido.proveedor.contacto_nombre or pedido.proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            
            asunto = f'Pedido de Insumos - {pedido.numero_pedido}'
            
            # Detalles del pedido
            fecha_entrega_str = pedido.fecha_entrega_esperada.strftime('%d/%m/%Y')
            fecha_pedido_str = pedido.fecha_pedido.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para realizar el siguiente pedido de insumos:

================================================================================
DETALLES DEL PEDIDO
================================================================================

* Numero de Pedido: {pedido.numero_pedido}
* Fecha del Pedido: {fecha_pedido_str}
* Fecha de Entrega Esperada: {fecha_entrega_str}

================================================================================
INSUMOS SOLICITADOS
================================================================================

"""
            
            # Agregar cada insumo
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                mensaje += f"* {nombre_insumo}\n"
                mensaje += f"  - Cantidad: {solicitud.cantidad_solicitada} {unidad_medida}\n"
                mensaje += f"  - Precio Unitario: {precio_str}\n"
                mensaje += f"  - Monto Total: {monto_str}\n"
                if solicitud.observaciones:
                    obs_norm = normalizar_texto(solicitud.observaciones)
                    mensaje += f"  - Observaciones: {obs_norm}\n"
                mensaje += "\n"
            
            # Monto total del pedido
            if pedido.monto_total:
                mensaje += f"================================================================================\n"
                mensaje += f"MONTO TOTAL DEL PEDIDO: ${pedido.monto_total:,.0f}\n"
                mensaje += f"================================================================================\n\n"
            
            # Observaciones generales
            if pedido.observaciones:
                obs_gen = normalizar_texto(pedido.observaciones)
                mensaje += f"Observaciones Generales:\n{obs_gen}\n\n"
            
            mensaje += f"""================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de este pedido y la disponibilidad de los 
insumos requeridos a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Preparar lista de insumos para el template
            insumos_list = []
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                insumos_list.append({
                    'nombre': nombre_insumo,
                    'cantidad': solicitud.cantidad_solicitada,
                    'unidad': unidad_medida,
                    'precio_unitario': precio_str,
                    'monto_total': monto_str,
                    'observaciones': normalizar_texto(solicitud.observaciones) if solicitud.observaciones else None,
                })
            
            # Renderizar template HTML
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/pedido_proveedor.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_pedido': pedido.numero_pedido,
                'fecha_pedido': pedido.fecha_pedido,
                'fecha_entrega_esperada': pedido.fecha_entrega_esperada,
                'insumos': insumos_list,
                'monto_total': f"${pedido.monto_total:,.0f}" if pedido.monto_total else None,
                'observaciones_generales': normalizar_texto(pedido.observaciones) if pedido.observaciones else None,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            # Enviar correo
            email = EmailMessage(
                subject=asunto,
                body=mensaje_html,
                from_email=email_clinica,
                to=[pedido.proveedor.email],
            )
            email.content_subtype = "html"  # Indicar que es HTML
            
            email.send(fail_silently=False)
            
            # Actualizar pedido
            pedido.correo_enviado = True
            pedido.fecha_envio_correo = timezone.now()
            pedido.estado = 'enviado'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido {pedido.numero_pedido} enviado correctamente a {pedido.proveedor.email}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al enviar el correo: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)









def gestor_pedidos(request):
    """Vista principal para gestionar pedidos a proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar pedidos.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Filtros
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    proveedor_id = request.GET.get('proveedor_id', '')
    
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').all()
    
    if search:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=search) |
            Q(proveedor__nombre__icontains=search) |
            Q(proveedor__rut__icontains=search)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    if proveedor_id:
        pedidos = pedidos.filter(proveedor_id=proveedor_id)
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Estadísticas
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # Obtener proveedores para filtro
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'proveedores': proveedores,
        'search': search,
        'estado': estado,
        'proveedor_id': proveedor_id,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'citas/proveedores/gestor_pedidos.html', context)


@login_required
def obtener_insumos_proveedor(request, proveedor_id):
    """Vista AJAX para obtener los insumos de un proveedor"""
    try:
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
        insumos = Insumo.objects.filter(proveedor_principal=proveedor).order_by('nombre')
        
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.id,
                'nombre': insumo.nombre,
                'categoria': insumo.get_categoria_display(),
                'precio_unitario': str(insumo.precio_unitario) if insumo.precio_unitario else None,
                'unidad_medida': insumo.unidad_medida,
                'stock_actual': insumo.cantidad_actual,
            })
        
        return JsonResponse({
            'success': True,
            'insumos': insumos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def crear_pedido(request):
    """Vista para crear un nuevo pedido"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            # Crear pedido
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                estado='borrador',
                registrar_como_egreso=registrar_como_egreso,
                creado_por=perfil
            )
            
            # Procesar insumos seleccionados
            insumos_seleccionados = request.POST.getlist('insumos[]')
            if insumos_seleccionados:
                from proveedores.models import SolicitudInsumo
                for insumo_id in insumos_seleccionados:
                    cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                    try:
                        cantidad_int = int(cantidad)
                        if cantidad_int > 0:
                            insumo = get_object_or_404(Insumo, id=insumo_id)
                            SolicitudInsumo.objects.create(
                                pedido=pedido,
                                proveedor=proveedor,
                                insumo=insumo,
                                cantidad_solicitada=cantidad_int,
                                fecha_entrega_esperada=fecha_entrega_obj,
                                precio_unitario=insumo.precio_unitario or None,
                                solicitado_por=perfil
                            )
                    except (ValueError, Insumo.DoesNotExist) as e:
                        # Log del error pero continuar con los demás insumos
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error al agregar insumo {insumo_id} al pedido: {str(e)}')
                        continue
            
            if insumos_seleccionados:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente con {len(insumos_seleccionados)} insumo(s).')
            else:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente. Ahora puedes agregar insumos al pedido.')
            
            return redirect('detalle_pedido', pedido_id=pedido.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
    }
    
    return render(request, 'citas/proveedores/crear_pedido.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver y gestionar un pedido específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes__insumo'), id=pedido_id)
    
    # Obtener insumos disponibles para agregar (priorizar los del proveedor)
    insumos_proveedor = Insumo.objects.filter(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos_otros = Insumo.objects.exclude(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos = list(insumos_proveedor) + list(insumos_otros)
    
    context = {
        'perfil': perfil,
        'pedido': pedido,
        'insumos': insumos,
    }
    
    return render(request, 'citas/proveedores/detalle_pedido.html', context)


@login_required
def agregar_insumo_pedido(request, pedido_id):
    """Vista AJAX para agregar un insumo a un pedido"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.estado != 'borrador':
            return JsonResponse({'success': False, 'message': 'Solo se pueden agregar insumos a pedidos en estado borrador.'}, status=400)
        
        insumo_id = request.POST.get('insumo_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario', '')
        observaciones = request.POST.get('observaciones', '').strip()
        
        if not insumo_id or not cantidad:
            return JsonResponse({'success': False, 'message': 'El insumo y la cantidad son obligatorios.'}, status=400)
        
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                return JsonResponse({'success': False, 'message': 'La cantidad debe ser mayor a 0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'La cantidad debe ser un número válido.'}, status=400)
        
        insumo = get_object_or_404(Insumo, id=insumo_id)
        
        # Precio unitario
        precio_unitario_decimal = None
        if precio_unitario:
            try:
                precio_unitario_decimal = Decimal(str(precio_unitario))
            except:
                precio_unitario_decimal = insumo.precio_unitario
        else:
            precio_unitario_decimal = insumo.precio_unitario
        
        # Crear solicitud
        solicitud = SolicitudInsumo.objects.create(
            pedido=pedido,
            proveedor=pedido.proveedor,
            insumo=insumo,
            cantidad_solicitada=cantidad_int,
            fecha_entrega_esperada=pedido.fecha_entrega_esperada,
            observaciones=observaciones,
            precio_unitario=precio_unitario_decimal,
            solicitado_por=perfil
        )
        
        # Recalcular monto total del pedido
        pedido.monto_total = pedido.calcular_monto_total()
        pedido.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Insumo "{insumo.nombre}" agregado al pedido correctamente.',
            'solicitud_id': solicitud.id
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def enviar_pedido_correo(request, pedido_id):
    """Vista para enviar el pedido por correo al proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido.objects.prefetch_related('solicitudes__insumo'), id=pedido_id)
        
        if not pedido.solicitudes.exists():
            return JsonResponse({'success': False, 'message': 'El pedido no tiene insumos. Agrega insumos antes de enviarlo.'}, status=400)
        
        if pedido.estado not in ['borrador', 'pendiente']:
            return JsonResponse({'success': False, 'message': 'Solo se pueden enviar pedidos en estado borrador o pendiente.'}, status=400)
        
        try:
            # Construir mensaje del correo
            nombre_proveedor = normalizar_texto(pedido.proveedor.contacto_nombre or pedido.proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            
            asunto = f'Pedido de Insumos - {pedido.numero_pedido}'
            
            # Detalles del pedido
            fecha_entrega_str = pedido.fecha_entrega_esperada.strftime('%d/%m/%Y')
            fecha_pedido_str = pedido.fecha_pedido.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para realizar el siguiente pedido de insumos:

================================================================================
DETALLES DEL PEDIDO
================================================================================

* Numero de Pedido: {pedido.numero_pedido}
* Fecha del Pedido: {fecha_pedido_str}
* Fecha de Entrega Esperada: {fecha_entrega_str}

================================================================================
INSUMOS SOLICITADOS
================================================================================

"""
            
            # Agregar cada insumo
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                mensaje += f"* {nombre_insumo}\n"
                mensaje += f"  - Cantidad: {solicitud.cantidad_solicitada} {unidad_medida}\n"
                mensaje += f"  - Precio Unitario: {precio_str}\n"
                mensaje += f"  - Monto Total: {monto_str}\n"
                if solicitud.observaciones:
                    obs_norm = normalizar_texto(solicitud.observaciones)
                    mensaje += f"  - Observaciones: {obs_norm}\n"
                mensaje += "\n"
            
            # Monto total del pedido
            if pedido.monto_total:
                mensaje += f"================================================================================\n"
                mensaje += f"MONTO TOTAL DEL PEDIDO: ${pedido.monto_total:,.0f}\n"
                mensaje += f"================================================================================\n\n"
            
            # Observaciones generales
            if pedido.observaciones:
                obs_gen = normalizar_texto(pedido.observaciones)
                mensaje += f"Observaciones Generales:\n{obs_gen}\n\n"
            
            mensaje += f"""================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de este pedido y la disponibilidad de los 
insumos requeridos a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Preparar lista de insumos para el template
            insumos_list = []
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                insumos_list.append({
                    'nombre': nombre_insumo,
                    'cantidad': solicitud.cantidad_solicitada,
                    'unidad': unidad_medida,
                    'precio_unitario': precio_str,
                    'monto_total': monto_str,
                    'observaciones': normalizar_texto(solicitud.observaciones) if solicitud.observaciones else None,
                })
            
            # Renderizar template HTML
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/pedido_proveedor.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_pedido': pedido.numero_pedido,
                'fecha_pedido': pedido.fecha_pedido,
                'fecha_entrega_esperada': pedido.fecha_entrega_esperada,
                'insumos': insumos_list,
                'monto_total': f"${pedido.monto_total:,.0f}" if pedido.monto_total else None,
                'observaciones_generales': normalizar_texto(pedido.observaciones) if pedido.observaciones else None,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            # Enviar correo
            email = EmailMessage(
                subject=asunto,
                body=mensaje_html,
                from_email=email_clinica,
                to=[pedido.proveedor.email],
            )
            email.content_subtype = "html"  # Indicar que es HTML
            
            email.send(fail_silently=False)
            
            # Actualizar pedido
            pedido.correo_enviado = True
            pedido.fecha_envio_correo = timezone.now()
            pedido.estado = 'enviado'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido {pedido.numero_pedido} enviado correctamente a {pedido.proveedor.email}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al enviar el correo: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)









def gestor_pedidos(request):
    """Vista principal para gestionar pedidos a proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar pedidos.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Filtros
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    proveedor_id = request.GET.get('proveedor_id', '')
    
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').all()
    
    if search:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=search) |
            Q(proveedor__nombre__icontains=search) |
            Q(proveedor__rut__icontains=search)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    if proveedor_id:
        pedidos = pedidos.filter(proveedor_id=proveedor_id)
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Estadísticas
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # Obtener proveedores para filtro
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'proveedores': proveedores,
        'search': search,
        'estado': estado,
        'proveedor_id': proveedor_id,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'citas/proveedores/gestor_pedidos.html', context)


@login_required
def obtener_insumos_proveedor(request, proveedor_id):
    """Vista AJAX para obtener los insumos de un proveedor"""
    try:
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
        insumos = Insumo.objects.filter(proveedor_principal=proveedor).order_by('nombre')
        
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.id,
                'nombre': insumo.nombre,
                'categoria': insumo.get_categoria_display(),
                'precio_unitario': str(insumo.precio_unitario) if insumo.precio_unitario else None,
                'unidad_medida': insumo.unidad_medida,
                'stock_actual': insumo.cantidad_actual,
            })
        
        return JsonResponse({
            'success': True,
            'insumos': insumos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def crear_pedido(request):
    """Vista para crear un nuevo pedido"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            # Crear pedido
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                estado='borrador',
                registrar_como_egreso=registrar_como_egreso,
                creado_por=perfil
            )
            
            # Procesar insumos seleccionados
            insumos_seleccionados = request.POST.getlist('insumos[]')
            if insumos_seleccionados:
                from proveedores.models import SolicitudInsumo
                for insumo_id in insumos_seleccionados:
                    cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                    try:
                        cantidad_int = int(cantidad)
                        if cantidad_int > 0:
                            insumo = get_object_or_404(Insumo, id=insumo_id)
                            SolicitudInsumo.objects.create(
                                pedido=pedido,
                                proveedor=proveedor,
                                insumo=insumo,
                                cantidad_solicitada=cantidad_int,
                                fecha_entrega_esperada=fecha_entrega_obj,
                                precio_unitario=insumo.precio_unitario or None,
                                solicitado_por=perfil
                            )
                    except (ValueError, Insumo.DoesNotExist) as e:
                        # Log del error pero continuar con los demás insumos
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error al agregar insumo {insumo_id} al pedido: {str(e)}')
                        continue
            
            if insumos_seleccionados:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente con {len(insumos_seleccionados)} insumo(s).')
            else:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente. Ahora puedes agregar insumos al pedido.')
            
            return redirect('detalle_pedido', pedido_id=pedido.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
    }
    
    return render(request, 'citas/proveedores/crear_pedido.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver y gestionar un pedido específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes__insumo'), id=pedido_id)
    
    # Obtener insumos disponibles para agregar (priorizar los del proveedor)
    insumos_proveedor = Insumo.objects.filter(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos_otros = Insumo.objects.exclude(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos = list(insumos_proveedor) + list(insumos_otros)
    
    context = {
        'perfil': perfil,
        'pedido': pedido,
        'insumos': insumos,
    }
    
    return render(request, 'citas/proveedores/detalle_pedido.html', context)


@login_required
def agregar_insumo_pedido(request, pedido_id):
    """Vista AJAX para agregar un insumo a un pedido"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.estado != 'borrador':
            return JsonResponse({'success': False, 'message': 'Solo se pueden agregar insumos a pedidos en estado borrador.'}, status=400)
        
        insumo_id = request.POST.get('insumo_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario', '')
        observaciones = request.POST.get('observaciones', '').strip()
        
        if not insumo_id or not cantidad:
            return JsonResponse({'success': False, 'message': 'El insumo y la cantidad son obligatorios.'}, status=400)
        
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                return JsonResponse({'success': False, 'message': 'La cantidad debe ser mayor a 0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'La cantidad debe ser un número válido.'}, status=400)
        
        insumo = get_object_or_404(Insumo, id=insumo_id)
        
        # Precio unitario
        precio_unitario_decimal = None
        if precio_unitario:
            try:
                precio_unitario_decimal = Decimal(str(precio_unitario))
            except:
                precio_unitario_decimal = insumo.precio_unitario
        else:
            precio_unitario_decimal = insumo.precio_unitario
        
        # Crear solicitud
        solicitud = SolicitudInsumo.objects.create(
            pedido=pedido,
            proveedor=pedido.proveedor,
            insumo=insumo,
            cantidad_solicitada=cantidad_int,
            fecha_entrega_esperada=pedido.fecha_entrega_esperada,
            observaciones=observaciones,
            precio_unitario=precio_unitario_decimal,
            solicitado_por=perfil
        )
        
        # Recalcular monto total del pedido
        pedido.monto_total = pedido.calcular_monto_total()
        pedido.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Insumo "{insumo.nombre}" agregado al pedido correctamente.',
            'solicitud_id': solicitud.id
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def enviar_pedido_correo(request, pedido_id):
    """Vista para enviar el pedido por correo al proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido.objects.prefetch_related('solicitudes__insumo'), id=pedido_id)
        
        if not pedido.solicitudes.exists():
            return JsonResponse({'success': False, 'message': 'El pedido no tiene insumos. Agrega insumos antes de enviarlo.'}, status=400)
        
        if pedido.estado not in ['borrador', 'pendiente']:
            return JsonResponse({'success': False, 'message': 'Solo se pueden enviar pedidos en estado borrador o pendiente.'}, status=400)
        
        try:
            # Construir mensaje del correo
            nombre_proveedor = normalizar_texto(pedido.proveedor.contacto_nombre or pedido.proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            
            asunto = f'Pedido de Insumos - {pedido.numero_pedido}'
            
            # Detalles del pedido
            fecha_entrega_str = pedido.fecha_entrega_esperada.strftime('%d/%m/%Y')
            fecha_pedido_str = pedido.fecha_pedido.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para realizar el siguiente pedido de insumos:

================================================================================
DETALLES DEL PEDIDO
================================================================================

* Numero de Pedido: {pedido.numero_pedido}
* Fecha del Pedido: {fecha_pedido_str}
* Fecha de Entrega Esperada: {fecha_entrega_str}

================================================================================
INSUMOS SOLICITADOS
================================================================================

"""
            
            # Agregar cada insumo
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                mensaje += f"* {nombre_insumo}\n"
                mensaje += f"  - Cantidad: {solicitud.cantidad_solicitada} {unidad_medida}\n"
                mensaje += f"  - Precio Unitario: {precio_str}\n"
                mensaje += f"  - Monto Total: {monto_str}\n"
                if solicitud.observaciones:
                    obs_norm = normalizar_texto(solicitud.observaciones)
                    mensaje += f"  - Observaciones: {obs_norm}\n"
                mensaje += "\n"
            
            # Monto total del pedido
            if pedido.monto_total:
                mensaje += f"================================================================================\n"
                mensaje += f"MONTO TOTAL DEL PEDIDO: ${pedido.monto_total:,.0f}\n"
                mensaje += f"================================================================================\n\n"
            
            # Observaciones generales
            if pedido.observaciones:
                obs_gen = normalizar_texto(pedido.observaciones)
                mensaje += f"Observaciones Generales:\n{obs_gen}\n\n"
            
            mensaje += f"""================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de este pedido y la disponibilidad de los 
insumos requeridos a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Preparar lista de insumos para el template
            insumos_list = []
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                insumos_list.append({
                    'nombre': nombre_insumo,
                    'cantidad': solicitud.cantidad_solicitada,
                    'unidad': unidad_medida,
                    'precio_unitario': precio_str,
                    'monto_total': monto_str,
                    'observaciones': normalizar_texto(solicitud.observaciones) if solicitud.observaciones else None,
                })
            
            # Renderizar template HTML
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/pedido_proveedor.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_pedido': pedido.numero_pedido,
                'fecha_pedido': pedido.fecha_pedido,
                'fecha_entrega_esperada': pedido.fecha_entrega_esperada,
                'insumos': insumos_list,
                'monto_total': f"${pedido.monto_total:,.0f}" if pedido.monto_total else None,
                'observaciones_generales': normalizar_texto(pedido.observaciones) if pedido.observaciones else None,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            # Enviar correo
            email = EmailMessage(
                subject=asunto,
                body=mensaje_html,
                from_email=email_clinica,
                to=[pedido.proveedor.email],
            )
            email.content_subtype = "html"  # Indicar que es HTML
            
            email.send(fail_silently=False)
            
            # Actualizar pedido
            pedido.correo_enviado = True
            pedido.fecha_envio_correo = timezone.now()
            pedido.estado = 'enviado'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido {pedido.numero_pedido} enviado correctamente a {pedido.proveedor.email}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al enviar el correo: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)









def gestor_pedidos(request):
    """Vista principal para gestionar pedidos a proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar pedidos.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Filtros
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    proveedor_id = request.GET.get('proveedor_id', '')
    
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').all()
    
    if search:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=search) |
            Q(proveedor__nombre__icontains=search) |
            Q(proveedor__rut__icontains=search)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    if proveedor_id:
        pedidos = pedidos.filter(proveedor_id=proveedor_id)
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Estadísticas
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # Obtener proveedores para filtro
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'proveedores': proveedores,
        'search': search,
        'estado': estado,
        'proveedor_id': proveedor_id,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'citas/proveedores/gestor_pedidos.html', context)


@login_required
def obtener_insumos_proveedor(request, proveedor_id):
    """Vista AJAX para obtener los insumos de un proveedor"""
    try:
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
        insumos = Insumo.objects.filter(proveedor_principal=proveedor).order_by('nombre')
        
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.id,
                'nombre': insumo.nombre,
                'categoria': insumo.get_categoria_display(),
                'precio_unitario': str(insumo.precio_unitario) if insumo.precio_unitario else None,
                'unidad_medida': insumo.unidad_medida,
                'stock_actual': insumo.cantidad_actual,
            })
        
        return JsonResponse({
            'success': True,
            'insumos': insumos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def crear_pedido(request):
    """Vista para crear un nuevo pedido"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            # Crear pedido
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                estado='borrador',
                registrar_como_egreso=registrar_como_egreso,
                creado_por=perfil
            )
            
            # Procesar insumos seleccionados
            insumos_seleccionados = request.POST.getlist('insumos[]')
            if insumos_seleccionados:
                from proveedores.models import SolicitudInsumo
                for insumo_id in insumos_seleccionados:
                    cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                    try:
                        cantidad_int = int(cantidad)
                        if cantidad_int > 0:
                            insumo = get_object_or_404(Insumo, id=insumo_id)
                            SolicitudInsumo.objects.create(
                                pedido=pedido,
                                proveedor=proveedor,
                                insumo=insumo,
                                cantidad_solicitada=cantidad_int,
                                fecha_entrega_esperada=fecha_entrega_obj,
                                precio_unitario=insumo.precio_unitario or None,
                                solicitado_por=perfil
                            )
                    except (ValueError, Insumo.DoesNotExist) as e:
                        # Log del error pero continuar con los demás insumos
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error al agregar insumo {insumo_id} al pedido: {str(e)}')
                        continue
            
            if insumos_seleccionados:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente con {len(insumos_seleccionados)} insumo(s).')
            else:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente. Ahora puedes agregar insumos al pedido.')
            
            return redirect('detalle_pedido', pedido_id=pedido.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
    }
    
    return render(request, 'citas/proveedores/crear_pedido.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver y gestionar un pedido específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes__insumo'), id=pedido_id)
    
    # Obtener insumos disponibles para agregar (priorizar los del proveedor)
    insumos_proveedor = Insumo.objects.filter(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos_otros = Insumo.objects.exclude(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos = list(insumos_proveedor) + list(insumos_otros)
    
    context = {
        'perfil': perfil,
        'pedido': pedido,
        'insumos': insumos,
    }
    
    return render(request, 'citas/proveedores/detalle_pedido.html', context)


@login_required
def agregar_insumo_pedido(request, pedido_id):
    """Vista AJAX para agregar un insumo a un pedido"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.estado != 'borrador':
            return JsonResponse({'success': False, 'message': 'Solo se pueden agregar insumos a pedidos en estado borrador.'}, status=400)
        
        insumo_id = request.POST.get('insumo_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario', '')
        observaciones = request.POST.get('observaciones', '').strip()
        
        if not insumo_id or not cantidad:
            return JsonResponse({'success': False, 'message': 'El insumo y la cantidad son obligatorios.'}, status=400)
        
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                return JsonResponse({'success': False, 'message': 'La cantidad debe ser mayor a 0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'La cantidad debe ser un número válido.'}, status=400)
        
        insumo = get_object_or_404(Insumo, id=insumo_id)
        
        # Precio unitario
        precio_unitario_decimal = None
        if precio_unitario:
            try:
                precio_unitario_decimal = Decimal(str(precio_unitario))
            except:
                precio_unitario_decimal = insumo.precio_unitario
        else:
            precio_unitario_decimal = insumo.precio_unitario
        
        # Crear solicitud
        solicitud = SolicitudInsumo.objects.create(
            pedido=pedido,
            proveedor=pedido.proveedor,
            insumo=insumo,
            cantidad_solicitada=cantidad_int,
            fecha_entrega_esperada=pedido.fecha_entrega_esperada,
            observaciones=observaciones,
            precio_unitario=precio_unitario_decimal,
            solicitado_por=perfil
        )
        
        # Recalcular monto total del pedido
        pedido.monto_total = pedido.calcular_monto_total()
        pedido.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Insumo "{insumo.nombre}" agregado al pedido correctamente.',
            'solicitud_id': solicitud.id
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def enviar_pedido_correo(request, pedido_id):
    """Vista para enviar el pedido por correo al proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido.objects.prefetch_related('solicitudes__insumo'), id=pedido_id)
        
        if not pedido.solicitudes.exists():
            return JsonResponse({'success': False, 'message': 'El pedido no tiene insumos. Agrega insumos antes de enviarlo.'}, status=400)
        
        if pedido.estado not in ['borrador', 'pendiente']:
            return JsonResponse({'success': False, 'message': 'Solo se pueden enviar pedidos en estado borrador o pendiente.'}, status=400)
        
        try:
            # Construir mensaje del correo
            nombre_proveedor = normalizar_texto(pedido.proveedor.contacto_nombre or pedido.proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            
            asunto = f'Pedido de Insumos - {pedido.numero_pedido}'
            
            # Detalles del pedido
            fecha_entrega_str = pedido.fecha_entrega_esperada.strftime('%d/%m/%Y')
            fecha_pedido_str = pedido.fecha_pedido.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para realizar el siguiente pedido de insumos:

================================================================================
DETALLES DEL PEDIDO
================================================================================

* Numero de Pedido: {pedido.numero_pedido}
* Fecha del Pedido: {fecha_pedido_str}
* Fecha de Entrega Esperada: {fecha_entrega_str}

================================================================================
INSUMOS SOLICITADOS
================================================================================

"""
            
            # Agregar cada insumo
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                mensaje += f"* {nombre_insumo}\n"
                mensaje += f"  - Cantidad: {solicitud.cantidad_solicitada} {unidad_medida}\n"
                mensaje += f"  - Precio Unitario: {precio_str}\n"
                mensaje += f"  - Monto Total: {monto_str}\n"
                if solicitud.observaciones:
                    obs_norm = normalizar_texto(solicitud.observaciones)
                    mensaje += f"  - Observaciones: {obs_norm}\n"
                mensaje += "\n"
            
            # Monto total del pedido
            if pedido.monto_total:
                mensaje += f"================================================================================\n"
                mensaje += f"MONTO TOTAL DEL PEDIDO: ${pedido.monto_total:,.0f}\n"
                mensaje += f"================================================================================\n\n"
            
            # Observaciones generales
            if pedido.observaciones:
                obs_gen = normalizar_texto(pedido.observaciones)
                mensaje += f"Observaciones Generales:\n{obs_gen}\n\n"
            
            mensaje += f"""================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de este pedido y la disponibilidad de los 
insumos requeridos a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Preparar lista de insumos para el template
            insumos_list = []
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                insumos_list.append({
                    'nombre': nombre_insumo,
                    'cantidad': solicitud.cantidad_solicitada,
                    'unidad': unidad_medida,
                    'precio_unitario': precio_str,
                    'monto_total': monto_str,
                    'observaciones': normalizar_texto(solicitud.observaciones) if solicitud.observaciones else None,
                })
            
            # Renderizar template HTML
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/pedido_proveedor.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_pedido': pedido.numero_pedido,
                'fecha_pedido': pedido.fecha_pedido,
                'fecha_entrega_esperada': pedido.fecha_entrega_esperada,
                'insumos': insumos_list,
                'monto_total': f"${pedido.monto_total:,.0f}" if pedido.monto_total else None,
                'observaciones_generales': normalizar_texto(pedido.observaciones) if pedido.observaciones else None,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            # Enviar correo
            email = EmailMessage(
                subject=asunto,
                body=mensaje_html,
                from_email=email_clinica,
                to=[pedido.proveedor.email],
            )
            email.content_subtype = "html"  # Indicar que es HTML
            
            email.send(fail_silently=False)
            
            # Actualizar pedido
            pedido.correo_enviado = True
            pedido.fecha_envio_correo = timezone.now()
            pedido.estado = 'enviado'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido {pedido.numero_pedido} enviado correctamente a {pedido.proveedor.email}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al enviar el correo: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)









def gestor_pedidos(request):
    """Vista principal para gestionar pedidos a proveedores"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar pedidos.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Filtros
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    proveedor_id = request.GET.get('proveedor_id', '')
    
    pedidos = Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes').all()
    
    if search:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=search) |
            Q(proveedor__nombre__icontains=search) |
            Q(proveedor__rut__icontains=search)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    if proveedor_id:
        pedidos = pedidos.filter(proveedor_id=proveedor_id)
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Estadísticas
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado__in=['borrador', 'pendiente']).count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_recibidos = Pedido.objects.filter(estado='recibido').count()
    
    estadisticas = {
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recibidos': pedidos_recibidos,
    }
    
    # Obtener proveedores para filtro
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'pedidos': pedidos,
        'estadisticas': estadisticas,
        'proveedores': proveedores,
        'search': search,
        'estado': estado,
        'proveedor_id': proveedor_id,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'citas/proveedores/gestor_pedidos.html', context)


@login_required
def obtener_insumos_proveedor(request, proveedor_id):
    """Vista AJAX para obtener los insumos de un proveedor"""
    try:
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
        insumos = Insumo.objects.filter(proveedor_principal=proveedor).order_by('nombre')
        
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.id,
                'nombre': insumo.nombre,
                'categoria': insumo.get_categoria_display(),
                'precio_unitario': str(insumo.precio_unitario) if insumo.precio_unitario else None,
                'unidad_medida': insumo.unidad_medida,
                'stock_actual': insumo.cantidad_actual,
            })
        
        return JsonResponse({
            'success': True,
            'insumos': insumos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def crear_pedido(request):
    """Vista para crear un nuevo pedido"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor_id')
            fecha_entrega = request.POST.get('fecha_entrega')
            observaciones = request.POST.get('observaciones', '').strip()
            registrar_como_egreso = request.POST.get('registrar_como_egreso') == 'on'
            
            # Validaciones
            if not proveedor_id:
                messages.error(request, 'El proveedor es obligatorio.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            if not fecha_entrega:
                messages.error(request, 'La fecha de entrega es obligatoria.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, activo=True)
            
            try:
                fecha_entrega_obj = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
            
            # Crear pedido
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha_entrega_esperada=fecha_entrega_obj,
                observaciones=observaciones,
                estado='borrador',
                registrar_como_egreso=registrar_como_egreso,
                creado_por=perfil
            )
            
            # Procesar insumos seleccionados
            insumos_seleccionados = request.POST.getlist('insumos[]')
            if insumos_seleccionados:
                from proveedores.models import SolicitudInsumo
                for insumo_id in insumos_seleccionados:
                    cantidad = request.POST.get(f'cantidad_{insumo_id}', '1')
                    try:
                        cantidad_int = int(cantidad)
                        if cantidad_int > 0:
                            insumo = get_object_or_404(Insumo, id=insumo_id)
                            SolicitudInsumo.objects.create(
                                pedido=pedido,
                                proveedor=proveedor,
                                insumo=insumo,
                                cantidad_solicitada=cantidad_int,
                                fecha_entrega_esperada=fecha_entrega_obj,
                                precio_unitario=insumo.precio_unitario or None,
                                solicitado_por=perfil
                            )
                    except (ValueError, Insumo.DoesNotExist) as e:
                        # Log del error pero continuar con los demás insumos
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error al agregar insumo {insumo_id} al pedido: {str(e)}')
                        continue
            
            if insumos_seleccionados:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente con {len(insumos_seleccionados)} insumo(s).')
            else:
                messages.success(request, f'Pedido {pedido.numero_pedido} creado correctamente. Ahora puedes agregar insumos al pedido.')
            
            return redirect('detalle_pedido', pedido_id=pedido.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el pedido: {str(e)}')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'perfil': perfil,
        'proveedores': proveedores,
    }
    
    return render(request, 'citas/proveedores/crear_pedido.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver y gestionar un pedido específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver pedidos.')
            return redirect(reverse('gestor_inventario_unificado') + '?seccion=pedidos')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    pedido = get_object_or_404(Pedido.objects.select_related('proveedor', 'creado_por').prefetch_related('solicitudes__insumo'), id=pedido_id)
    
    # Obtener insumos disponibles para agregar (priorizar los del proveedor)
    insumos_proveedor = Insumo.objects.filter(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos_otros = Insumo.objects.exclude(proveedor_principal=pedido.proveedor).order_by('nombre')
    insumos = list(insumos_proveedor) + list(insumos_otros)
    
    context = {
        'perfil': perfil,
        'pedido': pedido,
        'insumos': insumos,
    }
    
    return render(request, 'citas/proveedores/detalle_pedido.html', context)


@login_required
def agregar_insumo_pedido(request, pedido_id):
    """Vista AJAX para agregar un insumo a un pedido"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.estado != 'borrador':
            return JsonResponse({'success': False, 'message': 'Solo se pueden agregar insumos a pedidos en estado borrador.'}, status=400)
        
        insumo_id = request.POST.get('insumo_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario', '')
        observaciones = request.POST.get('observaciones', '').strip()
        
        if not insumo_id or not cantidad:
            return JsonResponse({'success': False, 'message': 'El insumo y la cantidad son obligatorios.'}, status=400)
        
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                return JsonResponse({'success': False, 'message': 'La cantidad debe ser mayor a 0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'La cantidad debe ser un número válido.'}, status=400)
        
        insumo = get_object_or_404(Insumo, id=insumo_id)
        
        # Precio unitario
        precio_unitario_decimal = None
        if precio_unitario:
            try:
                precio_unitario_decimal = Decimal(str(precio_unitario))
            except:
                precio_unitario_decimal = insumo.precio_unitario
        else:
            precio_unitario_decimal = insumo.precio_unitario
        
        # Crear solicitud
        solicitud = SolicitudInsumo.objects.create(
            pedido=pedido,
            proveedor=pedido.proveedor,
            insumo=insumo,
            cantidad_solicitada=cantidad_int,
            fecha_entrega_esperada=pedido.fecha_entrega_esperada,
            observaciones=observaciones,
            precio_unitario=precio_unitario_decimal,
            solicitado_por=perfil
        )
        
        # Recalcular monto total del pedido
        pedido.monto_total = pedido.calcular_monto_total()
        pedido.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Insumo "{insumo.nombre}" agregado al pedido correctamente.',
            'solicitud_id': solicitud.id
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def enviar_pedido_correo(request, pedido_id):
    """Vista para enviar el pedido por correo al proveedor"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            if not perfil.es_administrativo():
                return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        except Perfil.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'}, status=403)
        
        pedido = get_object_or_404(Pedido.objects.prefetch_related('solicitudes__insumo'), id=pedido_id)
        
        if not pedido.solicitudes.exists():
            return JsonResponse({'success': False, 'message': 'El pedido no tiene insumos. Agrega insumos antes de enviarlo.'}, status=400)
        
        if pedido.estado not in ['borrador', 'pendiente']:
            return JsonResponse({'success': False, 'message': 'Solo se pueden enviar pedidos en estado borrador o pendiente.'}, status=400)
        
        try:
            # Construir mensaje del correo
            nombre_proveedor = normalizar_texto(pedido.proveedor.contacto_nombre or pedido.proveedor.nombre)
            nombre_solicitante = normalizar_texto(perfil.nombre_completo)
            
            asunto = f'Pedido de Insumos - {pedido.numero_pedido}'
            
            # Detalles del pedido
            fecha_entrega_str = pedido.fecha_entrega_esperada.strftime('%d/%m/%Y')
            fecha_pedido_str = pedido.fecha_pedido.strftime('%d/%m/%Y')
            
            mensaje = f"""Estimado/a {nombre_proveedor},

Por medio de la presente, nos dirigimos a usted para realizar el siguiente pedido de insumos:

================================================================================
DETALLES DEL PEDIDO
================================================================================

* Numero de Pedido: {pedido.numero_pedido}
* Fecha del Pedido: {fecha_pedido_str}
* Fecha de Entrega Esperada: {fecha_entrega_str}

================================================================================
INSUMOS SOLICITADOS
================================================================================

"""
            
            # Agregar cada insumo
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                mensaje += f"* {nombre_insumo}\n"
                mensaje += f"  - Cantidad: {solicitud.cantidad_solicitada} {unidad_medida}\n"
                mensaje += f"  - Precio Unitario: {precio_str}\n"
                mensaje += f"  - Monto Total: {monto_str}\n"
                if solicitud.observaciones:
                    obs_norm = normalizar_texto(solicitud.observaciones)
                    mensaje += f"  - Observaciones: {obs_norm}\n"
                mensaje += "\n"
            
            # Monto total del pedido
            if pedido.monto_total:
                mensaje += f"================================================================================\n"
                mensaje += f"MONTO TOTAL DEL PEDIDO: ${pedido.monto_total:,.0f}\n"
                mensaje += f"================================================================================\n\n"
            
            # Observaciones generales
            if pedido.observaciones:
                obs_gen = normalizar_texto(pedido.observaciones)
                mensaje += f"Observaciones Generales:\n{obs_gen}\n\n"
            
            mensaje += f"""================================================================================
INFORMACION DEL SOLICITANTE
================================================================================

* Clinica Dental
* Solicitado por: {nombre_solicitante}
* Email: {perfil.email}
* Telefono: {perfil.telefono}

Agradecemos confirmar la recepcion de este pedido y la disponibilidad de los 
insumos requeridos a la brevedad posible.

En caso de requerir informacion adicional, favor contactarnos a traves de los 
medios indicados.

Quedamos atentos a su respuesta.

Saludos cordiales,
{nombre_solicitante}
Clinica Dental
"""
            
            # Obtener información de la clínica
            try:
                from configuracion.models import InformacionClinica
                info_clinica = InformacionClinica.obtener()
                nombre_clinica = info_clinica.nombre_clinica
                email_clinica = info_clinica.email or settings.DEFAULT_FROM_EMAIL
                direccion_clinica = info_clinica.direccion or ''
                telefono_clinica = info_clinica.telefono or ''
            except:
                nombre_clinica = "Clínica Dental"
                email_clinica = settings.DEFAULT_FROM_EMAIL
                direccion_clinica = ''
                telefono_clinica = ''
            
            # Preparar lista de insumos para el template
            insumos_list = []
            for solicitud in pedido.solicitudes.all():
                nombre_insumo = normalizar_texto(solicitud.insumo.nombre)
                unidad_medida = normalizar_texto(solicitud.insumo.unidad_medida)
                precio_str = f"${solicitud.precio_unitario:,.0f}" if solicitud.precio_unitario else "Precio a confirmar"
                monto_str = f"${solicitud.monto_egreso:,.0f}" if solicitud.monto_egreso else "Precio a confirmar"
                
                insumos_list.append({
                    'nombre': nombre_insumo,
                    'cantidad': solicitud.cantidad_solicitada,
                    'unidad': unidad_medida,
                    'precio_unitario': precio_str,
                    'monto_total': monto_str,
                    'observaciones': normalizar_texto(solicitud.observaciones) if solicitud.observaciones else None,
                })
            
            # Renderizar template HTML
            from django.template.loader import render_to_string
            mensaje_html = render_to_string('citas/emails/pedido_proveedor.html', {
                'nombre_proveedor': nombre_proveedor,
                'numero_pedido': pedido.numero_pedido,
                'fecha_pedido': pedido.fecha_pedido,
                'fecha_entrega_esperada': pedido.fecha_entrega_esperada,
                'insumos': insumos_list,
                'monto_total': f"${pedido.monto_total:,.0f}" if pedido.monto_total else None,
                'observaciones_generales': normalizar_texto(pedido.observaciones) if pedido.observaciones else None,
                'nombre_solicitante': nombre_solicitante,
                'email_solicitante': perfil.email,
                'telefono_solicitante': perfil.telefono or 'No especificado',
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': direccion_clinica,
                'telefono_clinica': telefono_clinica,
                'email_clinica': email_clinica,
            })
            
            # Enviar correo
            email = EmailMessage(
                subject=asunto,
                body=mensaje_html,
                from_email=email_clinica,
                to=[pedido.proveedor.email],
            )
            email.content_subtype = "html"  # Indicar que es HTML
            
            email.send(fail_silently=False)
            
            # Actualizar pedido
            pedido.correo_enviado = True
            pedido.fecha_envio_correo = timezone.now()
            pedido.estado = 'enviado'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido {pedido.numero_pedido} enviado correctamente a {pedido.proveedor.email}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al enviar el correo: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


@login_required
def marcar_solicitud_recibida(request, solicitud_id):
    """Vista AJAX para marcar una solicitud como recibida y registrar el stock y egreso"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            return JsonResponse({'success': False, 'message': 'No tienes permisos para realizar esta acción.'}, status=403)
    except Perfil.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Perfil no encontrado.'}, status=404)
    
    try:
        solicitud = get_object_or_404(SolicitudInsumo, id=solicitud_id)
        
        # Verificar que la solicitud no esté ya recibida o cancelada
        if solicitud.estado == 'recibida':
            return JsonResponse({'success': False, 'message': 'Esta solicitud ya fue marcada como recibida.'}, status=400)
        
        if solicitud.estado == 'cancelada':
            return JsonResponse({'success': False, 'message': 'No se puede marcar como recibida una solicitud cancelada.'}, status=400)
        
        # Cambiar estado a recibida
        solicitud.estado = 'recibida'
        solicitud.save()
        
        # Registrar movimiento de entrada de stock
        insumo = solicitud.insumo
        cantidad_anterior = insumo.cantidad_actual
        insumo.cantidad_actual += solicitud.cantidad_solicitada
        
        # Actualizar estado del insumo si estaba agotado
        if insumo.estado == 'agotado' and insumo.cantidad_actual > 0:
            insumo.estado = 'disponible'
        
        insumo.save()
        
        # Crear movimiento de stock
        MovimientoInsumo.objects.create(
            insumo=insumo,
            tipo='entrada',
            cantidad=solicitud.cantidad_solicitada,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=insumo.cantidad_actual,
            motivo=f'Recepción de solicitud #{solicitud.id}',
            observaciones=f'Solicitud recibida de {solicitud.proveedor.nombre}. Cantidad solicitada: {solicitud.cantidad_solicitada} {insumo.unidad_medida}',
            realizado_por=perfil
        )
        
        # Calcular monto si no está establecido (usar precio unitario de la solicitud o del insumo)
        monto_egreso = None
        if solicitud.monto_egreso:
            monto_egreso = float(solicitud.monto_egreso)
        else:
            # Calcular monto basado en precio unitario
            precio_unit = solicitud.precio_unitario or (insumo.precio_unitario if insumo.precio_unitario else None)
            if precio_unit:
                monto_egreso = float(precio_unit) * solicitud.cantidad_solicitada
        
        # Registrar egreso en finanzas si tiene monto
        mensaje_egreso = ''
        if monto_egreso:
            try:
                monto_egreso_redondeado = round(float(monto_egreso))
                EgresoManual.objects.create(
                    monto=monto_egreso_redondeado,
                    descripcion=f'Compra de insumos - Solicitud #{solicitud.id} - {insumo.nombre}',
                    fecha=timezone.now().date(),
                    notas=f'Proveedor: {solicitud.proveedor.nombre}. Cantidad: {solicitud.cantidad_solicitada} {insumo.unidad_medida}. Precio unitario: ${solicitud.precio_unitario or insumo.precio_unitario or "N/A"}',
                    creado_por=perfil
                )
                mensaje_egreso = f' Egreso registrado: ${monto_egreso_redondeado:,.0f}.'
            except (ValueError, TypeError) as e:
                # Si hay error al crear el egreso, continuar pero loguear
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Error al registrar egreso para solicitud {solicitud.id}: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'✅ Solicitud marcada como recibida. Stock de {insumo.nombre} actualizado: {cantidad_anterior} → {insumo.cantidad_actual} {insumo.unidad_medida}.{mensaje_egreso}'
        })
        
    except SolicitudInsumo.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Solicitud no encontrada.'}, status=404)
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error al marcar solicitud como recibida: {str(e)}\n{traceback.format_exc()}')
        return JsonResponse({'success': False, 'message': f'Error al procesar la solicitud: {str(e)}'}, status=500)
