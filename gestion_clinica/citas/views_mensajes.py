from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from comunicacion.models import Mensaje
from personal.models import Perfil
from historial_clinico.models import Odontograma
from pacientes.models import Cliente

@login_required
def obtener_mensajes(request):
    """API para obtener los mensajes del usuario actual"""
    try:
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        return JsonResponse({'error': 'Perfil no encontrado'}, status=404)
    
    # Obtener mensajes recibidos
    mensajes_recibidos = Mensaje.objects.filter(
        destinatario=perfil
    ).select_related('remitente', 'odontograma', 'cliente').order_by('-fecha_envio')[:20]
    
    # Obtener mensajes enviados
    mensajes_enviados = Mensaje.objects.filter(
        remitente=perfil
    ).select_related('destinatario', 'odontograma', 'cliente').order_by('-fecha_envio')[:20]
    
    # Contar mensajes no leídos
    mensajes_no_leidos = mensajes_recibidos.filter(estado='no_leido').count()
    
    # Preparar datos para JSON
    mensajes_data = []
    for mensaje in mensajes_recibidos:
        mensajes_data.append({
            'id': mensaje.id,
            'tipo': mensaje.tipo,
            'asunto': mensaje.asunto,
            'mensaje': mensaje.mensaje,
            'remitente': mensaje.remitente.nombre_completo,
            'remitente_rol': mensaje.remitente.get_rol_display(),
            'estado': mensaje.estado,
            'fecha_envio': mensaje.fecha_envio.strftime('%d/%m/%Y %H:%M'),
            'odontograma_id': mensaje.odontograma.id if mensaje.odontograma else None,
            'cliente_nombre': mensaje.cliente.nombre_completo if mensaje.cliente else None,
            'tiene_archivo': mensaje.tiene_archivo(),
            'archivo_url': mensaje.archivo_adjunto.url if mensaje.tiene_archivo() else None,
            'archivo_nombre': mensaje.archivo_adjunto.name.split('/')[-1] if mensaje.tiene_archivo() else None,
            'es_recibido': True
        })
    
    for mensaje in mensajes_enviados:
        mensajes_data.append({
            'id': mensaje.id,
            'tipo': mensaje.tipo,
            'asunto': mensaje.asunto,
            'mensaje': mensaje.mensaje,
            'destinatario': mensaje.destinatario.nombre_completo,
            'destinatario_rol': mensaje.destinatario.get_rol_display(),
            'estado': mensaje.estado,
            'fecha_envio': mensaje.fecha_envio.strftime('%d/%m/%Y %H:%M'),
            'odontograma_id': mensaje.odontograma.id if mensaje.odontograma else None,
            'cliente_nombre': mensaje.cliente.nombre_completo if mensaje.cliente else None,
            'tiene_archivo': mensaje.tiene_archivo(),
            'archivo_url': mensaje.archivo_adjunto.url if mensaje.tiene_archivo() else None,
            'archivo_nombre': mensaje.archivo_adjunto.name.split('/')[-1] if mensaje.tiene_archivo() else None,
            'es_recibido': False
        })
    
    return JsonResponse({
        'mensajes': mensajes_data,
        'no_leidos': mensajes_no_leidos
    })

@login_required
def enviar_mensaje(request):
    """Vista para enviar un nuevo mensaje"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            
            destinatario_id = request.POST.get('destinatario_id')
            tipo = request.POST.get('tipo', 'general')
            asunto = request.POST.get('asunto')
            mensaje_texto = request.POST.get('mensaje')
            odontograma_id = request.POST.get('odontograma_id')
            cliente_id = request.POST.get('cliente_id')
            archivo = request.FILES.get('archivo_adjunto')
            
            # Validaciones
            if not destinatario_id or not asunto or not mensaje_texto:
                return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)
            
            destinatario = get_object_or_404(Perfil, id=destinatario_id)
            
            # VALIDACIÓN: Solo permitir mensajes entre roles diferentes
            if perfil.rol == destinatario.rol:
                return JsonResponse({'error': 'Solo puedes enviar mensajes a usuarios de roles diferentes'}, status=403)
            
            # Validar tamaño y tipo de archivo si se adjuntó
            if archivo:
                # Validar tamaño (máximo 10MB)
                if archivo.size > 10 * 1024 * 1024:
                    return JsonResponse({'error': 'El archivo no puede superar los 10MB'}, status=400)
                
                # Validar extensión
                extension = archivo.name.split('.')[-1].lower()
                extensiones_permitidas = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
                if extension not in extensiones_permitidas:
                    return JsonResponse({'error': f'Tipo de archivo no permitido. Extensiones permitidas: {", ".join(extensiones_permitidas)}'}, status=400)
            
            # Crear el mensaje
            mensaje = Mensaje.objects.create(
                remitente=perfil,
                destinatario=destinatario,
                tipo=tipo,
                asunto=asunto,
                mensaje=mensaje_texto,
                archivo_adjunto=archivo
            )
            
            # Agregar referencias opcionales
            if odontograma_id:
                try:
                    mensaje.odontograma = Odontograma.objects.get(id=odontograma_id)
                except Odontograma.DoesNotExist:
                    pass
            
            if cliente_id:
                try:
                    mensaje.cliente = Cliente.objects.get(id=cliente_id)
                except Cliente.DoesNotExist:
                    pass
            
            mensaje.save()
            
            return JsonResponse({
                'success': True,
                'mensaje': 'Mensaje enviado correctamente',
                'mensaje_id': mensaje.id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def marcar_como_leido(request, mensaje_id):
    """Marca un mensaje como leído"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            mensaje = get_object_or_404(Mensaje, id=mensaje_id, destinatario=perfil)
            mensaje.marcar_como_leido()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def archivar_mensaje(request, mensaje_id):
    """Archiva un mensaje"""
    if request.method == 'POST':
        try:
            perfil = Perfil.objects.get(user=request.user)
            mensaje = get_object_or_404(Mensaje, id=mensaje_id)
            
            # Verificar que el usuario sea remitente o destinatario
            if mensaje.remitente == perfil or mensaje.destinatario == perfil:
                mensaje.estado = 'archivado'
                mensaje.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'error': 'No tienes permiso'}, status=403)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def obtener_usuarios_disponibles(request):
    """Obtiene la lista de usuarios disponibles para enviar mensajes"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        
        # Si es dentista, puede enviar a administradores
        # Si es admin, puede enviar a dentistas
        if perfil.rol == 'dentista':
            usuarios = Perfil.objects.filter(rol='administrador', activo=True).exclude(id=perfil.id)
        else:
            usuarios = Perfil.objects.filter(rol='dentista', activo=True).exclude(id=perfil.id)
        
        usuarios_data = [{
            'id': u.id,
            'nombre': u.nombre_completo,
            'rol': u.get_rol_display(),
            'especialidad': u.especialidad or ''
        } for u in usuarios]
        
        return JsonResponse({'usuarios': usuarios_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


        return JsonResponse({'error': str(e)}, status=500)


        return JsonResponse({'error': str(e)}, status=500)


        return JsonResponse({'error': str(e)}, status=500)


        return JsonResponse({'error': str(e)}, status=500)

