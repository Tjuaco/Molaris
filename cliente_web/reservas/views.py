# reservas/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Cita
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
import requests
from urllib.parse import urljoin

from .sms_service import enviar_sms_confirmacion, enviar_sms_cancelacion, consultar_estado_mensaje
import logging

logger = logging.getLogger(__name__)
from cuentas.models import PerfilCliente
from .dentist_service import obtener_info_dentista, obtener_estadisticas_dentista, obtener_dentista_de_cita, obtener_todos_dentistas_activos
from .servicio_service import obtener_tipo_servicio_de_cita
from .documentos_models import Odontograma, Radiografia, ClienteDocumento
from .servicios_models import TipoServicio

@login_required
def reservar_cita(request, cita_id):
    if request.method == 'POST':
        # Verificar que el usuario no tenga ya una cita reservada
        citas_existentes = Cita.objects.filter(
            paciente_nombre=request.user.username,
            estado__in=['reservada', 'confirmada']
        ).count()
        
        if citas_existentes > 0:
            messages.error(request, '❌ Ya tienes una cita activa. Solo puedes reservar una cita a la vez.')
            return redirect('panel_cliente')
        
        cita = get_object_or_404(Cita, id=cita_id)
        if cita.estado == 'disponible':
            # Obtener datos de perfil del usuario para usar nombre completo
            try:
                perfil = PerfilCliente.objects.get(user=request.user)
                nombre_completo = perfil.nombre_completo
                email = perfil.email or request.user.email
                telefono = perfil.telefono
            except PerfilCliente.DoesNotExist:
                # Si no hay perfil, usar datos del User
                nombre_completo = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
                email = request.user.email or ''
                telefono = ''
            
            # Buscar o crear el Cliente en el sistema de gestión
            from pacientes.models import Cliente
            cliente, created = Cliente.objects.get_or_create(
                email=email,
                defaults={
                    'nombre_completo': nombre_completo,
                    'telefono': telefono if telefono else '+56900000000'  # Placeholder si no hay teléfono
                }
            )
            
            # Si el cliente ya existe, actualizar su información si es necesario
            if not created:
                if nombre_completo and nombre_completo != cliente.nombre_completo:
                    cliente.nombre_completo = nombre_completo
                if telefono and telefono != cliente.telefono and telefono:
                    cliente.telefono = telefono
                cliente.save()
            
            # Reservar la cita usando el Cliente (esto establecerá el nombre completo correctamente)
            cita.reservar(
                cliente=cliente,
                paciente_nombre=nombre_completo,
                paciente_email=email,
                paciente_telefono=telefono if telefono else None
            )

            # Enviar SMS de confirmación
            try:
                # Verificar que haya teléfono antes de enviar SMS
                if not cita.paciente_telefono:
                    logger.warning(f"No hay teléfono para la cita {cita.id}, no se enviará SMS")
                    messages.success(request, f"Cita reservada exitosamente para {cita.fecha_hora}. No se pudo enviar SMS (falta número de teléfono).")
                else:
                    enviar_sms_confirmacion(cita)
                    messages.success(request, f"Cita reservada exitosamente para {cita.fecha_hora}. Se envió confirmación por SMS.")
            except Exception as e:
                logger.error(f"Error al enviar SMS para cita {cita.id}: {e}")
                print(f"Error al enviar SMS: {e}")
                messages.success(request, f"Cita reservada exitosamente para {cita.fecha_hora}. No se pudo enviar el SMS de confirmación.")
        else:
            messages.error(request, "Esta cita ya no está disponible")
        return redirect('panel_cliente')
    return redirect('panel_cliente')


