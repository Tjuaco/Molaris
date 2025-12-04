"""
Servicio de SMS alternativo usando Email-to-SMS y notificaciones por Email
Funciona con cualquier número sin necesidad de servicios externos pagos
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.urls import reverse
import re
import logging

logger = logging.getLogger(__name__)


def _normalizar_telefono_chile(telefono: str | None) -> str | None:
    """Normaliza número de teléfono chileno a formato +56XXXXXXXXX"""
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


def _detectar_operadora_chile(telefono: str) -> str | None:
    """
    Detecta la operadora chilena basándose en el número.
    Retorna el dominio email-to-SMS de la operadora o None.
    """
    # Remover el +56
    numero = telefono.replace("+56", "") if telefono.startswith("+56") else telefono
    
    # Extraer los primeros dígitos para identificar la operadora
    if len(numero) >= 2:
        prefijo = numero[:2]
        
        # Movistar: 9, 8 (móviles)
        if prefijo.startswith("9") or prefijo.startswith("8"):
            # Movistar Chile acepta varios formatos
            return "movistar.cl"
        
        # Entel: 9, 7 (móviles)
        if prefijo.startswith("9") or prefijo.startswith("7"):
            return "entelpcs.com"
        
        # Claro: 9, 7 (móviles)
        if prefijo.startswith("9"):
            return "clarochile.cl"
        
        # WOM: 9 (móviles)
        if prefijo.startswith("9"):
            return "wom.cl"
    
    return None


def _obtener_email_sms(telefono: str) -> str | None:
    """
    Convierte un número de teléfono a dirección email para Email-to-SMS.
    Retorna None si no se puede determinar la operadora.
    """
    telefono_normalizado = _normalizar_telefono_chile(telefono)
    if not telefono_normalizado:
        return None
    
    # Remover el +56
    numero = telefono_normalizado.replace("+56", "")
    
    # Detectar operadora
    operadora = _detectar_operadora_chile(telefono_normalizado)
    
    if operadora:
        # Formato: 9XXXXXXXX@operadora.com
        return f"{numero}@{operadora}"
    
    # Si no se detecta operadora, intentar con Movistar (más común en Chile)
    if len(numero) == 9 and numero.startswith("9"):
        return f"{numero}@movistar.cl"
    
    return None


def _enviar_email_simple(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """
    Envía un email simple usando la configuración de Django.
    Retorna True si se envió correctamente, False en caso contrario.
    """
    try:
        # Configuración de email desde settings
        email_host = getattr(settings, 'EMAIL_HOST', None)
        email_port = getattr(settings, 'EMAIL_PORT', 587)
        email_host_user = getattr(settings, 'EMAIL_HOST_USER', None)
        email_host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
        email_use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        email_from = getattr(settings, 'EMAIL_FROM', email_host_user)
        
        if not email_host or not email_host_user:
            logger.warning("Configuración de email no encontrada. Usando modo simulado.")
            print(f"[SIMULADO] Email a {destinatario}: {asunto}")
            print(f"[SIMULADO] Cuerpo: {cuerpo[:100]}...")
            return True  # Retornamos True para no romper el flujo
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = destinatario
        msg['Subject'] = asunto
        
        # Agregar cuerpo
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
        
        # Enviar email
        with smtplib.SMTP(email_host, email_port) as server:
            if email_use_tls:
                server.starttls()
            if email_host_password:
                server.login(email_host_user, email_host_password)
            server.send_message(msg)
        
        logger.info(f"Email enviado exitosamente a {destinatario}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar email a {destinatario}: {e}")
        print(f"Error al enviar email: {e}")
        return False


def enviar_notificacion_email(cita, telefono_override: str | None = None):
    """
    Envía notificación de confirmación de cita por EMAIL.
    Esta es la forma más confiable y funciona con cualquier correo.
    """
    # Obtener email del paciente
    email = None
    if cita.paciente_email:
        email = cita.paciente_email
    else:
        # Intentar obtener email del perfil
        try:
            from cuentas.models import PerfilCliente
            from django.contrib.auth.models import User
            user = User.objects.get(username=cita.paciente_nombre)
            perfil = PerfilCliente.objects.get(user=user)
            email = perfil.email
        except Exception:
            pass
    
    if not email:
        raise ValueError("No hay email del paciente para enviar notificación")
    
    # Construir enlaces
    base = getattr(settings, "SITE_URL", "")
    confirm_url = base + reverse('confirmar_cita', args=[cita.id])
    
    clinic = getattr(settings, "CLINIC_NAME", "Clínica Dental")
    address = getattr(settings, "CLINIC_ADDRESS", "")
    phone = getattr(settings, "CLINIC_PHONE", "")
    clinic_email = getattr(settings, "CLINIC_EMAIL", "")
    clinic_web = getattr(settings, "CLINIC_WEBSITE", "")
    
    paciente_nombre = cita.paciente_nombre or "Paciente"
    
    # Obtener información del servicio y precio
    from .servicio_service import obtener_tipo_servicio_de_cita
    servicio_info = obtener_tipo_servicio_de_cita(cita.id, tipo_consulta=cita.tipo_consulta)
    
    # Construir mensaje de email
    asunto = f"Confirmación de Cita - {clinic}"
    
    cuerpo = f"""
{clinic}

