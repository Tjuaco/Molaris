# reservas/api_service.py
"""
Servicio para comunicarse con la API del sistema de gestión de la clínica
"""
import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


def _get_api_config() -> Tuple[str, Dict[str, str]]:
    """
    Obtiene la configuración de la API del sistema de gestión.
    
    Returns:
        tuple: (api_url, headers)
    """
    api_url = getattr(settings, 'GESTION_API_URL', 'http://localhost:8001/api')
    api_token = getattr(settings, 'GESTION_API_TOKEN', '')
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    if api_token:
        headers['Authorization'] = f'Token {api_token}'
    
    return api_url, headers


def _make_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Tuple[bool, Dict, Optional[str]]:
    """
    Realiza una petición HTTP a la API del sistema de gestión.
    
    Args:
        method: Método HTTP (GET, POST, etc.)
        endpoint: Endpoint de la API (sin la URL base)
        data: Datos para enviar en el body (para POST, PUT, etc.)
        params: Parámetros para la URL (para GET)
        
    Returns:
        tuple: (success: bool, response_data: dict, error_message: str or None)
    """
    api_url, headers = _get_api_config()
    url = f"{api_url}/{endpoint.lstrip('/')}"
    
    try:
        logger.info(f"Realizando petición {method} a {url}")
        if data:
            logger.debug(f"Datos: {data}")
        if params:
            logger.debug(f"Parámetros: {params}")
        
        response = requests.request(
            method=method,
            url=url,
            json=data if data else None,
            params=params,
            headers=headers,
            timeout=10
        )
        
        logger.info(f"Respuesta: {response.status_code}")
        
        # Intentar parsear JSON
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"detail": response.text}
        
        # Verificar si fue exitoso
        if response.status_code in [200, 201]:
            return True, response_data, None
        else:
            error_msg = response_data.get('detail') or response_data.get('message') or response_data.get('error') or f"Error {response.status_code}"
            logger.warning(f"Error en API: {error_msg}")
            return False, response_data, error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Timeout al conectar con el sistema de gestión"
        logger.error(error_msg)
        return False, {}, error_msg
        
    except requests.exceptions.ConnectionError:
        error_msg = "No se pudo conectar con el sistema de gestión. Verifica que esté ejecutándose."
        logger.error(error_msg)
        return False, {}, error_msg
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error de conexión: {str(e)}"
        logger.error(error_msg)
        return False, {}, error_msg
        
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, {}, error_msg


def verificar_cliente_existe(email: str) -> Tuple[bool, Optional[Dict]]:
    """
    Verifica si un cliente existe en el sistema de gestión.
    
    Args:
        email: Email del cliente
        
    Returns:
        tuple: (existe: bool, datos_cliente: dict or None)
    """
    endpoint = "clientes/verificar/"
    params = {'email': email}
    
    success, response_data, error_msg = _make_request('GET', endpoint, params=params)
    
    if success and response_data.get('existe'):
        return True, response_data.get('cliente')
    else:
        return False, None


def obtener_historial_citas(email: str) -> Tuple[bool, list, Optional[str]]:
    """
    Obtiene el historial de citas de un cliente.
    
    Args:
        email: Email del cliente
        
    Returns:
        tuple: (success: bool, citas: list, error_message: str or None)
    """
    endpoint = "citas/historial/"
    params = {'email': email}
    
    success, response_data, error_msg = _make_request('GET', endpoint, params=params)
    
    if success:
        citas = response_data.get('citas', [])
        return True, citas, None
    else:
        return False, [], error_msg


def obtener_odontogramas_cliente(email: str) -> Tuple[bool, list, Optional[str]]:
    """
    Obtiene los odontogramas de un cliente.
    
    Args:
        email: Email del cliente
        
    Returns:
        tuple: (success: bool, odontogramas: list, error_message: str or None)
    """
    endpoint = "documentos/odontogramas/"
    params = {'email': email}
    
    success, response_data, error_msg = _make_request('GET', endpoint, params=params)
    
    if success:
        odontogramas = response_data.get('odontogramas', [])
        return True, odontogramas, None
    else:
        return False, [], error_msg


def obtener_radiografias_cliente(email: str) -> Tuple[bool, list, Optional[str]]:
    """
    Obtiene las radiografías de un cliente.
    
    Args:
        email: Email del cliente
        
    Returns:
        tuple: (success: bool, radiografias: list, error_message: str or None)
    """
    endpoint = "documentos/radiografias/"
    params = {'email': email}
    
    success, response_data, error_msg = _make_request('GET', endpoint, params=params)
    
    if success:
        radiografias = response_data.get('radiografias', [])
        return True, radiografias, None
    else:
        return False, [], error_msg


def verificar_puede_evaluar(email: str) -> Tuple[bool, bool, Optional[str]]:
    """
    Verifica si un cliente puede enviar una evaluación.
    
    Args:
        email: Email del cliente
        
    Returns:
        tuple: (success: bool, puede_evaluar: bool, mensaje: str or None)
    """
    endpoint = "evaluaciones/verificar/"
    params = {'email': email}
    
    success, response_data, error_msg = _make_request('GET', endpoint, params=params)
    
    if success:
        puede_evaluar = response_data.get('puede_evaluar', False)
        mensaje = response_data.get('mensaje', '')
        return True, puede_evaluar, mensaje
    else:
        return False, False, error_msg
