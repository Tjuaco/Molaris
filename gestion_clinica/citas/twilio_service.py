"""
Servicio de Twilio para gestion_clinica
Envía notificaciones SMS y WhatsApp cuando se agendan citas desde el sistema interno
"""
from twilio.rest import Client
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
import pytz
import re
import logging

logger = logging.getLogger(__name__)


def _normalizar_telefono_chile(telefono: str | None) -> str | None:
    """
    Normaliza número de teléfono chileno a formato +56XXXXXXXXX
    """
    if not telefono:
        return None
    
    # Quitar espacios, guiones y caracteres no numéricos excepto '+' inicial
    telefono = telefono.strip()
    if telefono.startswith('+'):
        telefono_limpio = '+' + re.sub(r"\D", "", telefono[1:])
    else:
        telefono_limpio = re.sub(r"\D", "", telefono)

    # Si ya viene en formato +56...
    if telefono_limpio.startswith("+56"):
        return telefono_limpio

    # Si viene empezando por 56...
    if telefono_limpio.startswith("56"):
        return "+" + telefono_limpio

    # Si empieza por 0, quitar ceros a la izquierda
    telefono_limpio = telefono_limpio.lstrip('0')

    # Caso típico móvil chileno: 9XXXXXXXX (9 + 8 dígitos)
    if telefono_limpio.startswith('9') and len(telefono_limpio) == 9:
        return "+56" + telefono_limpio

    # Si quedan 8 dígitos, asumir que es móvil y agregar +569
    if len(telefono_limpio) == 8:
        return "+569" + telefono_limpio

    # Si quedan 9 dígitos y no empieza por 9, agregar +56
    if len(telefono_limpio) == 9 and not telefono_limpio.startswith('9'):
        return "+56" + telefono_limpio

    # Como último recurso: si tiene 11 dígitos y empezó por 56
    if len(telefono_limpio) == 11 and telefono_limpio.startswith('56'):
        return "+" + telefono_limpio

    return None


def _obtener_info_clinica():
    """
    Obtiene la información de la clínica desde el modelo InformacionClinica.
    Retorna un diccionario con los datos o valores por defecto.
    """
    try:
        from configuracion.models import InformacionClinica
        info = InformacionClinica.obtener()
        nombre_clinica = info.nombre_clinica or "Clínica Dental San Felipe"
        # Asegurar que use "Clínica Dental San Felipe" si está vacío o es el predeterminado
        if nombre_clinica == "Clínica Dental":
            nombre_clinica = "Clínica Dental San Felipe"
        return {
            'nombre': nombre_clinica,
            'direccion': info.direccion or "",
            'telefono': info.telefono or "",
            'telefono_secundario': info.telefono_secundario or "",
            'email': info.email or "",
            'horario': info.horario_atencion or "",
            'whatsapp': info.whatsapp or "",
            'sitio_web': info.sitio_web or "",
        }
    except Exception as e:
        logger.warning(f"No se pudo obtener información de la clínica: {e}")
        return {
            'nombre': getattr(settings, 'CLINIC_NAME', "Clínica Dental San Felipe"),
            'direccion': getattr(settings, 'CLINIC_ADDRESS', ""),
            'telefono': getattr(settings, 'CLINIC_PHONE', ""),
            'telefono_secundario': "",
            'email': getattr(settings, 'CLINIC_EMAIL', ""),
            'horario': "",
            'whatsapp': "",
            'sitio_web': getattr(settings, 'CLINIC_WEBSITE', ""),
        }


def _obtener_cliente_twilio():
    """
    Obtiene el cliente de Twilio usando las credenciales de settings.
    Usa EXACTAMENTE la misma lógica que funcionaba en cliente_web/reservas/services.py
    """
    # Usar directamente como en services.py que funcionaba
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    
    if not account_sid or not auth_token:
        logger.warning("Twilio no configurado. Verifica TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN en settings.")
        return None
    
    try:
        return Client(account_sid, auth_token)
    except Exception as e:
        logger.error(f"Error al inicializar cliente Twilio: {e}")
        return None


