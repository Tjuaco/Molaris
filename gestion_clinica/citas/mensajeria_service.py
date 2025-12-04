"""
Servicio unificado de mensajería para gestion_clinica
Envía notificaciones por WhatsApp Y SMS cuando se agendan citas
"""
import logging

logger = logging.getLogger(__name__)


def enviar_notificaciones_cita(cita, telefono_override: str | None = None):
    """
    Envía notificaciones de confirmación de cita por WhatsApp, SMS Y correo electrónico.
    Intenta todos los canales para maximizar las posibilidades de que el paciente reciba la información.
    
    Args:
        cita: Objeto Cita del modelo
        telefono_override: Teléfono alternativo (opcional)
    
    Returns:
        dict: Resultado del envío con estado de cada canal
        {
            'whatsapp': {'enviado': bool, 'error': str|None},
            'sms': {'enviado': bool, 'error': str|None},
            'email': {'enviado': bool, 'error': str|None}
        }
    """
    resultado = {
        'whatsapp': {'enviado': False, 'error': None},
        'sms': {'enviado': False, 'error': None},
        'email': {'enviado': False, 'error': None}
    }
    
    # Obtener teléfono de forma segura
    telefono = telefono_override
    if not telefono:
        # Intentar usar la propiedad telefono_paciente si existe
        try:
            telefono = getattr(cita, 'telefono_paciente', None)
        except (AttributeError, TypeError):
            telefono = None
        
        # Si no funciona, usar el campo paciente_telefono directamente
        if not telefono:
            telefono = getattr(cita, 'paciente_telefono', None)
        
        # Si aún no hay teléfono, intentar desde el cliente
        if not telefono and cita.cliente:
            telefono = getattr(cita.cliente, 'telefono', None)
    
    logger.info(f"[DEBUG] Telefono para notificaciones - override: {telefono_override}, telefono final: {telefono}")
    if not telefono:
        logger.warning(f"No hay teléfono del paciente para enviar notificaciones (Cita ID: {cita.id})")
        resultado['whatsapp']['error'] = "No hay teléfono del paciente"
        resultado['sms']['error'] = "No hay teléfono del paciente"
        return resultado
    
    # INTENTAR ENVIAR POR WHATSAPP
    logger.info(f"[DEBUG] Intentando enviar WhatsApp para cita {cita.id}. Teléfono: {telefono}, telefono_override: {telefono_override}")
    try:
        from citas.twilio_service import enviar_whatsapp_confirmacion_cita
        logger.info(f"[DEBUG] Función enviar_whatsapp_confirmacion_cita importada correctamente")
        whatsapp_result = enviar_whatsapp_confirmacion_cita(cita, telefono_override)
        logger.info(f"[DEBUG] Resultado de enviar_whatsapp_confirmacion_cita: {whatsapp_result}")
        if whatsapp_result and whatsapp_result.get('sid'):
            resultado['whatsapp']['enviado'] = True
            logger.info(f"WhatsApp de confirmación enviado exitosamente para cita {cita.id} (SID: {whatsapp_result['sid']})")
        else:
            resultado['whatsapp']['error'] = f"No se pudo enviar WhatsApp. Resultado: {whatsapp_result}"
            logger.warning(f"No se pudo enviar WhatsApp para cita {cita.id}. Resultado recibido: {whatsapp_result}")
            if whatsapp_result:
                logger.warning(f"Detalles del resultado: {whatsapp_result}")
    except ImportError as e:
        resultado['whatsapp']['error'] = "Servicio de WhatsApp no disponible"
        logger.warning(f"Servicio de WhatsApp no disponible: {e}")
        import traceback
        logger.error(traceback.format_exc())
    except Exception as e:
        resultado['whatsapp']['error'] = str(e)
        logger.error(f"Error al enviar WhatsApp para cita {cita.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # INTENTAR ENVIAR POR SMS
    try:
        from citas.twilio_service import enviar_sms_confirmacion_cita as enviar_sms_twilio
        sms_result = enviar_sms_twilio(cita, telefono_override)
        if sms_result and sms_result.get('sid'):
            resultado['sms']['enviado'] = True
            logger.info(f"SMS de confirmación enviado exitosamente para cita {cita.id} (SID: {sms_result['sid']})")
            # Verificar si hay errores en el resultado
            if sms_result.get('error_code'):
                resultado['sms']['error'] = f"Error {sms_result.get('error_code')}: {sms_result.get('error_message', 'N/A')}"
                logger.warning(f"SMS enviado pero con error: {resultado['sms']['error']}")
        else:
            resultado['sms']['error'] = "No se pudo enviar SMS (no se obtuvo SID)"
            logger.warning(f"No se pudo enviar SMS para cita {cita.id}: {resultado['sms']['error']}")
            # Intentar con el servicio de respaldo
            try:
                from citas.sms_service import enviar_sms_confirmacion_cita as enviar_sms_respaldo
                sms_respaldo = enviar_sms_respaldo(cita, telefono_override)
                if sms_respaldo:
                    resultado['sms']['enviado'] = True
                    resultado['sms']['error'] = None
                    logger.info(f"SMS enviado exitosamente usando método de respaldo para cita {cita.id}")
            except Exception as e2:
                logger.warning(f"También falló el método de respaldo: {e2}")
    except ImportError:
        # Si no está disponible twilio_service, usar el servicio de respaldo
        try:
            from citas.sms_service import enviar_sms_confirmacion_cita
            sms_result = enviar_sms_confirmacion_cita(cita, telefono_override)
            if sms_result:
                resultado['sms']['enviado'] = True
                logger.info(f"SMS de confirmación enviado exitosamente usando método de respaldo para cita {cita.id}")
            else:
                resultado['sms']['error'] = "No se pudo enviar SMS"
                logger.warning(f"No se pudo enviar SMS para cita {cita.id}")
        except Exception as e:
            resultado['sms']['error'] = str(e)
            logger.error(f"Error al enviar SMS para cita {cita.id}: {e}")
    except Exception as e:
        resultado['sms']['error'] = str(e)
        logger.error(f"Error al enviar SMS para cita {cita.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # INTENTAR ENVIAR POR CORREO ELECTRÓNICO
    # Obtener email del paciente de forma segura
    email_paciente = None
    try:
        # Intentar usar la propiedad email_paciente (puede fallar si el modelo no está completamente cargado)
        email_paciente = cita.email_paciente
    except (AttributeError, TypeError):
        # Si falla, intentar desde el cliente directamente
        try:
            if cita.cliente:
                email_paciente = getattr(cita.cliente, 'email', None)
            else:
                # Usar el campo de respaldo
                email_paciente = getattr(cita, 'paciente_email', None)
        except (AttributeError, TypeError):
            email_paciente = None
    if email_paciente:
        try:
            from citas.email_service import enviar_email_confirmacion_cita
            email_result = enviar_email_confirmacion_cita(cita)
            if email_result:
                resultado['email']['enviado'] = True
                logger.info(f"Correo de confirmación enviado exitosamente para cita {cita.id} a {email_paciente}")
            else:
                resultado['email']['error'] = "No se pudo enviar correo"
        except ImportError:
            resultado['email']['error'] = "Servicio de correo no disponible"
        except Exception as e:
            resultado['email']['error'] = str(e)
            logger.error(f"Error al enviar correo de confirmación para cita {cita.id}: {e}")
    else:
        resultado['email']['error'] = "No hay email del paciente"
        logger.warning(f"No hay email del paciente para enviar correo de confirmación (Cita ID: {cita.id})")
    
    # Log del resultado final
    canales_exitosos = []
    if resultado['whatsapp']['enviado']:
        canales_exitosos.append('WhatsApp')
    if resultado['sms']['enviado']:
        canales_exitosos.append('SMS')
    if resultado['email']['enviado']:
        canales_exitosos.append('Correo')
    
    if canales_exitosos:
        logger.info(f"Notificaciones enviadas por: {', '.join(canales_exitosos)} para cita {cita.id}")
    else:
        logger.warning(f"No se pudieron enviar notificaciones por ningún canal para cita {cita.id}")
    
    return resultado


def enviar_notificaciones_cancelacion_cita(cita, telefono_override: str | None = None):
    """
    Envía notificaciones de cancelación de cita por WhatsApp, SMS Y correo electrónico.
    
    Args:
        cita: Objeto Cita del modelo
        telefono_override: Teléfono alternativo (opcional)
    
    Returns:
        dict: Resultado del envío con estado de cada canal
    """
    resultado = {
        'whatsapp': {'enviado': False, 'error': None},
        'sms': {'enviado': False, 'error': None},
        'email': {'enviado': False, 'error': None}
    }
    
    telefono = telefono_override or cita.telefono_paciente
    email_paciente = cita.email_paciente or (cita.cliente.email if cita.cliente else None)
    
    # INTENTAR ENVIAR POR WHATSAPP
    logger.info(f"[DEBUG] Intentando enviar WhatsApp de cancelación para cita {cita.id}. Teléfono: {telefono}, telefono_override: {telefono_override}")
    if telefono:
        try:
            from citas.twilio_service import enviar_whatsapp_cancelacion_cita
            logger.info(f"[DEBUG] Función enviar_whatsapp_cancelacion_cita importada correctamente")
            whatsapp_result = enviar_whatsapp_cancelacion_cita(cita, telefono_override)
            logger.info(f"[DEBUG] Resultado de enviar_whatsapp_cancelacion_cita: {whatsapp_result}")
            if whatsapp_result and whatsapp_result.get('sid'):
                resultado['whatsapp']['enviado'] = True
                logger.info(f"WhatsApp de cancelación enviado exitosamente para cita {cita.id} (SID: {whatsapp_result.get('sid')})")
            else:
                resultado['whatsapp']['error'] = f"No se pudo enviar WhatsApp. Resultado: {whatsapp_result}"
                logger.warning(f"No se pudo enviar WhatsApp de cancelación para cita {cita.id}. Resultado recibido: {whatsapp_result}")
                if whatsapp_result:
                    logger.warning(f"Detalles del resultado: {whatsapp_result}")
        except ImportError as e:
            resultado['whatsapp']['error'] = "Servicio de WhatsApp no disponible"
            logger.warning(f"Servicio de WhatsApp no disponible: {e}")
            import traceback
            logger.error(traceback.format_exc())
        except Exception as e:
            resultado['whatsapp']['error'] = str(e)
            logger.error(f"Error al enviar WhatsApp de cancelación para cita {cita.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        resultado['whatsapp']['error'] = "No hay teléfono del paciente"
        logger.warning(f"No hay teléfono del paciente para enviar WhatsApp de cancelación (Cita ID: {cita.id})")
    
    # INTENTAR ENVIAR POR SMS
    if telefono:
        try:
            from citas.twilio_service import enviar_sms_cancelacion_cita
            sms_result = enviar_sms_cancelacion_cita(cita, telefono_override)
            if sms_result and sms_result.get('sid'):
                resultado['sms']['enviado'] = True
                logger.info(f"SMS de cancelación enviado exitosamente para cita {cita.id}")
            else:
                resultado['sms']['error'] = "No se pudo enviar SMS"
        except ImportError:
            resultado['sms']['error'] = "Servicio de SMS no disponible"
        except Exception as e:
            resultado['sms']['error'] = str(e)
            logger.error(f"Error al enviar SMS de cancelación para cita {cita.id}: {e}")
    else:
        resultado['sms']['error'] = "No hay teléfono del paciente"
        logger.warning(f"No hay teléfono del paciente para enviar SMS de cancelación (Cita ID: {cita.id})")
    
    # INTENTAR ENVIAR POR CORREO ELECTRÓNICO
    if email_paciente:
        try:
            from citas.email_service import enviar_email_cancelacion_cita
            email_result = enviar_email_cancelacion_cita(cita)
            if email_result:
                resultado['email']['enviado'] = True
                logger.info(f"Correo de cancelación enviado exitosamente para cita {cita.id} a {email_paciente}")
            else:
                resultado['email']['error'] = "No se pudo enviar correo"
        except ImportError:
            resultado['email']['error'] = "Servicio de correo no disponible"
        except Exception as e:
            resultado['email']['error'] = str(e)
            logger.error(f"Error al enviar correo de cancelación para cita {cita.id}: {e}")
    else:
        resultado['email']['error'] = "No hay email del paciente"
        logger.warning(f"No hay email del paciente para enviar correo de cancelación (Cita ID: {cita.id})")
    
    # Log del resultado final
    canales_exitosos = []
    if resultado['whatsapp']['enviado']:
        canales_exitosos.append('WhatsApp')
    if resultado['sms']['enviado']:
        canales_exitosos.append('SMS')
    if resultado['email']['enviado']:
        canales_exitosos.append('Correo')
    
    if canales_exitosos:
        logger.info(f"Notificaciones de cancelación enviadas por: {', '.join(canales_exitosos)} para cita {cita.id}")
    else:
        logger.warning(f"No se pudieron enviar notificaciones de cancelación por ningún canal para cita {cita.id}")
    
    return resultado