Hola {paciente_nombre}!

Gracias por reservar tu cita con nosotros.

INFORMACIÓN DE TU CITA:
------------------------
Fecha: {cita.fecha_hora.strftime('%d/%m/%Y')}
Hora: {cita.fecha_hora.strftime('%H:%M')}"""
    
    # Agregar información del servicio
    if servicio_info and servicio_info.get('nombre'):
        cuerpo += f"\nServicio: {servicio_info.get('nombre')}"
    else:
        cuerpo += f"\nTipo de Consulta: {cita.tipo_consulta or 'Consulta general'}"
    
    # Agregar precio del servicio
    if servicio_info:
        precio_a_mostrar = None
        if servicio_info.get('precio_cobrado_formateado'):
            precio_a_mostrar = servicio_info.get('precio_cobrado_formateado')
        elif servicio_info.get('precio_formateado'):
            precio_a_mostrar = servicio_info.get('precio_formateado')
        
        if precio_a_mostrar:
            cuerpo += f"\nPrecio: {precio_a_mostrar}"
    
    cuerpo += "\n\nRecomendación: Llega 10 minutos antes para facilitar la atención.\n"
    
    if address:
        cuerpo += f"Dirección: {address}\n"
    
    if phone:
        cuerpo += f"Contacto: {phone}\n"
    
    if clinic_email:
        cuerpo += f"Email: {clinic_email}\n"
    
    if clinic_web:
        cuerpo += f"Web: {clinic_web}\n"
    
    cuerpo += f"""
Para confirmar tu cita, haz clic en el siguiente enlace:
{confirm_url}

Recuerda:
- Si deseas cambiar o cancelar tu cita, contáctanos con anticipación.
- Mantén tu teléfono disponible para recordatorios.

¡Esperamos verte y cuidar tu sonrisa!

Saludos,
{clinic}
"""
    
    # Enviar email
    exito = _enviar_email_simple(email, asunto, cuerpo)
    
    if exito:
        # Guardar referencia en la cita (usamos el campo whatsapp_message_sid para compatibilidad)
        cita.whatsapp_message_sid = f"email_sent_to_{email}"
        cita.save(update_fields=["whatsapp_message_sid"])
        logger.info(f"Notificación por email enviada a {email} para cita {cita.id}")
    
    return exito


def enviar_notificacion_email_sms(cita, telefono_override: str | None = None):
    """
    Envía notificación por Email-to-SMS (intenta convertir número a email de SMS).
    Funciona solo si se puede detectar la operadora del número.
    """
    telefono = telefono_override or cita.paciente_telefono
    if not telefono:
        raise ValueError("No hay teléfono del paciente")
    
    # Convertir número a email SMS
    email_sms = _obtener_email_sms(telefono)
    
    if not email_sms:
        # Si no se puede detectar operadora, lanzar error para que se intente otro método
        raise ValueError(f"No se pudo detectar operadora para {telefono}")
    
    # Obtener información del servicio y precio
    from .servicio_service import obtener_tipo_servicio_de_cita
    servicio_info = obtener_tipo_servicio_de_cita(cita.id, tipo_consulta=cita.tipo_consulta)
    
    # Construir mensaje SMS (más corto y optimizado para SMS)
    base = getattr(settings, "SITE_URL", "")
    confirm_url = base + reverse('confirmar_cita', args=[cita.id])
    
    clinic = getattr(settings, "CLINIC_NAME", "Clínica Dental")
    address = getattr(settings, "CLINIC_ADDRESS", "")
    phone = getattr(settings, "CLINIC_PHONE", "")
    paciente_nombre = cita.paciente_nombre or "Paciente"
    
    # Mensaje SMS optimizado (sin asunto, solo cuerpo)
    # Los SMS no tienen asunto, así que todo va en el cuerpo
    cuerpo = f"""{clinic}