@login_required
def panel_cliente(request):
    # Obtener parámetros de filtro
    tipo_consulta = request.GET.get('tipo_consulta', '')
    fecha_filtro = request.GET.get('fecha', '')
    dentista_id = request.GET.get('dentista_id', '')
    
    # Obtener citas disponibles con filtros
    citas_disponibles = Cita.objects.filter(estado='disponible')
    
    # Aplicar filtros si existen
    if tipo_consulta:
        citas_disponibles = citas_disponibles.filter(tipo_consulta=tipo_consulta)
    
    if fecha_filtro:
        from datetime import datetime
        try:
            fecha_obj = datetime.strptime(fecha_filtro, '%Y-%m-%d').date()
            citas_disponibles = citas_disponibles.filter(fecha_hora__date=fecha_obj)
        except ValueError:
            pass  # Si la fecha es inválida, ignorar el filtro
    
    citas_disponibles = citas_disponibles.order_by('fecha_hora')
    
    # Aplicar filtro de dentista si existe
    if dentista_id:
        try:
            dentista_id_int = int(dentista_id)
            # Filtrar citas que tienen este dentista asignado
            citas_disponibles = citas_disponibles.filter(dentista_id=dentista_id_int)
        except ValueError:
            pass  # Si el ID es inválido, ignorar el filtro
    
    # Agregar información del dentista y tipo de servicio a cada cita disponible
    citas_con_dentista = []
    for cita in citas_disponibles:
        dentista_info = obtener_dentista_de_cita(cita.id)
        servicio_info = obtener_tipo_servicio_de_cita(cita.id, tipo_consulta=cita.tipo_consulta)
        # Agregar el dentista y servicio como atributo de la cita
        cita.dentista_info = dentista_info
        cita.servicio_info = servicio_info
        citas_con_dentista.append(cita)
    
    # Obtener citas reservadas por el usuario actual
    citas_reservadas = Cita.objects.filter(
        estado='reservada',
        paciente_nombre=request.user.username
    ).order_by('fecha_hora')
    
    # Agregar información del dentista y tipo de servicio a cada cita reservada
    for cita in citas_reservadas:
        dentista_info = obtener_dentista_de_cita(cita.id)
        servicio_info = obtener_tipo_servicio_de_cita(cita.id, tipo_consulta=cita.tipo_consulta)
        cita.dentista_info = dentista_info
        cita.servicio_info = servicio_info
    
    # Obtener perfil del usuario
    try:
        perfil_usuario = PerfilCliente.objects.get(user=request.user)
    except PerfilCliente.DoesNotExist:
        perfil_usuario = None
    
    # Debug prints (se pueden quitar en producción)
    print(f"\n{'='*60}")
    print(f"=== DEBUG PANEL CLIENTE ===")
    print(f"{'='*60}")
    print(f"Usuario actual: {request.user.username}")
    print(f"Filtros aplicados: tipo_consulta={tipo_consulta}, fecha={fecha_filtro}")
    print(f"Citas disponibles encontradas: {len(citas_con_dentista)}")
    print(f"Citas reservadas por {request.user.username}: {citas_reservadas.count()}")
    print(f"\n--- CITAS DISPONIBLES ---")
    
    # Debug: Mostrar información de cada cita con su dentista
    for cita in citas_con_dentista:
        print(f"\nCita ID: {cita.id}")
        print(f"  Fecha/Hora: {cita.fecha_hora}")
        print(f"  Tipo: {cita.tipo_consulta or 'No especificado'}")
        print(f"  Estado: {cita.estado}")
        if cita.dentista_info:
            print(f"  ✅ Dentista: {cita.dentista_info.get('nombre')} ({cita.dentista_info.get('especialidad')})")
        else:
            print(f"  ⚠️ Dentista: Sin asignar")
    
    print(f"\n--- CITAS RESERVADAS ---")
    for cita in citas_reservadas:
        print(f"\nCita ID: {cita.id}")
        print(f"  Fecha/Hora: {cita.fecha_hora}")
        print(f"  Tipo: {cita.tipo_consulta or 'No especificado'}")
        print(f"  Paciente: {cita.paciente_nombre}")
        if hasattr(cita, 'dentista_info') and cita.dentista_info:
            print(f"  ✅ Dentista: {cita.dentista_info.get('nombre')}")
        else:
            print(f"  ⚠️ Dentista: Sin asignar")
    print(f"{'='*60}\n")

    # Obtener lista de dentistas disponibles para el filtro
    dentistas_disponibles = obtener_todos_dentistas_activos()
    
    return render(request, "reservas/panel.html", {
        "citas": citas_con_dentista,
        "citas_reservadas": citas_reservadas,
        "perfil_usuario": perfil_usuario,
        "dentistas_disponibles": dentistas_disponibles,
    })


def _cambiar_estado_cita(cita: Cita, nuevo_estado: str):
    cita.estado = nuevo_estado
    cita.save(update_fields=["estado"])


@csrf_exempt
def confirmar_cita(request, cita_id):
    """Endpoint público para confirmar sin login (desde enlace)."""
    cita = get_object_or_404(Cita, id=cita_id)
    if cita.estado in ("reservada", "confirmada"):
        _cambiar_estado_cita(cita, "confirmada")
        messages.success(request, f"Cita confirmada para {cita.fecha_hora}")
        return redirect('panel_cliente') if request.user.is_authenticated else JsonResponse({
            'ok': True,
            'cita_id': cita.id,
            'estado': cita.estado,
        })
    return JsonResponse({'ok': False, 'error': 'Cita no reservada'}, status=400)



@login_required
def obtener_citas_fecha(request):
    """Vista AJAX para obtener citas de una fecha específica"""
    if request.method == 'GET':
        fecha = request.GET.get('fecha')
        if fecha:
            try:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                citas = Cita.objects.filter(
                    fecha_hora__date=fecha_obj,
                    estado='disponible'
                ).order_by('fecha_hora')
                
                citas_data = []
                for cita in citas:
                    citas_data.append({
                        'id': cita.id,
                        'fecha_hora': cita.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                        'hora': cita.fecha_hora.strftime('%H:%M')
                    })
                
                return JsonResponse({'citas': citas_data})
            except ValueError:
                return JsonResponse({'error': 'Formato de fecha inválido'})
    
    return JsonResponse({'error': 'Método no permitido'})

# Vista temporal para debugging - eliminar en producción
def debug_citas(request):
    """Vista temporal para debug - mostrar todas las citas en la BD"""
    citas = Cita.objects.all().order_by('fecha_hora')
    debug_info = []
    
    for cita in citas:
        debug_info.append({
            'id': cita.id,
            'fecha_hora': cita.fecha_hora,
            'estado': cita.estado,
            'paciente_nombre': cita.paciente_nombre,
            'paciente_email': cita.paciente_email,
            'paciente_telefono': cita.paciente_telefono,
        })
    
    return JsonResponse({'citas': debug_info})


