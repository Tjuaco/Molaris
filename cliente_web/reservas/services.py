import json
from twilio.rest import Client
from django.conf import settings
from django.urls import reverse
import re

def _normalizar_telefono_chile(telefono: str | None) -> str | None:
    if not telefono:
        return None
    # Quitar espacios, guiones y caracteres no numéricos excepto '+' inicial
    telefono = telefono.strip()
    if telefono.startswith('+'):
        # Mantener '+' solo para la limpieza de lo demás
        telefono_limpio = '+' + re.sub(r"\D", "", telefono[1:])
    else:
        telefono_limpio = re.sub(r"\D", "", telefono)

    # Si ya viene en formato +56...
    if telefono_limpio.startswith("+56"):
        return telefono_limpio

    # Si viene empezando por 56...
    if telefono_limpio.startswith("56"):
        return "+" + telefono_limpio

    # Si empieza por 0, quitar ceros a la izquierda y continuar
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

    # Como último recurso: si tiene 11 dígitos y no empezó por 56, asumir ya incluye 56
    if len(telefono_limpio) == 11 and telefono_limpio.startswith('56'):
        return "+" + telefono_limpio

    # No se pudo normalizar confiablemente
    return None


def enviar_whatsapp_confirmacion(cita, telefono_override: str | None = None):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # Normalizar número antes de enviar (Chile: +56)
    telefono = telefono_override or cita.paciente_telefono
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        raise ValueError("No hay teléfono del paciente para enviar WhatsApp")

    # Construir enlaces simples de confirmación/cancelación
    base = getattr(settings, "SITE_URL", "")
    confirm_url = base + reverse('confirmar_cita', args=[cita.id])
    cancel_url = base + reverse('cancelar_cita_token', args=[cita.id])

    clinic = getattr(settings, "CLINIC_NAME", "Clínica")
    address = getattr(settings, "CLINIC_ADDRESS", "")
    phone = getattr(settings, "CLINIC_PHONE", "")
    map_url = getattr(settings, "CLINIC_MAP_URL", "")
    lat = getattr(settings, "CLINIC_LAT", "")
    lng = getattr(settings, "CLINIC_LNG", "")
    clinic_email = getattr(settings, "CLINIC_EMAIL", "")
    clinic_web = getattr(settings, "CLINIC_WEBSITE", "")
    
    # Configuración del remitente (WhatsApp Business o sandbox)
    whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_BUSINESS_NUMBER", settings.TWILIO_FROM_WHATSAPP)
    if not whatsapp_from.startswith("whatsapp:"):
        whatsapp_from = f"whatsapp:{whatsapp_from}"

    # Construir enlace de Google Maps si no viene uno directo
    if not map_url:
        if lat and lng:
            map_url = f"https://www.google.com/maps?q={lat},{lng}"
        elif address:
            from urllib.parse import quote
            map_url = f"https://www.google.com/maps/search/?api=1&query={quote(address)}"

    paciente_nombre = cita.paciente_nombre or "Paciente"

    seccion_header = f"🦷 {clinic}\n\n"
    seccion_saludo = (
        f"¡Hola {paciente_nombre}! Gracias por reservar tu cita con nosotros.\n\n"
    )
    seccion_fecha = (
        f"📅 Fecha: {cita.fecha_hora.strftime('%d/%m/%Y')}\n"
        f"⏰ Hora: {cita.fecha_hora.strftime('%H:%M')}\n"
        f"🕒 Recomendación: Llega 10 minutos antes para facilitar la atención.\n\n"
    )
    seccion_ubicacion = (
        (f"📍 Dirección: {address}\n" if address else "") +
        (f"🗺️ Cómo llegar: {map_url}\n\n" if map_url else "")
    )
    seccion_contacto = (
        (f"💬 Contacto: {phone}\n" if phone else "") +
        (f"📧 Correo: {clinic_email}\n" if clinic_email else "") +
        (f"🌐 Sitio web: {clinic_web}\n\n" if clinic_web else "\n")
    )
    seccion_recordatorio = (
        "🔔 Recuerda:\n"
        "- Si deseas cambiar o cancelar tu cita, contáctanos con anticipación.\n"
        "- Mantén tu teléfono disponible para recordatorios.\n\n"
        "¡Esperamos verte y cuidar tu sonrisa! 😁"
    )

    body = seccion_header + seccion_saludo + seccion_fecha + seccion_ubicacion + seccion_contacto + seccion_recordatorio

    print(f"Enviando WhatsApp a whatsapp:{telefono} | body_simple=True")
    status_callback = getattr(settings, "TWILIO_STATUS_CALLBACK", None)
    message = client.messages.create(
        from_=whatsapp_from,
        to=f"whatsapp:{telefono}",
        body=body,
        status_callback=status_callback,
    )

    # Guardamos el SID en la cita
    cita.whatsapp_message_sid = message.sid
    cita.save(update_fields=["whatsapp_message_sid"])
    try:
        print(f"WhatsApp enviado SID={message.sid} status={getattr(message, 'status', 'unknown')} to={message.to}")
    except Exception:
        pass

    return message