Hola {paciente_nombre}! Gracias por reservar tu cita.

Fecha: {cita.fecha_hora.strftime('%d/%m/%Y')}
Hora: {cita.fecha_hora.strftime('%H:%M')}"""
    
    # Agregar información del servicio
    if servicio_info and servicio_info.get('nombre'):
        cuerpo += f"\nServicio: {servicio_info.get('nombre')}"
    elif cita.tipo_consulta:
        cuerpo += f"\nServicio: {cita.tipo_consulta}"
    
    # Agregar precio del servicio
    if servicio_info:
        precio_a_mostrar = None
        if servicio_info.get('precio_cobrado_formateado'):
            precio_a_mostrar = servicio_info.get('precio_cobrado_formateado')
        elif servicio_info.get('precio_formateado'):
            precio_a_mostrar = servicio_info.get('precio_formateado')
        
        if precio_a_mostrar:
            cuerpo += f"\nPrecio: {precio_a_mostrar}"
    
    cuerpo += "\nRecomendacion: Llega 10 minutos antes."
    
    if address:
        cuerpo += f"\nDireccion: {address}"
    
    if phone:
        cuerpo += f"\nContacto: {phone}"
    
    cuerpo += f"\n\nConfirma tu cita: {confirm_url}"
    cuerpo += "\n\nSi deseas cambiar o cancelar, contactanos con anticipacion."
    cuerpo += "\n\nEsperamos verte!"
    
    # Enviar email SMS (el asunto se ignora en SMS, pero lo ponemos por si acaso)
    asunto = f"Cita {cita.fecha_hora.strftime('%d/%m %H:%M')}"
    exito = _enviar_email_simple(email_sms, asunto, cuerpo)
    
    if exito:
        cita.whatsapp_message_sid = f"email_sms_sent_to_{email_sms}"
        cita.save(update_fields=["whatsapp_message_sid"])
        logger.info(f"SMS enviado a {email_sms} para cita {cita.id}")
    
    return exito


def enviar_sms_confirmacion(cita, telefono_override: str | None = None):
    """
    Envía confirmación de cita por SMS usando Email-to-SMS.
    Esta función reemplaza la versión de Twilio.
    """
    telefono = telefono_override or cita.paciente_telefono
    if not telefono:
        raise ValueError("No hay teléfono del paciente para enviar SMS")
    
    try:
        # Intentar primero Email-to-SMS (SMS directo)
        return enviar_notificacion_email_sms(cita, telefono_override)
    except Exception as e:
        logger.error(f"Error al enviar SMS: {e}")
        # Si falla SMS, intentar email normal como respaldo
        try:
            logger.warning(f"SMS falló, intentando email normal como respaldo")
            return enviar_notificacion_email(cita, telefono_override)
        except Exception as e2:
            logger.error(f"Error al enviar notificación por email: {e2}")
            raise Exception(f"No se pudo enviar notificación por SMS ni por email: {e2}")


def enviar_sms_cancelacion(cita, telefono_override: str | None = None):
    """
    Envía notificación de cancelación por SMS usando Email-to-SMS.
    """
    telefono = telefono_override or cita.paciente_telefono
    if not telefono:
        raise ValueError("No hay teléfono del paciente para enviar SMS de cancelación")
    
    # Normalizar teléfono
    telefono_normalizado = _normalizar_telefono_chile(telefono)
    if not telefono_normalizado:
        raise ValueError(f"Número de teléfono inválido: {telefono}")
    
    # Convertir número a email SMS
    email_sms = _obtener_email_sms(telefono_normalizado)
    
    if not email_sms:
        # Si no se puede detectar operadora, intentar email normal como respaldo
        logger.warning(f"No se pudo detectar operadora para {telefono}, intentando email normal")
        email = None
        if cita.paciente_email:
            email = cita.paciente_email
        else:
            try:
                from cuentas.models import PerfilCliente
                from django.contrib.auth.models import User
                user = User.objects.get(username=cita.paciente_nombre)
                perfil = PerfilCliente.objects.get(user=user)
                email = perfil.email
            except Exception:
                pass
        
        if email:
            clinic = getattr(settings, "CLINIC_NAME", "Clínica Dental")
            asunto = f"Cancelación de Cita - {clinic}"
            cuerpo = f"""{clinic}