@login_required
def debug_estado_whatsapp(request, cita_id):
    """Consulta el estado del SMS asociado a una cita (si tiene SID)."""
    cita = get_object_or_404(Cita, id=cita_id)
    if not cita.whatsapp_message_sid:
        return JsonResponse({
            'error': 'La cita no tiene SID de mensaje guardado',
            'cita_id': cita_id,
        }, status=404)
    try:
        info = consultar_estado_mensaje(cita.whatsapp_message_sid)
        return JsonResponse({'cita_id': cita_id, 'message': info})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# VISTAS DEL MENÚ LATERAL
# ============================================

@login_required
def mi_perfil(request):
    """Vista para ver y editar el perfil del usuario"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
    except PerfilCliente.DoesNotExist:
        # Si no existe perfil, crear uno automáticamente con los datos del usuario
        print(f"DEBUG - No se encontró perfil para {request.user.username}, creando uno automáticamente...")
        
        # Intentar obtener teléfono de alguna cita existente
        telefono_desde_cita = None
        try:
            cita_existente = Cita.objects.filter(paciente_nombre=request.user.username).first()
            if cita_existente and cita_existente.paciente_telefono:
                telefono_desde_cita = cita_existente.paciente_telefono
        except Exception:
            pass
        
        # Crear perfil con datos disponibles
        nombre_completo = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        email = request.user.email or ''
        
        perfil = PerfilCliente.objects.create(
            user=request.user,
            nombre_completo=nombre_completo,
            telefono=telefono_desde_cita or '',
            email=email,
            telefono_verificado=False
        )
        print(f"DEBUG - Perfil creado automáticamente para {request.user.username}")
    
    # Sincronizar información del perfil desde citas_cliente del sistema de gestión
    # Esto asegura que el email, teléfono y nombre estén actualizados
    cliente_doc = None
    
    # 1. Intentar buscar el cliente en citas_cliente por múltiples métodos
    try:
        # Primero intentar por nombre completo (más estable que el email)
        if perfil.nombre_completo:
            cliente_doc = ClienteDocumento.objects.filter(nombre_completo=perfil.nombre_completo).first()
            if cliente_doc:
                print(f"DEBUG - Cliente encontrado en citas_cliente por nombre completo: {perfil.nombre_completo}")
        
        # Si no se encontró, intentar por el email del User de Django (puede estar más actualizado)
        if not cliente_doc and request.user.email:
            cliente_doc = ClienteDocumento.objects.filter(email=request.user.email).first()
            if cliente_doc:
                print(f"DEBUG - Cliente encontrado en citas_cliente por email de User: {request.user.email}")
        
        # Si no se encontró, intentar por el email del perfil actual
        if not cliente_doc and perfil.email:
            cliente_doc = ClienteDocumento.objects.filter(email=perfil.email).first()
            if cliente_doc:
                print(f"DEBUG - Cliente encontrado en citas_cliente por email del perfil: {perfil.email}")
        
        # Si aún no se encontró, intentar buscar desde las citas del usuario
        # Las citas pueden tener el email actualizado
        if not cliente_doc:
            try:
                citas_usuario = Cita.objects.filter(paciente_nombre=request.user.username)
                cita_con_email = citas_usuario.filter(
                    paciente_email__isnull=False
                ).exclude(paciente_email='').first()
                
                if cita_con_email and cita_con_email.paciente_email:
                    cliente_doc = ClienteDocumento.objects.filter(email=cita_con_email.paciente_email).first()
                    if cliente_doc:
                        print(f"DEBUG - Cliente encontrado en citas_cliente por email de cita: {cita_con_email.paciente_email}")
            except Exception as e:
                print(f"DEBUG - Error al buscar cliente desde citas: {e}")
        
        # Si encontramos el cliente en citas_cliente, sincronizar todos los datos
        if cliente_doc:
            actualizado = False
            
            # Actualizar email si es diferente
            if cliente_doc.email and cliente_doc.email != perfil.email:
                perfil.email = cliente_doc.email
                actualizado = True
                print(f"DEBUG - Email actualizado desde citas_cliente: {cliente_doc.email}")
            
            # Actualizar teléfono si está vacío o es diferente
            if cliente_doc.telefono:
                if not perfil.telefono or perfil.telefono.strip() == '':
                    perfil.telefono = cliente_doc.telefono
                    actualizado = True
                    print(f"DEBUG - Teléfono actualizado desde citas_cliente: {cliente_doc.telefono}")
            
            # Actualizar nombre completo si está disponible y es diferente
            if cliente_doc.nombre_completo and cliente_doc.nombre_completo != perfil.nombre_completo:
                perfil.nombre_completo = cliente_doc.nombre_completo
                actualizado = True
                print(f"DEBUG - Nombre completo actualizado desde citas_cliente: {cliente_doc.nombre_completo}")
            
            # Actualizar RUT si está disponible y es diferente
            if cliente_doc.rut and cliente_doc.rut != perfil.rut:
                perfil.rut = cliente_doc.rut
                actualizado = True
                print(f"DEBUG - RUT actualizado desde citas_cliente: {cliente_doc.rut}")
            
            # Actualizar fecha de nacimiento si está disponible y es diferente
            if cliente_doc.fecha_nacimiento and cliente_doc.fecha_nacimiento != perfil.fecha_nacimiento:
                perfil.fecha_nacimiento = cliente_doc.fecha_nacimiento
                actualizado = True
                print(f"DEBUG - Fecha de nacimiento actualizada desde citas_cliente: {cliente_doc.fecha_nacimiento}")
            
            # Actualizar alergias si está disponible y es diferente (MUY IMPORTANTE)
            if cliente_doc.alergias is not None:
                # Actualizar si el perfil no tiene alergias o si son diferentes
                if not perfil.alergias or perfil.alergias.strip() == '' or cliente_doc.alergias.strip() != perfil.alergias.strip():
                    perfil.alergias = cliente_doc.alergias
                    actualizado = True
                    print(f"DEBUG - Alergias actualizadas desde citas_cliente: {cliente_doc.alergias[:50] if cliente_doc.alergias else 'Sin alergias'}...")
            
            # Guardar los cambios si hubo actualizaciones
            if actualizado:
                perfil.save()
                print(f"DEBUG - Perfil sincronizado con citas_cliente")
    except Exception as e:
        print(f"DEBUG - Error al buscar o sincronizar con citas_cliente: {e}")
    
    # Si no se encontró en citas_cliente y el teléfono está vacío, intentar desde las citas del usuario
    if perfil and (not perfil.telefono or perfil.telefono.strip() == ''):
        telefono_encontrado = None
        try:
            citas_usuario = Cita.objects.filter(paciente_nombre=request.user.username)
            cita_con_telefono = citas_usuario.filter(
                paciente_telefono__isnull=False
            ).exclude(paciente_telefono='').first()
            
            if cita_con_telefono and cita_con_telefono.paciente_telefono:
                telefono_encontrado = cita_con_telefono.paciente_telefono
                print(f"DEBUG - Teléfono encontrado en cita: {telefono_encontrado}")
                
                # Actualizar el perfil si se encontró teléfono
                if telefono_encontrado:
                    perfil.telefono = telefono_encontrado
                    perfil.save(update_fields=['telefono'])
                    print(f"DEBUG - Teléfono actualizado en perfil: {perfil.telefono}")
        except Exception as e:
            print(f"DEBUG - Error al buscar en citas: {e}")
    
    # Debug: Verificar datos del perfil
    if perfil:
        print(f"DEBUG - Perfil encontrado para {request.user.username}:")
        print(f"  - Nombre completo: {perfil.nombre_completo}")
        print(f"  - Email: {perfil.email}")
        print(f"  - Teléfono: '{perfil.telefono}' (tipo: {type(perfil.telefono)}, longitud: {len(perfil.telefono) if perfil.telefono else 0})")
        print(f"  - Teléfono verificado: {perfil.telefono_verificado}")
    
    # Obtener estadísticas del usuario
    citas_totales = Cita.objects.filter(paciente_nombre=request.user.username).count()
    citas_reservadas = Cita.objects.filter(
        paciente_nombre=request.user.username,
        estado__in=['reservada', 'confirmada']
    ).count()
    citas_completadas = Cita.objects.filter(
        paciente_nombre=request.user.username,
        estado='completada'
    ).count()
    
    context = {
        'perfil': perfil,
        'user': request.user,
        'citas_totales': citas_totales,
        'citas_reservadas': citas_reservadas,
        'citas_completadas': citas_completadas,
    }
    
    return render(request, 'reservas/mi_perfil.html', context)


@login_required
def historial_citas(request):
    """Vista para ver el historial de citas del usuario"""
    # Obtener todas las citas del usuario (reservadas y pasadas)
    citas_historial = Cita.objects.filter(
        paciente_nombre=request.user.username
    ).order_by('-fecha_hora')
    
    # Agregar información del dentista y tipo de servicio a cada cita
    for cita in citas_historial:
        dentista_info = obtener_dentista_de_cita(cita.id)
        servicio_info = obtener_tipo_servicio_de_cita(cita.id, tipo_consulta=cita.tipo_consulta)
        cita.dentista_info = dentista_info
        cita.servicio_info = servicio_info
    
    context = {
        'citas_historial': citas_historial,
    }
    
    return render(request, 'reservas/historial_citas.html', context)


@login_required
def ayuda(request):
    """Vista para el centro de ayuda"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
    except PerfilCliente.DoesNotExist:
        perfil = None
    
    context = {
        'perfil': perfil,
    }
    
    return render(request, 'reservas/ayuda.html', context)