def enviar_whatsapp_cancelacion(cita, telefono_override: str | None = None):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    telefono = telefono_override or cita.paciente_telefono
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        raise ValueError("No hay teléfono del paciente para enviar WhatsApp de cancelación")

    clinic = getattr(settings, "CLINIC_NAME", "Clínica")
    body = (
        f"{clinic}: tu cita del {cita.fecha_hora.strftime('%d/%m/%Y %H:%M')} ha sido cancelada. "
        f"Si fue un error, por favor reserva nuevamente desde el panel."
    )
    
    # Configuración del remitente (WhatsApp Business o sandbox)
    whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_BUSINESS_NUMBER", settings.TWILIO_FROM_WHATSAPP)
    if not whatsapp_from.startswith("whatsapp:"):
        whatsapp_from = f"whatsapp:{whatsapp_from}"
    
    print(f"Enviando WhatsApp CANCEL a whatsapp:{telefono} | body_simple=True")
    message = client.messages.create(
        from_=whatsapp_from,
        to=f"whatsapp:{telefono}",
        body=body,
        status_callback=getattr(settings, "TWILIO_STATUS_CALLBACK", None),
    )

    return message


def enviar_sms_confirmacion(cita, telefono_override: str | None = None):
    """Envía confirmación de cita por SMS."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # Normalizar número antes de enviar (Chile: +56)
    telefono = telefono_override or cita.paciente_telefono
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        raise ValueError("No hay teléfono del paciente para enviar SMS")

    # Construir enlaces simples de confirmación/cancelación
    base = getattr(settings, "SITE_URL", "")
    confirm_url = base + reverse('confirmar_cita', args=[cita.id])
    cancel_url = base + reverse('cancelar_cita_token', args=[cita.id])

    clinic = getattr(settings, "CLINIC_NAME", "Clínica")
    address = getattr(settings, "CLINIC_ADDRESS", "")
    phone = getattr(settings, "CLINIC_PHONE", "")
    map_url = getattr(settings, "CLINIC_MAP_URL", "")
    lat = getattr(settings, "CLINIC_LAT", "")
    lng = getattr(settings, "CLINIC_LNG", "")
    clinic_email = getattr(settings, "CLINIC_EMAIL", "")
    clinic_web = getattr(settings, "CLINIC_WEBSITE", "")
    
    # Configuración del remitente SMS
    from_sms = getattr(settings, "TWILIO_FROM_SMS", settings.TWILIO_PHONE_NUMBER)
    
    # Construir enlace de Google Maps si no viene uno directo
    if not map_url:
        if lat and lng:
            map_url = f"https://www.google.com/maps?q={lat},{lng}"
        elif address:
            from urllib.parse import quote
            map_url = f"https://www.google.com/maps/search/?api=1&query={quote(address)}"

    paciente_nombre = cita.paciente_nombre or "Paciente"

    # Mensaje SMS (sin emojis para mejor compatibilidad)
    seccion_header = f"{clinic}\n\n"
    seccion_saludo = (
        f"Hola {paciente_nombre}! Gracias por reservar tu cita con nosotros.\n\n"
    )
    seccion_fecha = (
        f"Fecha: {cita.fecha_hora.strftime('%d/%m/%Y')}\n"
        f"Hora: {cita.fecha_hora.strftime('%H:%M')}\n"
        f"Recomendacion: Llega 10 minutos antes.\n\n"
    )
    seccion_ubicacion = (
        (f"Direccion: {address}\n" if address else "") +
        (f"Mapa: {map_url}\n\n" if map_url else "")
    )
    seccion_contacto = (
        (f"Contacto: {phone}\n" if phone else "") +
        (f"Email: {clinic_email}\n" if clinic_email else "") +
        (f"Web: {clinic_web}\n\n" if clinic_web else "\n")
    )
    seccion_recordatorio = (
        "Recuerda:\n"
        "- Si deseas cambiar o cancelar tu cita, contactanos con anticipacion.\n"
        "- Manten tu telefono disponible para recordatorios.\n\n"
        "Esperamos verte y cuidar tu sonrisa!"
    )

    body = seccion_header + seccion_saludo + seccion_fecha + seccion_ubicacion + seccion_contacto + seccion_recordatorio

    print(f"Enviando SMS a {telefono}")
    status_callback = getattr(settings, "TWILIO_STATUS_CALLBACK", None)
    message = client.messages.create(
        from_=from_sms,
        to=telefono,  # SMS usa E.164 sin prefijo whatsapp
        body=body,
        status_callback=status_callback,
    )

    # Guardamos el SID en la cita (mantenemos el campo whatsapp_message_sid para compatibilidad)
    cita.whatsapp_message_sid = message.sid
    cita.save(update_fields=["whatsapp_message_sid"])
    try:
        print(f"SMS enviado SID={message.sid} status={getattr(message, 'status', 'unknown')} to={message.to}")
    except Exception:
        pass

    return message


def enviar_sms_cancelacion(cita, telefono_override: str | None = None):
    """Envía notificación de cancelación por SMS."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    telefono = telefono_override or cita.paciente_telefono
    telefono = _normalizar_telefono_chile(telefono)
    if not telefono:
        raise ValueError("No hay teléfono del paciente para enviar SMS de cancelación")

    clinic = getattr(settings, "CLINIC_NAME", "Clínica")
    body = (
        f"{clinic}: tu cita del {cita.fecha_hora.strftime('%d/%m/%Y %H:%M')} ha sido cancelada. "
        f"Si fue un error, por favor reserva nuevamente desde el panel."
    )
    
    # Configuración del remitente SMS
    from_sms = getattr(settings, "TWILIO_FROM_SMS", settings.TWILIO_PHONE_NUMBER)
    
    print(f"Enviando SMS CANCEL a {telefono}")
    message = client.messages.create(
        from_=from_sms,
        to=telefono,  # SMS usa E.164 sin prefijo whatsapp
        body=body,
        status_callback=getattr(settings, "TWILIO_STATUS_CALLBACK", None),
    )

    return message


