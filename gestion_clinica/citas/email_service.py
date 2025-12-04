"""
Servicio de correo electrónico para gestion_clinica
Envía notificaciones por correo cuando se agendan o cancelan citas
"""
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import pytz
import logging

logger = logging.getLogger(__name__)


def _obtener_info_clinica():
    """
    Obtiene la información de la clínica desde el modelo InformacionClinica.
    Retorna un diccionario con los datos o valores por defecto.
    """
    try:
        from configuracion.models import InformacionClinica
        info = InformacionClinica.obtener()
        nombre_clinica = info.nombre_clinica or "Clínica Dental San Felipe"
        if nombre_clinica == "Clínica Dental":
            nombre_clinica = "Clínica Dental San Felipe"
        return {
            'nombre': nombre_clinica,
            'direccion': info.direccion or "",
            'telefono': info.telefono or "",
            'telefono_secundario': info.telefono_secundario or "",
            'email': info.email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'miclinicacontacto@gmail.com'),
            'horario': info.horario_atencion or "",
            'whatsapp': info.whatsapp or "",
        }
    except Exception as e:
        logger.warning(f"No se pudo obtener información de la clínica: {e}")
        return {
            'nombre': getattr(settings, 'CLINIC_NAME', "Clínica Dental San Felipe"),
            'direccion': getattr(settings, 'CLINIC_ADDRESS', ""),
            'telefono': getattr(settings, 'CLINIC_PHONE', ""),
            'telefono_secundario': "",
            'email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'miclinicacontacto@gmail.com'),
            'horario': "",
            'whatsapp': "",
        }