def enviar_whatsapp_confirmacion_cita(cita, telefono_override: str | None = None):
    """
    Envía confirmación de cita por WhatsApp usando Twilio.
    Usa EXACTAMENTE la misma lógica que funcionaba en cliente_web/reservas/services.py
    
    Args:
        cita: Objeto Cita del modelo
        telefono_override: Teléfono alternativo (opcional)
    
    Returns:
        dict: Información del mensaje enviado (sid, status, etc.) o None si falla
    """
    # Crear cliente directamente como en services.py que funcionaba
    try:
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        if not account_sid or not auth_token:
            logger.warning("Twilio no configurado. Verifica TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN.")
            return None
        client = Client(account_sid, auth_token)
    except Exception as e:
        logger.error(f"Error al inicializar cliente Twilio: {e}")
        return None
    
    # Normalizar número antes de enviar (Chile: +56)
    # Obtener teléfono de forma segura
    telefono = telefono_override
    if not telefono:
        # Intentar usar la propiedad telefono_paciente si existe
        try:
            telefono = getattr(cita, 'telefono_paciente', None)
            if callable(telefono):
                telefono = telefono()
        except (AttributeError, TypeError):
            telefono = None
        
        # Si no funciona, usar el campo paciente_telefono directamente
        if not telefono:
            telefono = getattr(cita, 'paciente_telefono', None)
        
        # Si aún no hay teléfono, intentar desde el cliente
        if not telefono and hasattr(cita, 'cliente') and cita.cliente:
            telefono = getattr(cita.cliente, 'telefono', None)
    
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        logger.warning(f"No hay teléfono del paciente para enviar WhatsApp (Cita ID: {cita.id})")
        return None

    # Obtener información de la clínica
    info_clinica = _obtener_info_clinica()
    
    # Obtener nombre del dentista
    dentista_nombre = ""
    if cita.dentista:
        try:
            # cita.dentista es un Perfil, que tiene nombre_completo
            if hasattr(cita.dentista, 'nombre_completo'):
                dentista_nombre = cita.dentista.nombre_completo or ""
            else:
                # Si por alguna razón es un User, intentar obtener el Perfil asociado
                # Solo si la app 'personal' está disponible (no disponible en cliente_web)
                try:
                    from personal.models import Perfil
                    try:
                        perfil = Perfil.objects.get(user=cita.dentista)
                        dentista_nombre = perfil.nombre_completo or ""
                    except (Perfil.DoesNotExist, AttributeError):
                        dentista_nombre = f"{cita.dentista.first_name} {cita.dentista.last_name}".strip() or str(cita.dentista)
                except (ImportError, RuntimeError):
                    # Si no se puede importar Perfil (por ejemplo, desde cliente_web), usar nombre del User
                    dentista_nombre = f"{cita.dentista.first_name} {cita.dentista.last_name}".strip() or str(cita.dentista)
        except AttributeError:
            dentista_nombre = str(cita.dentista) if cita.dentista else ""
    
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
    
    # Obtener nombre del paciente
    paciente_nombre = getattr(cita, 'paciente_nombre', None) or getattr(cita, 'nombre_paciente', None) or "Paciente"
    if paciente_nombre == "Paciente" and hasattr(cita, 'cliente') and cita.cliente:
        paciente_nombre = getattr(cita.cliente, 'nombre_completo', None) or paciente_nombre
    
    # Nombre de la clínica (usar "Clínica Dental San Felipe" como predeterminado)
    nombre_clinica = info_clinica['nombre'] or "Clínica Dental San Felipe"
    if nombre_clinica == "Clínica Dental":
        nombre_clinica = "Clínica Dental San Felipe"
    
    # Construir mensaje WhatsApp profesional (sin emojis excepto uno en el título)
    # WhatsApp soporta formato con asteriscos para negrita
    seccion_header = f"🦷 *{nombre_clinica}*\n\n"
    seccion_saludo = (
        f"Hola {paciente_nombre}, gracias por reservar tu cita con nosotros.\n\n"
    )
    
    # Convertir fecha_hora a zona horaria de Chile antes de formatear
    # Usar try-except más robusto para evitar que falle el envío
    fecha_hora_chile = cita.fecha_hora
    try:
        chile_tz = pytz.timezone('America/Santiago')
        if timezone.is_naive(cita.fecha_hora):
            fecha_hora_utc = timezone.make_aware(cita.fecha_hora, pytz.UTC)
            fecha_hora_chile = fecha_hora_utc.astimezone(chile_tz)
        else:
            # Si ya tiene timezone, convertir a Chile
            fecha_hora_chile = cita.fecha_hora.astimezone(chile_tz)
        logger.info(f"[DEBUG] Conversión de timezone para WhatsApp cita {cita.id}: Original={cita.fecha_hora}, Chile={fecha_hora_chile}")
    except Exception as e:
        logger.warning(f"Error al convertir zona horaria para WhatsApp de confirmación: {e}. Usando fecha original.")
        import traceback
        logger.error(traceback.format_exc())
        # No fallar el envío si hay error en la conversión
        fecha_hora_chile = cita.fecha_hora
    
    seccion_fecha = (
        f"*INFORMACIÓN DE TU CITA*\n"
        f"Fecha: {fecha_hora_chile.strftime('%d/%m/%Y')}\n"
        f"Hora: {fecha_hora_chile.strftime('%H:%M')}\n"
    )
    
    if dentista_nombre:
        seccion_fecha += f"Dentista: {dentista_nombre}\n"
    
    if servicio_nombre:
        seccion_fecha += f"Servicio: {servicio_nombre}\n"
    
    if precio_texto:
        seccion_fecha += f"Precio: {precio_texto}\n"
    
    seccion_fecha += "\nRecomendación: Llega 10 minutos antes para facilitar la atención.\n\n"
    
    seccion_ubicacion = ""
    if info_clinica['direccion']:
        seccion_ubicacion += f"*UBICACIÓN*\n"
        seccion_ubicacion += f"Dirección: {info_clinica['direccion']}\n"
    
    # Usar la URL de Maps proporcionada
    map_url = 'https://maps.app.goo.gl/be6QjzVein4JcYBn8'
    # Si hay una URL en settings, usarla, sino usar la por defecto
    map_url_settings = getattr(settings, 'CLINIC_MAP_URL', '')
    if map_url_settings:
        map_url = map_url_settings
    
    if map_url:
        seccion_ubicacion += f"Cómo llegar: {map_url}\n"
    
    if seccion_ubicacion:
        seccion_ubicacion += "\n"
    
    seccion_contacto = ""
    if info_clinica['telefono'] or info_clinica['email']:
        seccion_contacto += f"*CONTACTO*\n"
        if info_clinica['telefono']:
            seccion_contacto += f"Teléfono: {info_clinica['telefono']}\n"
        if info_clinica['email']:
            seccion_contacto += f"Email: {info_clinica['email']}\n"
        if info_clinica['sitio_web']:
            seccion_contacto += f"Sitio web: {info_clinica['sitio_web']}\n"
    
    if seccion_contacto:
        seccion_contacto += "\n"
    
    seccion_recordatorio = (
        "*IMPORTANTE*\n"
        "• Si deseas cambiar o cancelar tu cita, contáctanos con anticipación.\n"
        "• Mantén tu teléfono disponible para recordatorios.\n\n"
        "Esperamos verte y cuidar tu sonrisa."
    )

    body = seccion_header + seccion_saludo + seccion_fecha + seccion_ubicacion + seccion_contacto + seccion_recordatorio

    # Configuración del remitente (WhatsApp Business o sandbox)
    # Usar EXACTAMENTE la misma lógica que funcionaba en cliente_web/reservas/services.py
    whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_BUSINESS_NUMBER", None)
    if not whatsapp_from:
        whatsapp_from = getattr(settings, "TWILIO_FROM_WHATSAPP", None)
    if not whatsapp_from:
        whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    
    # Asegurar que tenga el formato correcto
    if not whatsapp_from.startswith("whatsapp:"):
        whatsapp_from = f"whatsapp:{whatsapp_from}"
    
    # Formato del número de destino (igual que services.py que funcionaba)
    telefono_whatsapp = f"whatsapp:{telefono}"
    logger.info(f"[DEBUG] Enviando WhatsApp desde {whatsapp_from} a {telefono_whatsapp} para cita {cita.id}")
    logger.info(f"[DEBUG] Body del mensaje (longitud: {len(body)} caracteres): {body[:100]}...")
    
    try:
        from twilio.base.exceptions import TwilioException
        
        # Usar EXACTAMENTE la misma estructura que funcionaba en cliente_web/reservas/services.py
        status_callback = getattr(settings, "TWILIO_STATUS_CALLBACK", None)
        logger.info(f"[DEBUG] Llamando a client.messages.create con from_={whatsapp_from}, to={telefono_whatsapp}")
        message = client.messages.create(
            from_=whatsapp_from,
            to=telefono_whatsapp,
            body=body,
            status_callback=status_callback,
        )
        
        logger.info(f"[DEBUG] Mensaje creado exitosamente. SID: {message.sid}, Status: {getattr(message, 'status', 'unknown')}")
        
        # Guardar el SID en la cita (igual que services.py)
        if hasattr(cita, 'whatsapp_message_sid'):
            cita.whatsapp_message_sid = message.sid
            cita.save(update_fields=["whatsapp_message_sid"])
        
        logger.info(f"WhatsApp enviado SID={message.sid} status={getattr(message, 'status', 'unknown')} to={message.to} para cita {cita.id}")
        
        return {
            'sid': message.sid,
            'status': getattr(message, 'status', 'unknown'),
            'to': message.to,
            'from': message.from_,
        }
    except TwilioException as e:
        logger.error(f"[ERROR] Error de Twilio al enviar WhatsApp para cita {cita.id}: {e}")
        logger.error(f"[ERROR] Código: {getattr(e, 'code', 'N/A')}, Mensaje: {getattr(e, 'msg', 'N/A')}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"[ERROR] Error inesperado al enviar WhatsApp para cita {cita.id}: {e}")
        logger.error(f"[ERROR] Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def enviar_whatsapp_cancelacion_cita(cita, telefono_override: str | None = None):
    """
    Envía notificación de cancelación de cita por WhatsApp usando Twilio.
    Usa EXACTAMENTE la misma lógica que funcionaba en cliente_web/reservas/services.py
    
    Args:
        cita: Objeto Cita del modelo
        telefono_override: Teléfono alternativo (opcional)
    
    Returns:
        dict: Información del mensaje enviado (sid, status, etc.) o None si falla
    """
    # Crear cliente directamente como en services.py que funcionaba
    try:
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        if not account_sid or not auth_token:
            logger.warning("Twilio no configurado. Verifica TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN.")
            return None
        client = Client(account_sid, auth_token)
    except Exception as e:
        logger.error(f"Error al inicializar cliente Twilio: {e}")
        return None
    
    # Obtener teléfono de forma segura
    telefono = telefono_override
    if not telefono:
        # Intentar usar la propiedad telefono_paciente si existe
        try:
            telefono = getattr(cita, 'telefono_paciente', None)
            if callable(telefono):
                telefono = telefono()
        except (AttributeError, TypeError):
            telefono = None
        
        # Si no funciona, usar el campo paciente_telefono directamente
        if not telefono:
            telefono = getattr(cita, 'paciente_telefono', None)
        
        # Si aún no hay teléfono, intentar desde el cliente
        if not telefono and hasattr(cita, 'cliente') and cita.cliente:
            telefono = getattr(cita.cliente, 'telefono', None)
    
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        logger.warning(f"No hay teléfono del paciente para enviar WhatsApp de cancelación (Cita ID: {cita.id})")
        return None

    info_clinica = _obtener_info_clinica()
    paciente_nombre = getattr(cita, 'paciente_nombre', None) or getattr(cita, 'nombre_paciente', None) or "Paciente"
    if paciente_nombre == "Paciente" and hasattr(cita, 'cliente') and cita.cliente:
        paciente_nombre = getattr(cita.cliente, 'nombre_completo', None) or paciente_nombre
    
    # Nombre de la clínica
    nombre_clinica = info_clinica['nombre'] or "Clínica Dental San Felipe"
    if nombre_clinica == "Clínica Dental":
        nombre_clinica = "Clínica Dental San Felipe"
    
    # Convertir fecha_hora a zona horaria de Chile antes de formatear
    # Usar try-except más robusto para evitar que falle el envío
    fecha_hora_chile = cita.fecha_hora
    try:
        chile_tz = pytz.timezone('America/Santiago')
        if timezone.is_naive(cita.fecha_hora):
            fecha_hora_chile = timezone.make_aware(cita.fecha_hora, pytz.UTC).astimezone(chile_tz)
        else:
            fecha_hora_chile = cita.fecha_hora.astimezone(chile_tz)
    except Exception as e:
        logger.warning(f"Error al convertir zona horaria para WhatsApp de cancelación: {e}. Usando fecha original.")
        # No fallar el envío si hay error en la conversión
        fecha_hora_chile = cita.fecha_hora
    
    # Mensaje de cancelación (igual que services.py que funcionaba)
    body = (
        f"{nombre_clinica}: tu cita del {fecha_hora_chile.strftime('%d/%m/%Y %H:%M')} ha sido cancelada. "
        f"Si fue un error, por favor contáctanos para reagendar."
    )
    
    # Configuración del remitente (igual que services.py que funcionaba)
    whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_BUSINESS_NUMBER", None)
    if not whatsapp_from:
        whatsapp_from = getattr(settings, "TWILIO_FROM_WHATSAPP", None)
    if not whatsapp_from:
        whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    
    # Asegurar que tenga el formato correcto
    if not whatsapp_from.startswith("whatsapp:"):
        whatsapp_from = f"whatsapp:{whatsapp_from}"
    
    telefono_whatsapp = f"whatsapp:{telefono}"
    logger.info(f"[DEBUG] Enviando WhatsApp de cancelación desde {whatsapp_from} a {telefono_whatsapp} para cita {cita.id}")
    logger.info(f"[DEBUG] Body del mensaje: {body}")
    
    try:
        from twilio.base.exceptions import TwilioException
        
        # Usar EXACTAMENTE la misma estructura que funcionaba en cliente_web/reservas/services.py
        status_callback = getattr(settings, "TWILIO_STATUS_CALLBACK", None)
        logger.info(f"[DEBUG] Llamando a client.messages.create con from_={whatsapp_from}, to={telefono_whatsapp}")
        message = client.messages.create(
            from_=whatsapp_from,
            to=telefono_whatsapp,
            body=body,
            status_callback=status_callback,
        )
        
        logger.info(f"[DEBUG] Mensaje de cancelación creado exitosamente. SID: {message.sid}, Status: {getattr(message, 'status', 'unknown')}")
        logger.info(f"WhatsApp de cancelación enviado SID={message.sid} status={getattr(message, 'status', 'unknown')} para cita {cita.id}")
        return {
            'sid': message.sid,
            'status': getattr(message, 'status', 'unknown'),
            'to': message.to,
            'from': message.from_,
        }
    except TwilioException as e:
        logger.error(f"[ERROR] Error de Twilio al enviar WhatsApp de cancelación para cita {cita.id}: {e}")
        logger.error(f"[ERROR] Código: {getattr(e, 'code', 'N/A')}, Mensaje: {getattr(e, 'msg', 'N/A')}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"[ERROR] Error inesperado al enviar WhatsApp de cancelación para cita {cita.id}: {e}")
        logger.error(f"[ERROR] Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def enviar_sms_confirmacion_cita(cita, telefono_override: str | None = None):
    """
    Envía confirmación de cita por SMS usando Twilio.
    
    Args:
        cita: Objeto Cita del modelo
        telefono_override: Teléfono alternativo (opcional)
    
    Returns:
        dict: Información del mensaje enviado (sid, status, etc.) o None si falla
    """
    try:
        client = _obtener_cliente_twilio()
    except ValueError as e:
        logger.error(f"Error de configuración de Twilio: {e}")
        return None
    
    # Normalizar número antes de enviar (Chile: +56)
    # Obtener teléfono de forma segura
    telefono = telefono_override
    if not telefono:
        # Intentar usar la propiedad telefono_paciente si existe
        try:
            telefono = getattr(cita, 'telefono_paciente', None)
            if callable(telefono):
                telefono = telefono()
        except (AttributeError, TypeError):
            telefono = None
        
        # Si no funciona, usar el campo paciente_telefono directamente
        if not telefono:
            telefono = getattr(cita, 'paciente_telefono', None)
        
        # Si aún no hay teléfono, intentar desde el cliente
        if not telefono and hasattr(cita, 'cliente') and cita.cliente:
            telefono = getattr(cita.cliente, 'telefono', None)
    
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        logger.warning(f"No hay teléfono del paciente para enviar SMS (Cita ID: {cita.id})")
        return None

    # Obtener información de la clínica
    info_clinica = _obtener_info_clinica()
    
    # Obtener nombre del dentista
    dentista_nombre = ""
    if cita.dentista:
        try:
            # cita.dentista es un Perfil, que tiene nombre_completo
            if hasattr(cita.dentista, 'nombre_completo'):
                dentista_nombre = cita.dentista.nombre_completo or ""
            else:
                # Si por alguna razón es un User, intentar obtener el Perfil asociado
                # Solo si la app 'personal' está disponible (no disponible en cliente_web)
                try:
                    from personal.models import Perfil
                    try:
                        perfil = Perfil.objects.get(user=cita.dentista)
                        dentista_nombre = perfil.nombre_completo or ""
                    except (Perfil.DoesNotExist, AttributeError):
                        dentista_nombre = f"{cita.dentista.first_name} {cita.dentista.last_name}".strip() or str(cita.dentista)
                except (ImportError, RuntimeError):
                    # Si no se puede importar Perfil (por ejemplo, desde cliente_web), usar nombre del User
                    dentista_nombre = f"{cita.dentista.first_name} {cita.dentista.last_name}".strip() or str(cita.dentista)
        except AttributeError:
            dentista_nombre = str(cita.dentista) if cita.dentista else ""
    
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
    
    # Obtener nombre del paciente
    paciente_nombre = getattr(cita, 'paciente_nombre', None) or getattr(cita, 'nombre_paciente', None) or "Paciente"
    if paciente_nombre == "Paciente" and hasattr(cita, 'cliente') and cita.cliente:
        paciente_nombre = getattr(cita.cliente, 'nombre_completo', None) or paciente_nombre
    
    # Nombre de la clínica (usar "Clínica Dental San Felipe" como predeterminado)
    nombre_clinica = info_clinica['nombre'] or "Clínica Dental San Felipe"
    if nombre_clinica == "Clínica Dental":
        nombre_clinica = "Clínica Dental San Felipe"
    
    # Construir mensaje SMS (sin emojis para mejor compatibilidad)
    seccion_header = f"{nombre_clinica}\n\n"
    seccion_saludo = (
        f"Hola {paciente_nombre}! Gracias por reservar tu cita con nosotros.\n\n"
    )
    # Convertir fecha_hora a zona horaria de Chile antes de formatear
    try:
        chile_tz = pytz.timezone('America/Santiago')
        if timezone.is_naive(cita.fecha_hora):
            fecha_hora_utc = timezone.make_aware(cita.fecha_hora, pytz.UTC)
            fecha_hora_chile = fecha_hora_utc.astimezone(chile_tz)
        else:
            fecha_hora_chile = cita.fecha_hora.astimezone(chile_tz)
    except Exception as e:
        logger.warning(f"Error al convertir zona horaria para SMS: {e}. Usando fecha original.")
        fecha_hora_chile = cita.fecha_hora
    
    seccion_fecha = (
        f"Fecha: {fecha_hora_chile.strftime('%d/%m/%Y')}\n"
        f"Hora: {fecha_hora_chile.strftime('%H:%M')}\n"
        f"Recomendacion: Llega 10 minutos antes.\n\n"
    )
    
    if dentista_nombre:
        seccion_fecha += f"Dentista: {dentista_nombre}\n"
    
    if servicio_nombre:
        seccion_fecha += f"Servicio: {servicio_nombre}\n"
    
    if precio_texto:
        seccion_fecha += f"Precio: {precio_texto}\n"
    
    seccion_fecha += "\n"
    
    seccion_ubicacion = ""
    if info_clinica['direccion']:
        seccion_ubicacion += f"Direccion: {info_clinica['direccion']}\n"
    
    # Construir enlace de Google Maps si hay dirección
    map_url = getattr(settings, 'CLINIC_MAP_URL', '')
    if not map_url and info_clinica['direccion']:
        from urllib.parse import quote
        map_url = f"https://www.google.com/maps/search/?api=1&query={quote(info_clinica['direccion'])}"
    
    if map_url:
        seccion_ubicacion += f"Mapa: {map_url}\n"
    
    if seccion_ubicacion:
        seccion_ubicacion += "\n"
    
    seccion_contacto = ""
    if info_clinica['telefono']:
        seccion_contacto += f"Contacto: {info_clinica['telefono']}\n"
    if info_clinica['email']:
        seccion_contacto += f"Email: {info_clinica['email']}\n"
    if info_clinica['sitio_web']:
        seccion_contacto += f"Web: {info_clinica['sitio_web']}\n"
    
    if seccion_contacto:
        seccion_contacto += "\n"
    
    seccion_recordatorio = (
        "Recuerda:\n"
        "- Si deseas cambiar o cancelar tu cita, contactanos con anticipacion.\n"
        "- Manten tu telefono disponible para recordatorios.\n\n"
        "Esperamos verte y cuidar tu sonrisa!"
    )

    body = seccion_header + seccion_saludo + seccion_fecha + seccion_ubicacion + seccion_contacto + seccion_recordatorio

    # Configuración del remitente SMS
    from_sms = getattr(settings, "TWILIO_FROM_SMS", None)
    if not from_sms:
        from_sms = getattr(settings, "TWILIO_PHONE_NUMBER", None)
    
    if not from_sms:
        logger.error("No se ha configurado TWILIO_FROM_SMS o TWILIO_PHONE_NUMBER en settings")
        return None
    
    try:
        status_callback = getattr(settings, "TWILIO_STATUS_CALLBACK", None)
        logger.info(f"Intentando enviar SMS desde {from_sms} a {telefono} para cita {cita.id}")
        message = client.messages.create(
            from_=from_sms,
            to=telefono,  # SMS usa E.164 sin prefijo whatsapp
            body=body,
            status_callback=status_callback,
        )
        
        logger.info(f"SMS enviado SID={message.sid} status={getattr(message, 'status', 'unknown')} to={message.to} desde={message.from_} para cita {cita.id}")
        
        # Verificar si hay errores
        if hasattr(message, 'error_code') and message.error_code:
            logger.error(f"SMS tiene error_code={message.error_code} error_message={getattr(message, 'error_message', 'N/A')} para cita {cita.id}")
        
        # Guardar el SID en la cita si el campo existe
        if hasattr(cita, 'sms_message_sid'):
            cita.sms_message_sid = message.sid
            cita.save(update_fields=["sms_message_sid"])
        elif hasattr(cita, 'whatsapp_message_sid'):  # Compatibilidad con campo existente
            cita.whatsapp_message_sid = message.sid
            cita.save(update_fields=["whatsapp_message_sid"])
        
        return {
            'sid': message.sid,
            'status': getattr(message, 'status', 'unknown'),
            'to': message.to,
            'from': message.from_,
            'error_code': getattr(message, 'error_code', None),
            'error_message': getattr(message, 'error_message', None),
        }
    except Exception as e:
        logger.error(f"Error al enviar SMS para cita {cita.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def enviar_sms_cancelacion_cita(cita, telefono_override: str | None = None):
    """
    Envía notificación de cancelación de cita por SMS usando Twilio.
    
    Args:
        cita: Objeto Cita del modelo
        telefono_override: Teléfono alternativo (opcional)
    
    Returns:
        dict: Información del mensaje enviado (sid, status, etc.) o None si falla
    """
    try:
        client = _obtener_cliente_twilio()
    except ValueError as e:
        logger.error(f"Error de configuración de Twilio: {e}")
        return None
    
    # Obtener teléfono de forma segura
    telefono = telefono_override
    if not telefono:
        # Intentar usar la propiedad telefono_paciente si existe
        try:
            telefono = getattr(cita, 'telefono_paciente', None)
            if callable(telefono):
                telefono = telefono()
        except (AttributeError, TypeError):
            telefono = None
        
        # Si no funciona, usar el campo paciente_telefono directamente
        if not telefono:
            telefono = getattr(cita, 'paciente_telefono', None)
        
        # Si aún no hay teléfono, intentar desde el cliente
        if not telefono and hasattr(cita, 'cliente') and cita.cliente:
            telefono = getattr(cita.cliente, 'telefono', None)
    
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        logger.warning(f"No hay teléfono del paciente para enviar SMS de cancelación (Cita ID: {cita.id})")
        return None

    info_clinica = _obtener_info_clinica()
    paciente_nombre = getattr(cita, 'paciente_nombre', None) or getattr(cita, 'nombre_paciente', None) or "Paciente"
    if paciente_nombre == "Paciente" and hasattr(cita, 'cliente') and cita.cliente:
        paciente_nombre = getattr(cita.cliente, 'nombre_completo', None) or paciente_nombre
    
    # Convertir fecha_hora a zona horaria de Chile antes de formatear
    try:
        chile_tz = pytz.timezone('America/Santiago')
        if timezone.is_naive(cita.fecha_hora):
            fecha_hora_chile = timezone.make_aware(cita.fecha_hora, pytz.UTC).astimezone(chile_tz)
        else:
            fecha_hora_chile = cita.fecha_hora.astimezone(chile_tz)
    except Exception as e:
        logger.warning(f"Error al convertir zona horaria para SMS de cancelación: {e}. Usando fecha original.")
        fecha_hora_chile = cita.fecha_hora
    
    body = (
        f"{info_clinica['nombre']}: tu cita del {fecha_hora_chile.strftime('%d/%m/%Y %H:%M')} ha sido cancelada. "
        f"Si fue un error, por favor contactanos para reagendar."
    )
    
    # Configuración del remitente SMS
    from_sms = getattr(settings, "TWILIO_FROM_SMS", None)
    if not from_sms:
        from_sms = getattr(settings, "TWILIO_PHONE_NUMBER", None)
    
    if not from_sms:
        logger.error("No se ha configurado TWILIO_FROM_SMS o TWILIO_PHONE_NUMBER en settings")
        return None
    
    try:
        message = client.messages.create(
            from_=from_sms,
            to=telefono,  # SMS usa E.164 sin prefijo whatsapp
            body=body,
            status_callback=getattr(settings, "TWILIO_STATUS_CALLBACK", None),
        )
        
        logger.info(f"SMS de cancelación enviado SID={message.sid} para cita {cita.id}")
        return {
            'sid': message.sid,
            'status': getattr(message, 'status', 'unknown'),
            'to': message.to,
            'from': message.from_,
        }
    except Exception as e:
        logger.error(f"Error al enviar SMS de cancelación para cita {cita.id}: {e}")
        return None


def consultar_estado_mensaje(message_sid: str) -> dict | None:
    """
    Consulta el estado de un mensaje en Twilio por su SID.
    
    Args:
        message_sid: SID del mensaje de Twilio
    
    Returns:
        dict: Información del mensaje o None si falla
    """
    try:
        client = _obtener_cliente_twilio()
        msg = client.messages(message_sid).fetch()
        return {
            "sid": msg.sid,
            "status": msg.status,
            "to": msg.to,
            "from": msg.from_,
            "error_code": msg.error_code,
            "error_message": msg.error_message,
            "date_created": str(msg.date_created) if msg.date_created else None,
            "date_sent": str(msg.date_sent) if msg.date_sent else None,
            "date_updated": str(msg.date_updated) if msg.date_updated else None,
        }
    except Exception as e:
        logger.error(f"Error al consultar estado del mensaje {message_sid}: {e}")
        return None