# ============================================
# VISTAS DE DOCUMENTOS (FICHAS Y RADIOGRAFÍAS)
# ============================================

@login_required
def ver_odontogramas(request):
    """Vista para ver todas las fichas odontológicas del usuario"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
        email_usuario = perfil.email
    except PerfilCliente.DoesNotExist:
        email_usuario = request.user.email
    
    # Obtener cliente desde la tabla citas_cliente si existe
    cliente_doc = None
    try:
        cliente_doc = ClienteDocumento.objects.filter(email=email_usuario).first()
    except Exception:
        pass
    
    # Obtener odontogramas por email del paciente
    odontogramas = Odontograma.objects.filter(paciente_email=email_usuario)
    
    # Si tenemos cliente_id, también buscar por ese ID
    if cliente_doc:
        odontogramas = odontogramas | Odontograma.objects.filter(cliente_id=cliente_doc.id)
    
    # Eliminar duplicados y ordenar
    odontogramas = odontogramas.distinct().order_by('-fecha_creacion')
    
    context = {
        'odontogramas': odontogramas,
        'total': odontogramas.count(),
        'perfil': perfil if 'perfil' in locals() else None,
    }
    
    return render(request, 'reservas/ver_odontogramas.html', context)


@login_required
def ver_odontograma(request, odontograma_id):
    """Vista para ver un odontograma específico"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
        email_usuario = perfil.email
    except PerfilCliente.DoesNotExist:
        email_usuario = request.user.email
    
    # Obtener el odontograma solo si pertenece al usuario
    try:
        odontograma = Odontograma.objects.get(
            id=odontograma_id,
            paciente_email=email_usuario
        )
    except Odontograma.DoesNotExist:
        # Intentar buscar por cliente_id también
        try:
            cliente_doc = ClienteDocumento.objects.get(email=email_usuario)
            odontograma = Odontograma.objects.get(
                id=odontograma_id,
                cliente_id=cliente_doc.id
            )
        except (Odontograma.DoesNotExist, ClienteDocumento.DoesNotExist):
            messages.error(request, 'No tienes acceso a este documento.')
            return redirect('ver_odontogramas')
    
    context = {
        'odontograma': odontograma,
    }
    
    return render(request, 'reservas/ver_odontograma.html', context)


