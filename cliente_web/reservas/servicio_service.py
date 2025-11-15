"""
Servicio para obtener información del tipo de servicio desde la base de datos
"""
from django.db import connections
from typing import Dict, Optional
import logging
from .servicios_models import TipoServicio

logger = logging.getLogger(__name__)


def obtener_tipo_servicio_de_cita(cita_id: int, tipo_consulta: str = None) -> Optional[Dict]:
    """
    Obtiene la información del tipo de servicio asignado a una cita.
    Si no hay tipo_servicio_id, intenta buscar el servicio por tipo_consulta.
    """
    try:
        with connections['default'].cursor() as cursor:
            # Obtener tipo_servicio_id, precio_cobrado y tipo_consulta de la cita
            cursor.execute("""
                SELECT tipo_servicio_id, precio_cobrado, tipo_consulta
                FROM citas_cita
                WHERE id = %s
            """, [cita_id])
            
            cita_info = cursor.fetchone()
            
            if not cita_info:
                return None
            
            tipo_servicio_id, precio_cobrado, tipo_consulta_db = cita_info
            # Usar tipo_consulta del parámetro si no está en la BD
            tipo_consulta = tipo_consulta or tipo_consulta_db
            
            # Si no hay tipo_servicio_id, intentar buscar por tipo_consulta
            if not tipo_servicio_id:
                # Primero intentar buscar servicio por nombre similar al tipo_consulta
                if tipo_consulta:
                    try:
                        # Buscar servicio por nombre (case insensitive, parcial)
                        tipo_servicio = TipoServicio.objects.filter(
                            nombre__icontains=tipo_consulta,
                            activo=True
                        ).first()
                        
                        if tipo_servicio:
                            # Formatear precio
                            precio_a_mostrar = precio_cobrado if precio_cobrado else tipo_servicio.precio_base
                            if precio_a_mostrar:
                                precio_float = float(precio_a_mostrar)
                                if precio_float == int(precio_float):
                                    precio_formateado = f"${precio_float:,.0f}"
                                else:
                                    precio_formateado = f"${precio_float:,.2f}"
                            else:
                                precio_formateado = None
                            
                            return {
                                'id': tipo_servicio.id,
                                'nombre': tipo_servicio.nombre,
                                'descripcion': tipo_servicio.descripcion or '',
                                'categoria': tipo_servicio.categoria or '',
                                'precio_base': float(tipo_servicio.precio_base) if tipo_servicio.precio_base else None,
                                'precio_formateado': tipo_servicio.get_precio_formateado(),
                                'precio_cobrado': float(precio_cobrado) if precio_cobrado else None,
                                'precio_cobrado_formateado': precio_formateado if precio_cobrado else None,
                                'duracion_estimada': tipo_servicio.duracion_estimada,
                                'activo': tipo_servicio.activo,
                            }
                    except Exception as e:
                        logger.warning(f"Error al buscar servicio por tipo_consulta '{tipo_consulta}': {e}")
                
                # Si no se encontró servicio y hay precio_cobrado, retornar info básica
                if precio_cobrado:
                    # Formatear precio_cobrado
                    precio_float = float(precio_cobrado)
                    if precio_float == int(precio_float):
                        precio_formateado = f"${precio_float:,.0f}"
                    else:
                        precio_formateado = f"${precio_float:,.2f}"
                    
                    return {
                        'id': None,
                        'nombre': tipo_consulta or 'Servicio',
                        'descripcion': '',
                        'categoria': '',
                        'precio_base': None,
                        'precio_formateado': precio_formateado,
                        'precio_cobrado': precio_float,
                        'precio_cobrado_formateado': precio_formateado,
                        'duracion_estimada': None,
                        'activo': True,
                    }
                else:
                    logger.info(f"Cita {cita_id} no tiene tipo_servicio_id ni precio_cobrado asignado")
                    return None
            
            # Obtener información del tipo de servicio
            try:
                tipo_servicio = TipoServicio.objects.get(id=tipo_servicio_id)
                
                # Formatear precio_cobrado (mostrar decimales solo si son necesarios)
                precio_cobrado_formateado = None
                if precio_cobrado:
                    precio_float = float(precio_cobrado)
                    if precio_float == int(precio_float):
                        # Si no tiene decimales, mostrar sin decimales
                        precio_cobrado_formateado = f"${precio_float:,.0f}"
                    else:
                        # Si tiene decimales, mostrar con 2 decimales
                        precio_cobrado_formateado = f"${precio_float:,.2f}"
                
                return {
                    'id': tipo_servicio.id,
                    'nombre': tipo_servicio.nombre,
                    'descripcion': tipo_servicio.descripcion or '',
                    'categoria': tipo_servicio.categoria or '',
                    'precio_base': float(tipo_servicio.precio_base) if tipo_servicio.precio_base else None,
                    'precio_formateado': tipo_servicio.get_precio_formateado(),
                    'precio_cobrado': float(precio_cobrado) if precio_cobrado else None,
                    'precio_cobrado_formateado': precio_cobrado_formateado,
                    'duracion_estimada': tipo_servicio.duracion_estimada,
                    'activo': tipo_servicio.activo,
                }
            except TipoServicio.DoesNotExist:
                logger.warning(f"TipoServicio con id {tipo_servicio_id} no encontrado")
                return None
                
    except Exception as e:
        logger.error(f"Error al obtener tipo de servicio de cita {cita_id}: {e}")
        return None


def obtener_todos_tipos_servicio_activos() -> list:
    """
    Obtiene todos los tipos de servicio activos.
    """
    try:
        servicios = TipoServicio.objects.filter(activo=True).order_by('nombre')
        return [
            {
                'id': s.id,
                'nombre': s.nombre,
                'descripcion': s.descripcion or '',
                'categoria': s.categoria or '',
                'precio_base': float(s.precio_base) if s.precio_base else None,
                'precio_formateado': s.get_precio_formateado(),
                'duracion_estimada': s.duracion_estimada,
            }
            for s in servicios
        ]
    except Exception as e:
        logger.error(f"Error al obtener tipos de servicio: {e}")
        return []




