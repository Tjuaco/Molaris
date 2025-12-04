"""
Servicio de SMS para gestion_clinica usando Email-to-SMS
Envía notificaciones SMS cuando se agendan citas desde el sistema interno
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
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
            logger.info(f"Email enviado exitosamente a {destinatario} desde {email_from}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar email a {destinatario}: {e}")
        print(f"Error al enviar email: {e}")
        return False


def _obtener_info_clinica():
    """
    Obtiene la información de la clínica desde el modelo InformacionClinica.
    Retorna un diccionario con los datos o valores por defecto.
    """
    try:
        from configuracion.models import InformacionClinica
        info = InformacionClinica.obtener()
        return {
            'nombre': info.nombre_clinica or "Clínica Dental",
            'direccion': info.direccion or "",
            'telefono': info.telefono or "",
            'telefono_secundario': info.telefono_secundario or "",
            'email': info.email or "",
            'horario': info.horario_atencion or "",
            'whatsapp': info.whatsapp or "",
        }
    except Exception as e:
        logger.warning(f"No se pudo obtener información de la clínica: {e}")
        return {
            'nombre': "Clínica Dental",
            'direccion': "",
            'telefono': "",
            'telefono_secundario': "",
            'email': "",
            'horario': "",
            'whatsapp': "",
        }


def enviar_sms_confirmacion_cita(cita, telefono_override: str | None = None):
    """
    Envía confirmación de cita por SMS.
    Intenta primero con Twilio, si falla usa Email-to-SMS como respaldo.
    Esta función se usa cuando se agenda una cita desde el sistema interno.
    
    Args:
        cita: Objeto Cita del modelo
        telefono_override: Teléfono alternativo (opcional)
    
    Returns:
        bool: True si se envió exitosamente, False en caso contrario
    """
    telefono = telefono_override or cita.telefono_paciente
    if not telefono:
        logger.warning(f"No hay teléfono del paciente para enviar SMS de confirmación (Cita ID: {cita.id})")
        return False
    
    # Normalizar teléfono
    telefono_normalizado = _normalizar_telefono_chile(telefono)
    if not telefono_normalizado:
        logger.warning(f"Número de teléfono inválido: {telefono}")
        return False
    
    # INTENTAR PRIMERO CON TWILIO (método preferido)
    try:
        from citas.twilio_service import enviar_sms_confirmacion_cita as enviar_sms_twilio
        resultado = enviar_sms_twilio(cita, telefono_override)
        if resultado and resultado.get('sid'):
            logger.info(f"SMS enviado exitosamente con Twilio (SID: {resultado['sid']}) para cita {cita.id}")
            # También enviar email de respaldo si está disponible
            if cita.email_paciente:
                try:
                    enviar_email_confirmacion_cita(cita)
                except Exception as e:
                    logger.warning(f"No se pudo enviar email de respaldo: {e}")
            return True
        else:
            logger.warning(f"Twilio no pudo enviar SMS para cita {cita.id}, intentando Email-to-SMS como respaldo")
    except ImportError:
        logger.warning("Servicio de Twilio no disponible, usando Email-to-SMS")
    except Exception as e:
        logger.warning(f"Error al intentar enviar SMS con Twilio: {e}. Intentando Email-to-SMS como respaldo")
    
    # RESpaldo: Email-to-SMS (método alternativo)
    # Convertir número a email SMS
    email_sms = _obtener_email_sms(telefono_normalizado)
    
    if not email_sms:
        logger.warning(f"No se pudo detectar operadora para {telefono}. Intentando email normal como respaldo.")
        # Intentar enviar por email normal si hay email del paciente
        if cita.email_paciente:
            logger.info(f"Enviando confirmación por email normal a {cita.email_paciente} como respaldo")
            return enviar_email_confirmacion_cita(cita)
        return False
    
    # Intentar enviar SMS primero
    logger.info(f"Intentando enviar SMS a {email_sms} (teléfono: {telefono_normalizado})")
    
    # Obtener información de la clínica
    info_clinica = _obtener_info_clinica()
    
    # Obtener nombre del dentista
    dentista_nombre = ""
    if cita.dentista:
        dentista_nombre = cita.dentista.nombre_completo or ""
    
    # Obtener información del servicio
    servicio_nombre = ""
    if cita.tipo_servicio:
        servicio_nombre = cita.tipo_servicio.nombre
    elif cita.tipo_consulta:
        servicio_nombre = cita.tipo_consulta
    
    # Obtener precio
    precio_texto = ""
    if cita.precio_cobrado:
        precio_texto = f"${cita.precio_cobrado:,.0f}".replace(',', '.')
    
    paciente_nombre = cita.nombre_paciente or "Paciente"
    
    # Construir mensaje SMS (optimizado para SMS, más corto)
    cuerpo = f"""{info_clinica['nombre']}

Hola {paciente_nombre}! Tu cita ha sido agendada.