def enviar_sms_fallback(cita, telefono_override: str | None = None):
    """Envío SMS simple con enlaces por si WhatsApp falla o no está permitido (DEPRECADO - usar enviar_sms_confirmacion)."""
    return enviar_sms_confirmacion(cita, telefono_override)


def consultar_estado_mensaje(message_sid: str) -> dict:
    """Consulta el estado de un mensaje en Twilio por su SID."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
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


def enviar_codigo_verificacion_whatsapp(telefono: str, codigo: str):
    """Envía código de verificación por WhatsApp."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # Normalizar número
    telefono_normalizado = _normalizar_telefono_chile(telefono)
    if not telefono_normalizado:
        raise ValueError("Número de teléfono inválido")
    
    # Formatear para WhatsApp
    whatsapp_to = f"whatsapp:{telefono_normalizado}"
    from_whatsapp = settings.TWILIO_WHATSAPP_NUMBER
    
    mensaje = f"""🔐 *Código de Verificación - Clínica Dental*

Tu código de verificación es: *{codigo}*

⏰ Este código expira en 15 minutos.

🛡️ No compartas este código con nadie.

¡Gracias por registrarte en nuestro sistema de reservas!"""
    
    try:
        msg = client.messages.create(
            from_=from_whatsapp,
            to=whatsapp_to,
            body=mensaje,
        )
        print(f"Código de verificación WhatsApp enviado SID={msg.sid} to={telefono_normalizado}")
        return msg
    except Exception as e:
        print("Error al enviar código de verificación por WhatsApp:", e)
        raise


def enviar_codigo_verificacion_sms(telefono: str, codigo: str):
    """Envía código de verificación por SMS como fallback."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # Normalizar número
    telefono_normalizado = _normalizar_telefono_chile(telefono)
    if not telefono_normalizado:
        raise ValueError("Número de teléfono inválido")
    
    from_sms = settings.TWILIO_PHONE_NUMBER
    
    mensaje = f"""Codigo de verificacion - Clinica Dental

Tu codigo es: {codigo}

Este codigo expira en 15 minutos.

No compartas este codigo con nadie.

Gracias por registrarte!"""
    
    try:
        msg = client.messages.create(
            from_=from_sms,
            to=telefono_normalizado,
            body=mensaje,
        )
        print(f"Código de verificación SMS enviado SID={msg.sid} to={telefono_normalizado}")
        return msg
    except Exception as e:
        print("Error al enviar código de verificación por SMS:", e)
        raise


def enviar_codigo_verificacion(telefono: str, codigo: str):
    """Envía código de verificación por SMS (usando el nuevo servicio de email/SMS)."""
    try:
        from .sms_service import enviar_codigo_verificacion as enviar_codigo_email
        return enviar_codigo_email(telefono, codigo)
    except ImportError:
        # Fallback al método anterior si el nuevo servicio no está disponible
        try:
            return enviar_codigo_verificacion_sms(telefono, codigo)
        except Exception as e:
            print("Error al enviar código de verificación por SMS:", e)
            raise Exception("No se pudo enviar el código de verificación por SMS")
    except Exception as e:
        print("Error al enviar código de verificación:", e)
        raise Exception("No se pudo enviar el código de verificación")