@login_required
def descargar_odontograma(request, odontograma_id):
    """Vista para descargar PDF de odontograma"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
        email_usuario = perfil.email
    except PerfilCliente.DoesNotExist:
        email_usuario = request.user.email
    
    # Obtener el odontograma solo si pertenece al usuario
    try:
        odontograma = Odontograma.objects.get(
            id=odontograma_id,
            paciente_email=email_usuario
        )
    except Odontograma.DoesNotExist:
        try:
            cliente_doc = ClienteDocumento.objects.get(email=email_usuario)
            odontograma = Odontograma.objects.get(
                id=odontograma_id,
                cliente_id=cliente_doc.id
            )
        except (Odontograma.DoesNotExist, ClienteDocumento.DoesNotExist):
            messages.error(request, 'No tienes acceso a este documento.')
            return redirect('ver_odontogramas')
    
    # Intentar obtener el PDF desde el sistema de gestión
    gestion_url = getattr(settings, 'GESTION_API_URL', 'http://localhost:8001')
    base_url = gestion_url.replace('/api', '').rstrip('/')
    
    # Intentar primero desde API endpoints (si existen)
    api_endpoints = [
        f"{gestion_url}/odontogramas/{odontograma_id}/pdf/",
        f"{gestion_url}/fichas/{odontograma_id}/pdf/",
        f"{base_url}/api/odontogramas/{odontograma_id}/pdf/",
        f"{base_url}/api/fichas/{odontograma_id}/pdf/",
        f"{base_url}/odontogramas/{odontograma_id}/pdf/",
        f"{base_url}/fichas/{odontograma_id}/pdf/",
    ]
    
    for api_url in api_endpoints:
        try:
            response = requests.get(api_url, timeout=10, stream=True, allow_redirects=True)
            if response.status_code == 200:
                content = response.content
                # Verificar que sea PDF válido
                if content and (content[:4] == b'%PDF' or 'pdf' in response.headers.get('Content-Type', '').lower()):
                    paciente_name = (odontograma.paciente_nombre or 'paciente').replace(' ', '_')
                    paciente_name = ''.join(c for c in paciente_name if c.isalnum() or c in ('_', '-'))
                    filename = f"ficha_odontologica_{odontograma_id}_{paciente_name}.pdf"
                    
                    http_response = HttpResponse(content, content_type='application/pdf')
                    http_response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    http_response['Content-Length'] = len(content)
                    return http_response
        except Exception as e:
            continue
    
    # Si no funciona API, probar rutas de archivos estáticos/media
    # Basado en el patrón de radiografías (radiografias/YYYY/MM/DD/archivo),
    # los PDFs podrían estar en odontogramas/YYYY/MM/DD/archivo.pdf
    from datetime import datetime
    fecha_creacion = odontograma.fecha_creacion
    if fecha_creacion:
        year = fecha_creacion.year
        month = fecha_creacion.month
        day = fecha_creacion.day
    else:
        fecha_actual = datetime.now()
        year = fecha_actual.year
        month = fecha_actual.month
        day = fecha_actual.day
    
    possible_paths = [
        # Rutas con fecha (similar a radiografías): odontogramas/YYYY/MM/DD/odontograma_ID.pdf
        f"media/odontogramas/{year}/{month:02d}/{day:02d}/odontograma_{odontograma_id}.pdf",
        f"media/odontogramas/{year}/{month:02d}/{day:02d}/ficha_{odontograma_id}.pdf",
        f"media/fichas/{year}/{month:02d}/{day:02d}/odontograma_{odontograma_id}.pdf",
        f"media/fichas/{year}/{month:02d}/{day:02d}/ficha_{odontograma_id}.pdf",
        # Rutas directas (sin fecha)
        f"media/odontogramas/{odontograma_id}.pdf",
        f"media/odontogramas/odontograma_{odontograma_id}.pdf",
        f"media/fichas/{odontograma_id}.pdf",
        f"media/fichas/ficha_{odontograma_id}.pdf",
        f"media/pdf/odontograma_{odontograma_id}.pdf",
        f"media/pdf/ficha_{odontograma_id}.pdf",
        # Sin media/ al inicio
        f"odontogramas/{year}/{month:02d}/{day:02d}/odontograma_{odontograma_id}.pdf",
        f"odontogramas/{odontograma_id}.pdf",
        f"fichas/{odontograma_id}.pdf",
    ]
    
    # Intentar cada ruta posible
    for pdf_path in possible_paths:
        pdf_url = urljoin(base_url + '/', pdf_path)
        try:
            response = requests.get(pdf_url, timeout=10, stream=True, allow_redirects=True)
            if response.status_code == 200:
                content = response.content
                # Verificar que sea PDF válido (magic bytes %PDF o tamaño razonable)
                if content and (content[:4] == b'%PDF' or len(content) > 1000):
                    paciente_name = (odontograma.paciente_nombre or 'paciente').replace(' ', '_')
                    paciente_name = ''.join(c for c in paciente_name if c.isalnum() or c in ('_', '-'))
                    filename = f"ficha_odontologica_{odontograma_id}_{paciente_name}.pdf"
                    
                    http_response = HttpResponse(content, content_type='application/pdf')
                    http_response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    http_response['Content-Length'] = len(content)
                    return http_response
        except Exception as e:
            continue
    
    # Si no se encuentra el PDF, informar al usuario con más detalles
    messages.error(
        request, 
        f'No se pudo encontrar el PDF de la ficha odontológica (ID: {odontograma_id}). '
        f'Por favor, contacta con la clínica para obtener tu documento. '
        f'Puedes ver toda la información disponible en la página de detalle.'
    )
    return redirect('ver_odontograma', odontograma_id=odontograma_id)


@login_required
def ver_pdf_odontograma(request, odontograma_id):
    """Vista proxy para servir PDF de odontograma (evita problemas de CORS)"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
        email_usuario = perfil.email
    except PerfilCliente.DoesNotExist:
        email_usuario = request.user.email
    
    # Obtener el odontograma solo si pertenece al usuario
    try:
        odontograma = Odontograma.objects.get(
            id=odontograma_id,
            paciente_email=email_usuario
        )
    except Odontograma.DoesNotExist:
        try:
            cliente_doc = ClienteDocumento.objects.get(email=email_usuario)
            odontograma = Odontograma.objects.get(
                id=odontograma_id,
                cliente_id=cliente_doc.id
            )
        except (Odontograma.DoesNotExist, ClienteDocumento.DoesNotExist):
            return HttpResponse('Acceso denegado', status=403)
    
    # Intentar obtener el PDF desde el sistema de gestión
    gestion_url = getattr(settings, 'GESTION_API_URL', 'http://localhost:8001')
    base_url = gestion_url.replace('/api', '').rstrip('/')
    
    # Intentar primero desde API endpoints (si existen)
    api_endpoints = [
        f"{gestion_url}/odontogramas/{odontograma_id}/pdf/",
        f"{gestion_url}/fichas/{odontograma_id}/pdf/",
        f"{base_url}/api/odontogramas/{odontograma_id}/pdf/",
        f"{base_url}/api/fichas/{odontograma_id}/pdf/",
        f"{base_url}/odontogramas/{odontograma_id}/pdf/",
        f"{base_url}/fichas/{odontograma_id}/pdf/",
    ]
    
    for api_url in api_endpoints:
        try:
            response = requests.get(api_url, timeout=10, stream=True, allow_redirects=True)
            if response.status_code == 200:
                content = response.content
                # Verificar que sea PDF válido
                if content and (content[:4] == b'%PDF' or 'pdf' in response.headers.get('Content-Type', '').lower()):
                    http_response = HttpResponse(content, content_type='application/pdf')
                    http_response['Content-Disposition'] = 'inline; filename="odontograma.pdf"'
                    http_response['Cache-Control'] = 'public, max-age=3600'
                    return http_response
        except Exception as e:
            continue
    
    # Si no funciona API, probar rutas de archivos estáticos/media
    from datetime import datetime
    fecha_creacion = odontograma.fecha_creacion
    if fecha_creacion:
        year = fecha_creacion.year
        month = fecha_creacion.month
        day = fecha_creacion.day
    else:
        fecha_actual = datetime.now()
        year = fecha_actual.year
        month = fecha_actual.month
        day = fecha_actual.day
    
    possible_paths = [
        f"media/odontogramas/{year}/{month:02d}/{day:02d}/odontograma_{odontograma_id}.pdf",
        f"media/odontogramas/{year}/{month:02d}/{day:02d}/ficha_{odontograma_id}.pdf",
        f"media/fichas/{year}/{month:02d}/{day:02d}/odontograma_{odontograma_id}.pdf",
        f"media/fichas/{year}/{month:02d}/{day:02d}/ficha_{odontograma_id}.pdf",
        f"media/odontogramas/{odontograma_id}.pdf",
        f"media/odontogramas/odontograma_{odontograma_id}.pdf",
        f"media/fichas/{odontograma_id}.pdf",
        f"media/fichas/ficha_{odontograma_id}.pdf",
        f"media/pdf/odontograma_{odontograma_id}.pdf",
        f"media/pdf/ficha_{odontograma_id}.pdf",
        f"odontogramas/{year}/{month:02d}/{day:02d}/odontograma_{odontograma_id}.pdf",
        f"odontogramas/{odontograma_id}.pdf",
        f"fichas/{odontograma_id}.pdf",
        f"fichas/ficha_{odontograma_id}.pdf",
    ]
    
    # Intentar cada ruta posible
    for pdf_path in possible_paths:
        pdf_url = urljoin(base_url + '/', pdf_path)
        try:
            response = requests.get(pdf_url, timeout=10, stream=True, allow_redirects=True)
            if response.status_code == 200:
                content = response.content
                # Verificar que sea PDF válido (magic bytes %PDF o tamaño razonable)
                if content and (content[:4] == b'%PDF' or len(content) > 1000):
                    http_response = HttpResponse(content, content_type='application/pdf')
                    http_response['Content-Disposition'] = 'inline; filename="odontograma.pdf"'
                    http_response['Cache-Control'] = 'public, max-age=3600'
                    return http_response
        except Exception as e:
            continue
    
    # Si no se encuentra el PDF, retornar 404
    return HttpResponse('PDF no disponible', status=404)


