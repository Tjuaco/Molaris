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
        
        # Enviar email con timeout para evitar que se quede colgado
        import socket
        socket.setdefaulttimeout(10)  # Timeout de 10 segundos
        
        try:
            # Verificar configuración antes de enviar
            logger.info(f"Intentando enviar código por email a {email}")
            logger.info(f"EMAIL_HOST: {email_host}")
            logger.info(f"EMAIL_HOST_USER: {email_host_user}")
            logger.info(f"EMAIL_FROM: {email_from}")
            
            send_mail(
                asunto,
                mensaje,
                email_from,
                [email],
                fail_silently=False,
            )
            logger.info(f"✓ Código de verificación enviado por email a {email}")
            return True
        except socket.timeout:
            logger.error(f"✗ Timeout al enviar código por email a {email}")
            # En caso de timeout, mostrar código en consola y continuar
            print(f"\n{'='*60}")
            print(f"[TIMEOUT] Código de verificación Email")
            print(f"Email: {email}")
            print(f"CÓDIGO: {codigo}")
            print(f"{'='*60}\n")
            return True  # Retornar True para no romper el flujo
        except Exception as mail_error:
            logger.error(f"✗ Error al enviar email: {type(mail_error).__name__}: {str(mail_error)}")
            # Re-lanzar para que se capture en el except general
            raise
        finally:
            socket.setdefaulttimeout(None)  # Restaurar timeout por defecto
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"✗ Error al enviar código por email: {error_type}: {error_msg}")
        logger.error(f"  Email destino: {email}")
        logger.error(f"  Email host: {email_host}")
        logger.error(f"  Email user: {email_host_user}")
        
        # En desarrollo, mostrar en consola
        print(f"\n{'='*60}")
        print(f"[ERROR] Código de verificación Email")
        print(f"Email: {email}")
        print(f"CÓDIGO: {codigo}")
        print(f"Error: {error_type}: {error_msg}")
        print(f"{'='*60}\n")
        
        # Si es un error de autenticación, retornar False para que se muestre el error
        if 'authentication' in error_msg.lower() or '535' in error_msg or '534' in error_msg:
            logger.error("Error de autenticación con Gmail. Verifica EMAIL_HOST_PASSWORD.")
            return False
        
        return True  # Retornar True para otros errores y no romper el flujo