def enviar_email_confirmacion_cita(cita):
    """
    Envía notificación de confirmación de cita por correo electrónico.
    
    Args:
        cita: Objeto Cita del modelo
    
    Returns:
        bool: True si se envió exitosamente, False en caso contrario
    """
    # Obtener email de forma segura
    email_paciente = None
    try:
        # Intentar usar la propiedad email_paciente si existe
        email_paciente = getattr(cita, 'email_paciente', None)
        if callable(email_paciente):
            email_paciente = email_paciente()
    except (AttributeError, TypeError):
        email_paciente = None
    
    # Si no funciona, usar el campo paciente_email directamente
    if not email_paciente:
        email_paciente = getattr(cita, 'paciente_email', None)
    
    # Si aún no hay email, intentar desde el cliente
    if not email_paciente and hasattr(cita, 'cliente') and cita.cliente:
        email_paciente = getattr(cita.cliente, 'email', None)
    
    if not email_paciente:
        logger.warning(f"No hay email del paciente para enviar notificación de confirmación (Cita ID: {cita.id}). Campos disponibles: paciente_email={getattr(cita, 'paciente_email', None)}, cliente={cita.cliente if hasattr(cita, 'cliente') else None}")
        return False
    
    # Obtener información de la clínica
    info_clinica = _obtener_info_clinica()
    
    # Obtener nombre del dentista de forma segura
    dentista_nombre = ""
    dentista = getattr(cita, 'dentista', None)
    if dentista:
        if hasattr(dentista, 'nombre_completo'):
            dentista_nombre = getattr(dentista, 'nombre_completo', '') or ""
        else:
            try:
                from personal.models import Perfil
                try:
                    perfil = Perfil.objects.get(user=dentista)
                    dentista_nombre = getattr(perfil, 'nombre_completo', '') or ""
                except (Perfil.DoesNotExist, AttributeError):
                    dentista_nombre = f"{getattr(dentista, 'first_name', '')} {getattr(dentista, 'last_name', '')}".strip() or str(dentista)
            except (ImportError, RuntimeError):
                dentista_nombre = f"{getattr(dentista, 'first_name', '')} {getattr(dentista, 'last_name', '')}".strip() or str(dentista)
    
    # Obtener información del servicio
    servicio_nombre = ""
    tipo_servicio = getattr(cita, 'tipo_servicio', None)
    if tipo_servicio:
        servicio_nombre = getattr(tipo_servicio, 'nombre', '') or ''
    if not servicio_nombre:
        servicio_nombre = getattr(cita, 'tipo_consulta', '') or ''
    
    # Obtener precio
    precio_texto = ""
    if cita.precio_cobrado:
        precio_texto = f"${cita.precio_cobrado:,.0f}".replace(',', '.')
    
    # Obtener nombre del paciente de forma segura
    paciente_nombre = None
    try:
        # Intentar usar la propiedad nombre_paciente si existe
        paciente_nombre = getattr(cita, 'nombre_paciente', None)
        if callable(paciente_nombre):
            paciente_nombre = paciente_nombre()
    except (AttributeError, TypeError):
        paciente_nombre = None
    
    # Si no funciona, usar el campo paciente_nombre directamente
    if not paciente_nombre:
        paciente_nombre = getattr(cita, 'paciente_nombre', None)
    
    # Si aún no hay nombre, intentar desde el cliente
    if not paciente_nombre and hasattr(cita, 'cliente') and cita.cliente:
        paciente_nombre = getattr(cita.cliente, 'nombre_completo', None)
    
    paciente_nombre = paciente_nombre or "Paciente"
    
    # Nombre de la clínica
    nombre_clinica = info_clinica['nombre'] or "Clínica Dental San Felipe"
    if nombre_clinica == "Clínica Dental":
        nombre_clinica = "Clínica Dental San Felipe"
    
    # Obtener URL del mapa
    map_url = getattr(settings, 'CLINIC_MAP_URL', '')
    
    # Convertir fecha_hora a zona horaria de Chile antes de formatear
    try:
        # Obtener zona horaria de Chile
        chile_tz = pytz.timezone('America/Santiago')
        fecha_hora_original = cita.fecha_hora
        
        # IMPORTANTE: Con USE_TZ=True, Django automáticamente convierte las fechas de UTC a la zona horaria local
        # cuando se leen de la BD usando el ORM. Por lo tanto, si la fecha ya tiene timezone y no es UTC,
        # probablemente ya está en la zona horaria local (Chile). Solo necesitamos convertir si está en UTC.
        # 
        # Sin embargo, cuando se accede directamente a cita.fecha_hora desde cliente_web (que no usa el ORM
        # de gestion_clinica), puede que la fecha esté en UTC. Necesitamos verificar y convertir solo si es necesario.
        if timezone.is_naive(fecha_hora_original):
            # Si es naive, asumir que está en hora local de Chile (no UTC)
            # porque si estuviera en UTC, Django la habría convertido automáticamente con USE_TZ=True
            fecha_hora_chile = timezone.make_aware(fecha_hora_original, chile_tz)
        else:
            # Si ya tiene timezone, verificar si está en UTC
            if fecha_hora_original.tzinfo == pytz.UTC:
                # Está en UTC, convertir a Chile (UTC-3 en verano, UTC-4 en invierno)
                fecha_hora_chile = fecha_hora_original.astimezone(chile_tz)
            else:
                # Ya tiene timezone y no es UTC, probablemente ya está en hora local
                # Verificar si es Chile comparando los offsets
                try:
                    # Obtener el offset de la fecha original y del timezone de Chile
                    offset_original = fecha_hora_original.utcoffset()
                    offset_chile = chile_tz.utcoffset(fecha_hora_original.replace(tzinfo=None))
                    
                    # Si los offsets son iguales, ya está en hora de Chile
                    if offset_original == offset_chile:
                        fecha_hora_chile = fecha_hora_original
                    else:
                        # Está en otra zona, convertir a Chile
                        fecha_hora_chile = fecha_hora_original.astimezone(chile_tz)
                except Exception:
                    # Si hay error al comparar offsets, verificar por nombre
                    tz_str = str(fecha_hora_original.tzinfo)
                    if 'Santiago' in tz_str or tz_str == str(chile_tz):
                        fecha_hora_chile = fecha_hora_original
                    else:
                        fecha_hora_chile = fecha_hora_original.astimezone(chile_tz)
        
        logger.info(f"[DEBUG] Conversión de timezone para email cita {cita.id}: Original={fecha_hora_original} (naive={timezone.is_naive(fecha_hora_original)}, tzinfo={fecha_hora_original.tzinfo if not timezone.is_naive(fecha_hora_original) else 'naive'}, USE_TZ={getattr(settings, 'USE_TZ', False)}), Chile={fecha_hora_chile}, Hora={fecha_hora_chile.strftime('%H:%M')}")
    except Exception as e:
        logger.warning(f"Error al convertir zona horaria: {e}. Usando fecha original.")
        import traceback
        logger.error(traceback.format_exc())
        fecha_hora_chile = cita.fecha_hora
    
    # Construir mensaje HTML
    logger.info(f"[DEBUG] Intentando renderizar template de CONFIRMACIÓN para cita {cita.id}")
    try:
        # Intentar renderizar el template, primero con la ruta normal, luego con ruta absoluta si falla
        try:
            logger.info(f"[DEBUG] Intentando renderizar 'citas/emails/cita_confirmada.html' para cita {cita.id}")
            mensaje_html = render_to_string('citas/emails/cita_confirmada.html', {
                'cliente_nombre': paciente_nombre,
                'fecha_cita': fecha_hora_chile.strftime('%d/%m/%Y'),
                'hora_cita': fecha_hora_chile.strftime('%H:%M'),
                'dentista_nombre': dentista_nombre,
                'servicio_nombre': servicio_nombre,
                'precio_texto': precio_texto,
                'nombre_clinica': nombre_clinica,
                'direccion_clinica': info_clinica['direccion'],
                'telefono_clinica': info_clinica['telefono'],
                'email_clinica': info_clinica['email'],
                'horario_clinica': info_clinica['horario'],
                'map_url': map_url,
            })
        except Exception as template_error:
            # Si falla, intentar con ruta absoluta
            logger.warning(f"Error al renderizar template con ruta relativa: {template_error}. Intentando con ruta absoluta.")
            import os
            # Buscar el template en la ruta absoluta de gestion_clinica
            # Intentar múltiples rutas posibles
            # Buscar el template en múltiples ubicaciones posibles
            posibles_rutas = []
            
            # Ruta 1: Desde el directorio de gestion_clinica (cuando se llama desde cliente_web)
            # El archivo está en: gestion_clinica/citas/email_service.py
            # El template está en: gestion_clinica/citas/templates/citas/emails/cita_confirmada.html
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            posibles_rutas.append(os.path.join(base_dir, 'citas', 'templates', 'citas', 'emails', 'cita_confirmada.html'))
            
            # Ruta 2: Desde el directorio actual usando rutas relativas
            posibles_rutas.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'citas', 'templates', 'citas', 'emails', 'cita_confirmada.html'))
            
            # Ruta 3: Buscar en el directorio padre del proyecto (si estamos en cliente_web)
            # El proyecto está en: Proyecto gestion clinica dental/
            # gestion_clinica está en: Proyecto gestion clinica dental/gestion_clinica/
            proyecto_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            posibles_rutas.append(os.path.join(proyecto_dir, 'gestion_clinica', 'citas', 'templates', 'citas', 'emails', 'cita_confirmada.html'))
            
            template_encontrado = False
            for template_path in posibles_rutas:
                template_path = os.path.normpath(template_path)
                logger.info(f"[DEBUG] Intentando encontrar template en: {template_path}")
                if os.path.exists(template_path):
                    logger.info(f"[DEBUG] Template encontrado en: {template_path}")
                    try:
                        # Leer el archivo directamente y renderizarlo con Django
                        from django.template import Template, Context
                        from django.template.loader import get_template
                        from django.conf import settings as django_settings
                        
                        # Intentar agregar el directorio del template a los DIRS de templates
                        template_dir = os.path.dirname(template_path)
                        template_name = 'citas/emails/cita_confirmada.html'
                        
                        # Agregar el directorio padre de templates a DIRS si no está
                        if hasattr(django_settings, 'TEMPLATES') and django_settings.TEMPLATES:
                            for template_config in django_settings.TEMPLATES:
                                if 'DIRS' in template_config:
                                    # Agregar el directorio que contiene 'citas/templates'
                                    templates_base_dir = os.path.dirname(template_dir)  # Esto es 'citas/templates'
                                    templates_parent_dir = os.path.dirname(templates_base_dir)  # Esto es 'citas'
                                    if templates_parent_dir not in template_config['DIRS']:
                                        template_config['DIRS'].insert(0, templates_parent_dir)
                        
                        # Intentar usar render_to_string con el nombre del template
                        try:
                            mensaje_html = render_to_string(template_name, {
                                'cliente_nombre': paciente_nombre,
                                'fecha_cita': fecha_hora_chile.strftime('%d/%m/%Y'),
                                'hora_cita': fecha_hora_chile.strftime('%H:%M'),
                                'dentista_nombre': dentista_nombre,
                                'servicio_nombre': servicio_nombre,
                                'precio_texto': precio_texto,
                                'nombre_clinica': nombre_clinica,
                                'direccion_clinica': info_clinica['direccion'],
                                'telefono_clinica': info_clinica['telefono'],
                                'email_clinica': info_clinica['email'],
                                'horario_clinica': info_clinica['horario'],
                                'map_url': map_url,
                            })
                            template_encontrado = True
                            logger.info(f"[DEBUG] Template renderizado exitosamente usando render_to_string")
                            break
                        except Exception as e2:
                            # Si falla, leer el archivo directamente
                            logger.warning(f"Error al usar render_to_string: {e2}. Leyendo archivo directamente.")
                            with open(template_path, 'r', encoding='utf-8') as f:
                                template_content = f.read()
                            template = Template(template_content)
                            mensaje_html = template.render(Context({
                                'cliente_nombre': paciente_nombre,
                                'fecha_cita': fecha_hora_chile.strftime('%d/%m/%Y'),
                                'hora_cita': fecha_hora_chile.strftime('%H:%M'),
                                'dentista_nombre': dentista_nombre,
                                'servicio_nombre': servicio_nombre,
                                'precio_texto': precio_texto,
                                'nombre_clinica': nombre_clinica,
                                'direccion_clinica': info_clinica['direccion'],
                                'telefono_clinica': info_clinica['telefono'],
                                'email_clinica': info_clinica['email'],
                                'horario_clinica': info_clinica['horario'],
                                'map_url': map_url,
                            }))
                            template_encontrado = True
                            logger.info(f"[DEBUG] Template renderizado exitosamente leyendo archivo directamente")
                            break
                    except Exception as e:
                        logger.warning(f"Error al renderizar template desde {template_path}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
            
            if not template_encontrado:
                logger.error(f"No se pudo encontrar el template en ninguna de las rutas: {posibles_rutas}")
                raise template_error
    except Exception as e:
        logger.warning(f"No se pudo renderizar template HTML, usando texto plano: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Fallback a texto plano (usar fecha_hora_chile que ya fue calculada)
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f0fdfa; border-left: 4px solid #14b8a6;">
                <h2 style="color: #14b8a6; margin-top: 0;">{nombre_clinica}</h2>
                <p>Hola {paciente_nombre}!</p>
                <p>Gracias por reservar tu cita con nosotros. Tu cita ha sido agendada exitosamente.</p>
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #64748b; margin-top: 0;">Información de tu Cita:</h3>
                    <p><strong>Fecha:</strong> {fecha_hora_chile.strftime('%d/%m/%Y')}</p>
                    <p><strong>Hora:</strong> {fecha_hora_chile.strftime('%H:%M')}</p>
                    {f'<p><strong>Dentista:</strong> {dentista_nombre}</p>' if dentista_nombre else ''}
                    {f'<p><strong>Servicio:</strong> {servicio_nombre}</p>' if servicio_nombre else ''}
                    {f'<p><strong>Precio:</strong> {precio_texto}</p>' if precio_texto else ''}
                </div>
                <p>Recomendación: Llega 10 minutos antes para facilitar la atención.</p>
                {f'<p><strong>Dirección:</strong> {info_clinica["direccion"]}</p>' if info_clinica['direccion'] else ''}
                {f'<p><strong>Contacto:</strong> {info_clinica["telefono"]}</p>' if info_clinica['telefono'] else ''}
                {f'<p><strong>Email:</strong> {info_clinica["email"]}</p>' if info_clinica['email'] else ''}
                <p style="margin-top: 30px; color: #64748b; font-size: 0.9em;">Saludos,<br>{nombre_clinica}</p>
            </div>
        </body>
        </html>
        """
    
    # Crear el email
    asunto = f"Confirmación de Cita - {nombre_clinica}"
    email_clinica = info_clinica['email'] or getattr(settings, 'DEFAULT_FROM_EMAIL', 'miclinicacontacto@gmail.com')
    
    try:
        # Crear el email con EmailMultiAlternatives para asegurar que se envíe como HTML
        # Proporcionar versión de texto plano como fallback
        texto_plano = f"""
Confirmación de Cita - {nombre_clinica}

Hola {paciente_nombre}!

Gracias por reservar tu cita con nosotros. Tu cita ha sido agendada exitosamente.

INFORMACIÓN DE TU CITA:
Fecha: {fecha_hora_chile.strftime('%d/%m/%Y')}
Hora: {fecha_hora_chile.strftime('%H:%M')}
{f'Dentista: {dentista_nombre}' if dentista_nombre else ''}
{f'Servicio: {servicio_nombre}' if servicio_nombre else ''}
{f'Precio: {precio_texto}' if precio_texto else ''}

Recomendación: Llega 10 minutos antes para facilitar la atención.

Saludos,
{nombre_clinica}
        """
        
        email = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano.strip(),  # Versión de texto plano
            from_email=email_clinica,
            to=[email_paciente],
        )
        email.attach_alternative(mensaje_html, "text/html")
        
        # Enviar email
        email.send(fail_silently=False)
        logger.info(f"Correo de confirmación enviado exitosamente a {email_paciente} para cita {cita.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar correo de confirmación a {email_paciente} para cita {cita.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def enviar_email_cancelacion_cita(cita):
    """
    Envía notificación de cancelación de cita por correo electrónico.
    
    Args:
        cita: Objeto Cita del modelo
    
    Returns:
        bool: True si se envió exitosamente, False en caso contrario
    """
    # Obtener email de forma segura
    email_paciente = None
    try:
        email_paciente = getattr(cita, 'email_paciente', None)
        if callable(email_paciente):
            email_paciente = email_paciente()
    except (AttributeError, TypeError):
        email_paciente = None
    
    if not email_paciente:
        email_paciente = getattr(cita, 'paciente_email', None)
    
    if not email_paciente and hasattr(cita, 'cliente') and cita.cliente:
        email_paciente = getattr(cita.cliente, 'email', None)
    
    if not email_paciente:
        logger.warning(f"No hay email del paciente para enviar notificación de cancelación (Cita ID: {cita.id})")
        return False
    
    # Obtener información de la clínica
    info_clinica = _obtener_info_clinica()
    
    # Obtener nombre del dentista de forma segura
    dentista_nombre = ""
    dentista = getattr(cita, 'dentista', None)
    if dentista:
        if hasattr(dentista, 'nombre_completo'):
            dentista_nombre = getattr(dentista, 'nombre_completo', '') or ""
        else:
            try:
                from personal.models import Perfil
                try:
                    perfil = Perfil.objects.get(user=dentista)
                    dentista_nombre = getattr(perfil, 'nombre_completo', '') or ""
                except (Perfil.DoesNotExist, AttributeError):
                    dentista_nombre = f"{getattr(dentista, 'first_name', '')} {getattr(dentista, 'last_name', '')}".strip() or str(dentista)
            except (ImportError, RuntimeError):
                dentista_nombre = f"{getattr(dentista, 'first_name', '')} {getattr(dentista, 'last_name', '')}".strip() or str(dentista)
    
    # Obtener información del servicio
    servicio_nombre = ""
    tipo_servicio = getattr(cita, 'tipo_servicio', None)
    if tipo_servicio:
        servicio_nombre = getattr(tipo_servicio, 'nombre', '') or ''
    if not servicio_nombre:
        servicio_nombre = getattr(cita, 'tipo_consulta', '') or ''
    
    # Obtener nombre del paciente de forma segura
    paciente_nombre = None
    try:
        paciente_nombre = getattr(cita, 'nombre_paciente', None)
        if callable(paciente_nombre):
            paciente_nombre = paciente_nombre()
    except (AttributeError, TypeError):
        paciente_nombre = None
    
    if not paciente_nombre:
        paciente_nombre = getattr(cita, 'paciente_nombre', None)
    
    if not paciente_nombre and hasattr(cita, 'cliente') and cita.cliente:
        paciente_nombre = getattr(cita.cliente, 'nombre_completo', None)
    
    paciente_nombre = paciente_nombre or "Paciente"
    
    # Nombre de la clínica
    nombre_clinica = info_clinica['nombre'] or "Clínica Dental San Felipe"
    if nombre_clinica == "Clínica Dental":
        nombre_clinica = "Clínica Dental San Felipe"
    
    # Convertir fecha_hora a zona horaria de Chile antes de formatear
    try:
        chile_tz = pytz.timezone('America/Santiago')
        fecha_hora_original = cita.fecha_hora
        
        if timezone.is_naive(fecha_hora_original):
            # Si es naive, asumir que está en hora local de Chile
            fecha_hora_chile = timezone.make_aware(fecha_hora_original, chile_tz)
        else:
            # Si ya tiene timezone, verificar si está en UTC o en otra zona
            if fecha_hora_original.tzinfo == pytz.UTC:
                # Está en UTC, convertir a Chile
                fecha_hora_chile = fecha_hora_original.astimezone(chile_tz)
            elif str(fecha_hora_original.tzinfo) == str(chile_tz) or 'Santiago' in str(fecha_hora_original.tzinfo):
                # Ya está en hora de Chile, usar directamente
                fecha_hora_chile = fecha_hora_original
            else:
                # Está en otra zona, convertir a Chile
                fecha_hora_chile = fecha_hora_original.astimezone(chile_tz)
        
        logger.info(f"[DEBUG] Conversión de timezone para email cancelación cita {cita.id}: Original={fecha_hora_original}, Chile={fecha_hora_chile}, Hora={fecha_hora_chile.strftime('%H:%M')}")
    except Exception as e:
        logger.warning(f"Error al convertir zona horaria: {e}. Usando fecha original.")
        import traceback
        logger.error(traceback.format_exc())
        fecha_hora_chile = cita.fecha_hora
    
    # Construir mensaje HTML
    try:
        mensaje_html = render_to_string('citas/emails/cita_cancelada.html', {
            'cliente_nombre': paciente_nombre,
            'fecha_cita': fecha_hora_chile.strftime('%d/%m/%Y'),
            'hora_cita': fecha_hora_chile.strftime('%H:%M'),
            'dentista_nombre': dentista_nombre,
            'servicio_nombre': servicio_nombre,
            'nombre_clinica': nombre_clinica,
            'direccion_clinica': info_clinica['direccion'],
            'telefono_clinica': info_clinica['telefono'],
            'email_clinica': info_clinica['email'],
        })
    except Exception as e:
        logger.warning(f"No se pudo renderizar template HTML, usando texto plano: {e}")
        # Fallback a texto plano (usar fecha_hora_chile que ya fue calculada)
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f0fdfa; border-left: 4px solid #14b8a6;">
                <h2 style="color: #14b8a6; margin-top: 0;">{nombre_clinica}</h2>
                <p>Hola {paciente_nombre},</p>
                <p>Te informamos que tu cita ha sido cancelada.</p>
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #64748b; margin-top: 0;">Información de la Cita Cancelada:</h3>
                    <p><strong>Fecha:</strong> {fecha_hora_chile.strftime('%d/%m/%Y')}</p>
                    <p><strong>Hora:</strong> {fecha_hora_chile.strftime('%H:%M')}</p>
                    {f'<p><strong>Dentista:</strong> {dentista_nombre}</p>' if dentista_nombre else ''}
                    {f'<p><strong>Servicio:</strong> {servicio_nombre}</p>' if servicio_nombre else ''}
                </div>
                <p>Si fue un error o deseas reagendar, por favor contáctanos.</p>
                {f'<p><strong>Contacto:</strong> {info_clinica["telefono"]}</p>' if info_clinica['telefono'] else ''}
                {f'<p><strong>Email:</strong> {info_clinica["email"]}</p>' if info_clinica['email'] else ''}
                <p style="margin-top: 30px; color: #64748b; font-size: 0.9em;">Saludos,<br>{nombre_clinica}</p>
            </div>
        </body>
        </html>
        """
    
    # Crear el email
    asunto = f"Cancelación de Cita - {nombre_clinica}"
    email_clinica = info_clinica['email'] or getattr(settings, 'DEFAULT_FROM_EMAIL', 'miclinicacontacto@gmail.com')
    
    try:
        # Crear el email con EmailMultiAlternatives para asegurar que se envíe como HTML
        # Proporcionar versión de texto plano como fallback
        texto_plano = f"""
Cancelación de Cita - {nombre_clinica}

Hola {paciente_nombre},

Te informamos que tu cita ha sido cancelada.

INFORMACIÓN DE LA CITA CANCELADA:
Fecha: {fecha_hora_chile.strftime('%d/%m/%Y')}
Hora: {fecha_hora_chile.strftime('%H:%M')}
{f'Dentista: {dentista_nombre}' if dentista_nombre else ''}
{f'Servicio: {servicio_nombre}' if servicio_nombre else ''}

Si fue un error o deseas reagendar, por favor contáctanos.

Saludos,
{nombre_clinica}
        """
        
        email = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano.strip(),  # Versión de texto plano
            from_email=email_clinica,
            to=[email_paciente],
        )
        email.attach_alternative(mensaje_html, "text/html")
        
        # Enviar email
        email.send(fail_silently=False)
        logger.info(f"Correo de cancelación enviado exitosamente a {email_paciente} para cita {cita.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar correo de cancelación a {email_paciente} para cita {cita.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