@login_required
def ver_radiografias(request):
    """Vista para ver todas las radiografías del usuario"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
        email_usuario = perfil.email
    except PerfilCliente.DoesNotExist:
        email_usuario = request.user.email
    
    # Obtener cliente desde la tabla citas_cliente si existe
    cliente_doc = None
    try:
        cliente_doc = ClienteDocumento.objects.filter(email=email_usuario).first()
    except Exception:
        pass
    
    # Obtener radiografías por email del paciente
    radiografias = Radiografia.objects.filter(paciente_email=email_usuario)
    
    # Si tenemos cliente_id, también buscar por ese ID
    if cliente_doc:
        radiografias = radiografias | Radiografia.objects.filter(cliente_id=cliente_doc.id)
    
    # Eliminar duplicados y ordenar
    radiografias = radiografias.distinct().order_by('-fecha_carga')
    
    # Agrupar por tipo
    radiografias_por_tipo = {}
    for radio in radiografias:
        tipo = radio.get_tipo_display_value()
        if tipo not in radiografias_por_tipo:
            radiografias_por_tipo[tipo] = []
        radiografias_por_tipo[tipo].append(radio)
    
    context = {
        'radiografias': radiografias,
        'radiografias_por_tipo': radiografias_por_tipo,
        'total': radiografias.count(),
        'perfil': perfil if 'perfil' in locals() else None,
    }
    
    return render(request, 'reservas/ver_radiografias.html', context)


@login_required
def descargar_radiografia(request, radiografia_id):
    """Vista para descargar imagen de radiografía"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
        email_usuario = perfil.email
    except PerfilCliente.DoesNotExist:
        email_usuario = request.user.email
    
    # Obtener la radiografía solo si pertenece al usuario
    try:
        radiografia = Radiografia.objects.get(
            id=radiografia_id,
            paciente_email=email_usuario
        )
    except Radiografia.DoesNotExist:
        try:
            cliente_doc = ClienteDocumento.objects.get(email=email_usuario)
            radiografia = Radiografia.objects.get(
                id=radiografia_id,
                cliente_id=cliente_doc.id
            )
        except (Radiografia.DoesNotExist, ClienteDocumento.DoesNotExist):
            messages.error(request, 'No tienes acceso a esta radiografía.')
            return redirect('ver_radiografias')
    
    if not radiografia.imagen:
        messages.error(request, 'Esta radiografía no tiene imagen disponible.')
        return redirect('ver_radiografias')
    
    # Intentar descargar desde el sistema de gestión
    # Las imágenes están en formato: radiografias/2025/11/02/radiografia_1.png
    # Necesitamos agregar media/ al inicio
    gestion_url = getattr(settings, 'GESTION_API_URL', 'http://localhost:8001')
    base_url = gestion_url.replace('/api', '').rstrip('/')
    
    # Determinar la ruta correcta según el formato
    if radiografia.imagen.startswith('http://') or radiografia.imagen.startswith('https://'):
        # URL completa
        image_url = radiografia.imagen
    elif radiografia.imagen.startswith('media/'):
        # Ya incluye media/
        image_url = urljoin(base_url + '/', radiografia.imagen)
    else:
        # Formato esperado: radiografias/2025/11/02/radiografia_1.png
        # Agregar media/ al inicio
        image_url = urljoin(base_url + '/', f"media/{radiografia.imagen}")
    
    try:
        response = requests.get(image_url, timeout=10, stream=True)
        if response.status_code == 200:
            # Determinar tipo de contenido
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            extension = '.jpg'
            if 'png' in content_type.lower():
                extension = '.png'
            elif 'pdf' in content_type.lower():
                extension = '.pdf'
            
            filename = f"radiografia_{radiografia_id}_{radiografia.get_tipo_display_value().replace(' ', '_')}{extension}"
            response_http = HttpResponse(response.content, content_type=content_type)
            response_http['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response_http
    except Exception as e:
        pass
    
    # Si no se puede descargar, redirigir a ver la imagen
    messages.info(request, 'No se pudo descargar la imagen. Puedes verla en la galería.')
    return redirect('ver_radiografias')


@login_required
def ver_imagen_radiografia(request, radiografia_id):
    """Vista proxy para servir imágenes de radiografías (evita problemas de CORS)"""
    try:
        perfil = PerfilCliente.objects.get(user=request.user)
        email_usuario = perfil.email
    except PerfilCliente.DoesNotExist:
        email_usuario = request.user.email
    
    # Obtener la radiografía solo si pertenece al usuario
    try:
        radiografia = Radiografia.objects.get(
            id=radiografia_id,
            paciente_email=email_usuario
        )
    except Radiografia.DoesNotExist:
        try:
            cliente_doc = ClienteDocumento.objects.get(email=email_usuario)
            radiografia = Radiografia.objects.get(
                id=radiografia_id,
                cliente_id=cliente_doc.id
            )
        except (Radiografia.DoesNotExist, ClienteDocumento.DoesNotExist):
            return HttpResponse('Acceso denegado', status=403)
    
    if not radiografia.imagen:
        return HttpResponse('Imagen no disponible', status=404)
    
    # Obtener la imagen desde el sistema de gestión
    gestion_url = getattr(settings, 'GESTION_API_URL', 'http://localhost:8001')
    base_url = gestion_url.replace('/api', '').rstrip('/')
    
    # Construir URL de la imagen - probar múltiples formatos
    image_path = radiografia.imagen.strip()
    
    # Rutas posibles para probar
    possible_urls = []
    
    if image_path.startswith('http://') or image_path.startswith('https://'):
        possible_urls.append(image_path)
    elif image_path.startswith('media/'):
        possible_urls.append(urljoin(base_url + '/', image_path))
    else:
        # Formato esperado: radiografias/2025/11/02/radiografia_1.png
        # Agregar media/ al inicio
        possible_urls.append(urljoin(base_url + '/', f"media/{image_path}"))
        # También probar sin media/
        possible_urls.append(urljoin(base_url + '/', image_path))
    
    # Intentar cada URL posible
    last_error = None
    for image_url in possible_urls:
        try:
            response = requests.get(image_url, timeout=10, stream=True, allow_redirects=True)
            if response.status_code == 200:
                content = response.content
                # Verificar que tenga contenido válido
                if content and len(content) > 100:  # Mínimo 100 bytes para ser una imagen válida
                    # Determinar tipo de contenido
                    content_type = response.headers.get('Content-Type', '')
                    
                    # Si no tiene content-type, intentar detectarlo por extensión o magic bytes
                    if not content_type or 'text' in content_type.lower():
                        # Detectar por extensión
                        if image_path.lower().endswith('.png') or content[:8] == b'\x89PNG\r\n\x1a\n':
                            content_type = 'image/png'
                        elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg') or content[:2] == b'\xff\xd8':
                            content_type = 'image/jpeg'
                        elif image_path.lower().endswith('.gif') or content[:6] == b'GIF89a':
                            content_type = 'image/gif'
                        else:
                            content_type = 'image/jpeg'  # Default
                    
                    http_response = HttpResponse(content, content_type=content_type)
                    http_response['Cache-Control'] = 'public, max-age=3600'
                    return http_response
                else:
                    last_error = f"Contenido vacío o muy pequeño ({len(content) if content else 0} bytes)"
            else:
                last_error = f"Status code: {response.status_code}"
        except requests.exceptions.ConnectionError as e:
            last_error = f"No se pudo conectar: {str(e)}"
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout: {str(e)}"
        except Exception as e:
            last_error = f"Error: {str(e)}"
            continue
    
    # Si ninguna URL funciona, log el error y retornar 404 con mensaje descriptivo
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"No se pudo cargar imagen radiografia_id={radiografia_id}, imagen={image_path}, URLs probadas={possible_urls}, último error={last_error}")
    
    # Si el sistema de gestión no está corriendo, mostrar mensaje más claro
    if last_error and 'Connection' in last_error:
        error_msg = f'El sistema de gestión no está disponible en {base_url}. Por favor, inicia el sistema de gestión para poder ver las imágenes.'
    else:
        error_msg = f'No se pudo cargar la imagen. {last_error or "Error desconocido"}'
    
    return HttpResponse(error_msg, status=404)