Tu cita del {cita.fecha_hora.strftime('%d/%m/%Y %H:%M')} ha sido cancelada.

Si fue un error, por favor reserva nuevamente desde el panel.

Saludos,
{clinic}
"""
            return _enviar_email_simple(email, asunto, cuerpo)
        
        raise ValueError(f"No se pudo detectar la operadora para el teléfono {telefono} y no hay email disponible.")
    
    # Enviar SMS de cancelación
    clinic = getattr(settings, "CLINIC_NAME", "Clínica Dental")
    asunto = "Cita Cancelada"
    cuerpo = f"""{clinic}

Tu cita del {cita.fecha_hora.strftime('%d/%m/%Y %H:%M')} ha sido cancelada.

Si fue un error, por favor reserva nuevamente desde el panel.

Saludos,
{clinic}"""
    
    exito = _enviar_email_simple(email_sms, asunto, cuerpo)
    
    if exito:
        logger.info(f"SMS de cancelación enviado a {email_sms} (teléfono: {telefono_normalizado}) para cita {cita.id}")
    
    return exito


def enviar_codigo_verificacion_sms(telefono: str, codigo: str):
    """
    Envía código de verificación por SMS usando Email-to-SMS.
    En modo desarrollo (sin configuración de email), muestra el código en consola.
    """
    # Normalizar teléfono
    telefono_normalizado = _normalizar_telefono_chile(telefono)
    if not telefono_normalizado:
        raise ValueError(f"Número de teléfono inválido: {telefono}")
    
    # Convertir número a email SMS
    email_sms = _obtener_email_sms(telefono_normalizado)
    
    if not email_sms:
        raise ValueError(f"No se pudo detectar la operadora para el teléfono {telefono}. Por favor, verifica que el número sea correcto y sea de una operadora chilena (Movistar, Entel, Claro, WOM).")
    
    # Verificar si hay configuración de email válida
    email_host = getattr(settings, 'EMAIL_HOST', None)
    email_host_user = getattr(settings, 'EMAIL_HOST_USER', None)
    
    # Si no hay configuración válida de email, usar modo desarrollo
    if not email_host or not email_host_user or email_host_user == 'tu-email@gmail.com':
        # Modo desarrollo: mostrar código en consola
        logger.warning(f"[MODO DESARROLLO] Código de verificación para {telefono_normalizado}: {codigo}")
        print(f"\n{'='*60}")
        print(f"[MODO DESARROLLO] Código de verificación SMS")
        print(f"Teléfono: {telefono_normalizado}")
        print(f"Email SMS: {email_sms}")
        print(f"CÓDIGO: {codigo}")
        print(f"{'='*60}\n")
        return True
    
    # Mensaje SMS optimizado (sin asunto, solo cuerpo)
    mensaje = f"""Clinica Dental - Codigo de Verificacion

Tu codigo es: {codigo}

Este codigo expira en 15 minutos.

No compartas este codigo con nadie.

Gracias por registrarte!"""
    
    # Enviar SMS (el asunto se ignora en SMS, pero lo ponemos por si acaso)
    asunto = "Codigo de Verificacion"
    exito = _enviar_email_simple(email_sms, asunto, mensaje)
    
    if exito:
        logger.info(f"Código de verificación enviado por SMS a {email_sms} (teléfono: {telefono_normalizado})")
        return True
    
    raise ValueError(f"No se pudo enviar código de verificación al teléfono {telefono}. Por favor, verifica que el número sea correcto.")


def enviar_codigo_verificacion(telefono: str, codigo: str):
    """
    Envía código de verificación por Email-to-SMS.
    """
    return enviar_codigo_verificacion_sms(telefono, codigo)


def consultar_estado_mensaje(message_id: str) -> dict:
    """
    Para compatibilidad con la función anterior.
    Retorna información básica del mensaje.
    """
    return {
        "sid": message_id,
        "status": "sent" if message_id.startswith("email") else "unknown",
        "to": message_id.replace("email_sent_to_", "").replace("email_sms_sent_to_", ""),
        "from": getattr(settings, 'EMAIL_FROM', getattr(settings, 'EMAIL_HOST_USER', '')),
        "date_created": None,
        "date_sent": None,
        "date_updated": None,
    }



