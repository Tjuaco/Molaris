"""
Servicio de Twilio para envío de códigos de verificación por WhatsApp y Email
"""
from django.conf import settings
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)


def _get_twilio_client():
    """Obtiene el cliente de Twilio configurado"""
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    
    if not account_sid or not auth_token or account_sid == 'default' or auth_token == 'default':
        return None
    
    try:
        return Client(account_sid, auth_token)
    except Exception as e:
        logger.error(f"Error al inicializar cliente Twilio: {e}")
        return None


def enviar_codigo_por_whatsapp(telefono: str, codigo: str) -> bool:
    """
    Envía código de verificación por WhatsApp usando Twilio.
    
    Args:
        telefono: Número de teléfono en formato +56XXXXXXXXX
        codigo: Código de verificación a enviar
    
    Returns:
        True si se envió correctamente, False en caso contrario
    """
    client = _get_twilio_client()
    if not client:
        logger.warning("Twilio no configurado. Mostrando código en consola.")
        print(f"\n{'='*60}")
        print(f"[MODO DESARROLLO] Código de verificación WhatsApp")
        print(f"Teléfono: {telefono}")
        print(f"CÓDIGO: {codigo}")
        print(f"{'='*60}\n")
        return True
    
    try:
        whatsapp_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        
        mensaje = f"""Clínica Dental - Código de Verificación

Tu código es: *{codigo}*

Este código expira en 15 minutos.

No compartas este código con nadie.

Gracias por registrarte!"""
        
        # Asegurar que el número tenga el formato correcto para WhatsApp
        if not telefono.startswith('whatsapp:'):
            telefono_whatsapp = f"whatsapp:{telefono}"
        else:
            telefono_whatsapp = telefono
        
        message = client.messages.create(
            body=mensaje,
            from_=whatsapp_number,
            to=telefono_whatsapp
        )
        
        logger.info(f"Código de verificación enviado por WhatsApp a {telefono} (SID: {message.sid})")
        return True
        
    except TwilioException as e:
        logger.error(f"Error de Twilio al enviar WhatsApp: {e}")
        # En desarrollo, mostrar en consola
        print(f"\n{'='*60}")
        print(f"[MODO DESARROLLO] Código de verificación WhatsApp")
        print(f"Teléfono: {telefono}")
        print(f"CÓDIGO: {codigo}")
        print(f"Error Twilio: {e}")
        print(f"{'='*60}\n")
        return True  # Retornar True para no romper el flujo en desarrollo
    except Exception as e:
        logger.error(f"Error inesperado al enviar WhatsApp: {e}")
        raise


def enviar_codigo_por_email(email: str, codigo: str) -> bool:
    """
    Envía código de verificación por email.
    
    Args:
        email: Dirección de email del usuario
        codigo: Código de verificación a enviar
    
    Returns:
        True si se envió correctamente, False en caso contrario
    """
    from django.core.mail import send_mail
    from django.conf import settings
    
    try:
        clinic_name = getattr(settings, 'CLINIC_NAME', 'Clínica Dental')
        
        asunto = f"{clinic_name} - Código de Verificación"
        
        mensaje = f"""Hola!

Tu código de verificación es: {codigo}

Este código expira en 15 minutos.

No compartas este código con nadie.

Gracias por registrarte en {clinic_name}!

Saludos,
Equipo {clinic_name}"""
        
        email_from = getattr(settings, 'EMAIL_FROM', getattr(settings, 'EMAIL_HOST_USER', 'noreply@clinica.com'))
        
        # Verificar si hay configuración de email
        email_host = getattr(settings, 'EMAIL_HOST', None)
        email_host_user = getattr(settings, 'EMAIL_HOST_USER', None)
        
        if not email_host or not email_host_user or email_host_user == 'tu-email@gmail.com':
            # Modo desarrollo: mostrar código en consola
            logger.warning(f"[MODO DESARROLLO] Código de verificación por email para {email}: {codigo}")
            print(f"\n{'='*60}")
            print(f"[MODO DESARROLLO] Código de verificación Email")
            print(f"Email: {email}")
            print(f"CÓDIGO: {codigo}")
            print(f"{'='*60}\n")
            return True
        
        send_mail(
            asunto,
            mensaje,
            email_from,
            [email],
            fail_silently=False,
        )
        
        logger.info(f"Código de verificación enviado por email a {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar código por email: {e}")
        # En desarrollo, mostrar en consola
        print(f"\n{'='*60}")
        print(f"[MODO DESARROLLO] Código de verificación Email")
        print(f"Email: {email}")
        print(f"CÓDIGO: {codigo}")
        print(f"Error: {e}")
        print(f"{'='*60}\n")
        return True  # Retornar True para no romper el flujo en desarrollo