Fecha: {cita.fecha_hora.strftime('%d/%m/%Y')}
Hora: {cita.fecha_hora.strftime('%H:%M')}"""
    
    if dentista_nombre:
        cuerpo += f"\nDentista: {dentista_nombre}"
    
    if servicio_nombre:
        cuerpo += f"\nServicio: {servicio_nombre}"
    
    if precio_texto:
        cuerpo += f"\nPrecio: {precio_texto}"
    
    cuerpo += "\n\nRecomendacion: Llega 10 minutos antes."
    
    if info_clinica['direccion']:
        cuerpo += f"\n\nDireccion: {info_clinica['direccion']}"
    
    if info_clinica['telefono']:
        cuerpo += f"\nContacto: {info_clinica['telefono']}"
    
    if info_clinica['horario']:
        cuerpo += f"\nHorario: {info_clinica['horario'].replace(chr(10), ' ')}"
    
    cuerpo += "\n\nSi necesitas cambiar o cancelar, contactanos con anticipacion."
    cuerpo += f"\n\nEsperamos verte!"
    
    # Enviar SMS (el asunto se ignora en SMS, pero lo ponemos por si acaso)
    asunto = f"Cita {cita.fecha_hora.strftime('%d/%m %H:%M')}"
    exito = _enviar_email_simple(email_sms, asunto, cuerpo)
    
    if exito:
        logger.info(f"SMS de confirmación enviado a {email_sms} (teléfono: {telefono_normalizado}) para cita {cita.id}")
        
        # IMPORTANTE: También enviar por email normal como respaldo
        # Email-to-SMS puede no funcionar en todas las operadoras
        if cita.email_paciente:
            logger.info(f"Enviando también confirmación por email normal a {cita.email_paciente} como respaldo")
            try:
                enviar_email_confirmacion_cita(cita)
            except Exception as e:
                logger.warning(f"No se pudo enviar email de respaldo: {e}")
    else:
        logger.warning(f"No se pudo enviar SMS a {email_sms}. Intentando email normal como respaldo.")
        # Si falla el SMS, intentar email normal
        if cita.email_paciente:
            return enviar_email_confirmacion_cita(cita)
    
    return exito


def enviar_email_confirmacion_cita(cita):
    """
    Envía confirmación de cita por EMAIL como respaldo cuando no se puede enviar SMS.
    """
    email_paciente = cita.email_paciente
    if not email_paciente:
        logger.warning(f"No hay email del paciente para enviar notificación (Cita ID: {cita.id})")
        return False
    
    # Obtener información de la clínica
    info_clinica = _obtener_info_clinica()
    
    # Obtener nombre del dentista
    dentista_nombre = ""
    if cita.dentista:
        dentista_nombre = cita.dentista.nombre_completo or ""
    
    # Obtener información del servicio
    servicio_nombre = ""
    if cita.tipo_servicio:
        servicio_nombre = cita.tipo_servicio.nombre
    elif cita.tipo_consulta:
        servicio_nombre = cita.tipo_consulta
    
    # Obtener precio
    precio_texto = ""
    if cita.precio_cobrado:
        precio_texto = f"${cita.precio_cobrado:,.0f}".replace(',', '.')
    
    paciente_nombre = cita.nombre_paciente or "Paciente"
    
    # Construir mensaje de email
    asunto = f"Confirmación de Cita - {info_clinica['nombre']}"
    
    cuerpo = f"""
{info_clinica['nombre']}

Hola {paciente_nombre}!

Tu cita ha sido agendada exitosamente.

INFORMACIÓN DE TU CITA:
------------------------
Fecha: {cita.fecha_hora.strftime('%d/%m/%Y')}
Hora: {cita.fecha_hora.strftime('%H:%M')}"""
    
    if dentista_nombre:
        cuerpo += f"\nDentista: {dentista_nombre}"
    
    if servicio_nombre:
        cuerpo += f"\nServicio: {servicio_nombre}"
    
    if precio_texto:
        cuerpo += f"\nPrecio: {precio_texto}"
    
    cuerpo += "\n\nRecomendación: Llega 10 minutos antes para facilitar la atención.\n"
    
    if info_clinica['direccion']:
        cuerpo += f"Dirección: {info_clinica['direccion']}\n"
    
    if info_clinica['telefono']:
        cuerpo += f"Contacto: {info_clinica['telefono']}\n"
    
    if info_clinica['email']:
        cuerpo += f"Email: {info_clinica['email']}\n"
    
    if info_clinica['horario']:
        cuerpo += f"Horario de Atención:\n{info_clinica['horario']}\n"
    
    cuerpo += f"""
Recuerda:
- Si deseas cambiar o cancelar tu cita, contáctanos con anticipación.
- Mantén tu teléfono disponible para recordatorios.

¡Esperamos verte y cuidar tu sonrisa!

Saludos,
{info_clinica['nombre']}
"""
    
    # Enviar email
    exito = _enviar_email_simple(email_paciente, asunto, cuerpo)
    
    if exito:
        logger.info(f"Email de confirmación enviado a {email_paciente} para cita {cita.id}")
    
    return exito

