"""
Servicio para obtener información del dentista desde el sistema de gestión
"""
from django.conf import settings
from django.db import connections
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

def obtener_info_dentista() -> Dict:
    """
    Obtiene la información del dentista desde la base de datos del sistema de gestión.
    """
    try:
        logger.info("🔍 Iniciando búsqueda de dentista en personal_perfil")
        
        # Conectar a la base de datos del sistema de gestión
        # Asumiendo que usas la misma base de datos pero con tablas diferentes
        with connections['default'].cursor() as cursor:
            # Buscar dentistas activos en la tabla de perfiles
            logger.info("📊 Ejecutando consulta SQL para buscar dentistas")
            cursor.execute("""
                SELECT nombre_completo, especialidad, telefono, email, numero_colegio, activo
                FROM personal_perfil 
                WHERE rol = 'dentista' AND activo = true
                ORDER BY nombre_completo
                LIMIT 1
            """)
            
            dentista = cursor.fetchone()
            logger.info(f"📋 Resultado de la consulta: {dentista}")
            
            if dentista:
                nombre, especialidad, telefono, email, numero_colegio, activo = dentista
                
                logger.info(f"✅ Dentista encontrado: {nombre}")
                return {
                    'nombre': nombre,
                    'especialidad': especialidad or 'Odontología General',
                    'telefono': telefono or '+56 2 2345 6789',
                    'email': email or 'dentista@clinicasonrisas.cl',
                    'horario_atencion': 'Lunes a Viernes: 9:00 - 18:00',
                    'foto': f'https://via.placeholder.com/150x150/667eea/ffffff?text={nombre.split()[0][:2]}',
                    'numero_colegio': numero_colegio or 'N/A',
                    'activo': activo,
                    'rol': 'dentista'
                }
            else:
                logger.warning("❌ No se encontraron dentistas activos en la base de datos")
                return _get_dentista_por_defecto()
                
    except Exception as e:
        logger.error(f"Error al obtener información del dentista: {e}")
        return _get_dentista_por_defecto()

def _get_dentista_por_defecto() -> Dict:
    """Retorna datos por defecto cuando no se puede conectar a la BD"""
    return {
        'nombre': 'Dr. Sin Asignar',
        'especialidad': 'Odontología General',
        'telefono': '+56 2 2345 6789',
        'email': 'contacto@clinicasonrisas.cl',
        'horario_atencion': 'Lunes a Viernes: 9:00 - 18:00',
        'foto': 'https://via.placeholder.com/150x150/667eea/ffffff?text=Dr.',
        'numero_colegio': 'N/A',
        'activo': True,
        'rol': 'dentista'
    }

def obtener_dentista_por_cliente(cliente_email: str) -> Optional[Dict]:
    """
    Obtiene el dentista asignado a un cliente específico.
    """
    try:
        logger.info(f"🔍 Buscando dentista para cliente: {cliente_email}")
        with connections['default'].cursor() as cursor:
            # Buscar el cliente y su dentista asignado desde las citas
            cursor.execute("""
                SELECT pc.nombre_completo as cliente_nombre,
                       p.nombre_completo, p.especialidad, p.telefono, p.email, 
                       p.numero_colegio, p.activo, p.fecha_registro
                FROM cuentas_perfilcliente pc
                LEFT JOIN reservas_cita rc ON pc.id = rc.cliente_id
                LEFT JOIN personal_perfil p ON rc.dentista_id = p.id
                WHERE pc.email = %s
                ORDER BY rc.fecha_hora DESC
                LIMIT 1
            """, [cliente_email])
            
            resultado = cursor.fetchone()
            logger.info(f"📋 Resultado de búsqueda cliente-dentista: {resultado}")
            
            if resultado:
                cliente_nombre, nombre, especialidad, telefono, email, numero_colegio, activo, fecha_registro = resultado
                
                if nombre:  # Si tiene dentista asignado
                    return {
                        'nombre': nombre,
                        'especialidad': especialidad or 'Odontología General',
                        'telefono': telefono or '+56 2 2345 6789',
                        'email': email or 'dentista@clinicasonrisas.cl',
                        'horario_atencion': 'Lunes a Viernes: 9:00 - 18:00',
                        'foto': f'https://via.placeholder.com/150x150/667eea/ffffff?text={nombre.split()[0][:2]}',
                        'numero_colegio': numero_colegio or 'N/A',
                        'activo': activo,
                        'rol': 'dentista',
                        'cliente_asignado': cliente_nombre
                    }
                else:
                    # Cliente sin dentista asignado, buscar dentista por defecto
                    logger.info(f"Cliente {cliente_email} no tiene dentista asignado, buscando dentista por defecto")
                    return obtener_info_dentista()
            else:
                # Cliente no encontrado, buscar dentista por defecto
                logger.warning(f"Cliente {cliente_email} no encontrado en la base de datos")
                return obtener_info_dentista()
                
    except Exception as e:
        logger.error(f"Error al obtener dentista del cliente {cliente_email}: {e}")
        return obtener_info_dentista()

def diagnosticar_base_datos() -> Dict:
    """
    Función de diagnóstico para verificar las tablas disponibles en la base de datos.
    """
    try:
        with connections['default'].cursor() as cursor:
            # Obtener todas las tablas de la base de datos (PostgreSQL)
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tablas = cursor.fetchall()
            
            # Buscar tablas que contengan 'perfil', 'cliente', 'cita'
            tablas_relevantes = []
            for tabla in tablas:
                nombre_tabla = tabla[0]
                if any(palabra in nombre_tabla.lower() for palabra in ['perfil', 'cliente', 'cita', 'dentista', 'gestion']):
                    tablas_relevantes.append(nombre_tabla)
            
            # Si encontramos tablas relevantes, obtener su estructura (PostgreSQL)
            estructuras = {}
            for tabla in tablas_relevantes[:3]:  # Solo las primeras 3
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, [tabla])
                columnas = cursor.fetchall()
                estructuras[tabla] = [col[0] for col in columnas]
            
            # Verificar si hay dentistas en personal_perfil
            dentistas_count = 0
            dentistas_data = []
            try:
                cursor.execute("SELECT COUNT(*) FROM personal_perfil WHERE rol = 'dentista' AND activo = true")
                dentistas_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT nombre_completo, especialidad, email FROM personal_perfil WHERE rol = 'dentista' AND activo = true LIMIT 3")
                dentistas_data = cursor.fetchall()
            except Exception as e:
                logger.error(f"Error al verificar dentistas: {e}")
            
            # Verificar si hay citas
            citas_count = 0
            try:
                cursor.execute("SELECT COUNT(*) FROM reservas_cita")
                citas_count = cursor.fetchone()[0]
            except Exception as e:
                logger.error(f"Error al verificar citas: {e}")
            
            # Verificar si hay citas con pacientes
            citas_con_pacientes = 0
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM reservas_cita 
                    WHERE cliente_id IS NOT NULL
                """)
                citas_con_pacientes = cursor.fetchone()[0]
            except Exception as e:
                logger.error(f"Error al verificar citas con pacientes: {e}")
            
            return {
                'todas_las_tablas': [t[0] for t in tablas],
                'tablas_relevantes': tablas_relevantes,
                'estructuras': estructuras,
                'dentistas_count': dentistas_count,
                'dentistas_data': dentistas_data,
                'citas_count': citas_count,
                'citas_con_pacientes': citas_con_pacientes
            }
            
    except Exception as e:
        logger.error(f"Error en diagnóstico de base de datos: {e}")
        return {'error': str(e)}

def obtener_estadisticas_dentista() -> Dict:
    """
    Obtiene estadísticas del dentista desde el sistema de gestión.
    """
    try:
        with connections['default'].cursor() as cursor:
            # Obtener estadísticas generales de dentistas
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT rc.cliente_id) as total_pacientes,
                    COUNT(rc.id) as citas_totales,
                    COUNT(CASE WHEN rc.tomada = true THEN 1 END) as citas_completadas,
                    COUNT(CASE WHEN rc.tomada = false AND rc.cliente_id IS NOT NULL THEN 1 END) as citas_pendientes,
                    COUNT(CASE WHEN DATE(rc.fecha_hora) = CURRENT_DATE THEN 1 END) as citas_hoy
                FROM personal_perfil p
                LEFT JOIN reservas_cita rc ON rc.dentista_id = p.id
                WHERE p.rol = 'dentista' AND p.activo = true
            """)
            
            stats = cursor.fetchone()
            logger.info(f"📊 Estadísticas obtenidas: {stats}")
            
            if stats:
                total_pacientes, citas_totales, citas_completadas, citas_pendientes, citas_hoy = stats
                return {
                    'total_pacientes': total_pacientes or 0,
                    'citas_totales': citas_totales or 0,
                    'citas_completadas': citas_completadas or 0,
                    'citas_pendientes': citas_pendientes or 0,
                    'citas_hoy': citas_hoy or 0
                }
            else:
                return {
                    'total_pacientes': 0,
                    'citas_totales': 0,
                    'citas_completadas': 0,
                    'citas_pendientes': 0,
                    'citas_hoy': 0
                }
                
    except Exception as e:
        logger.error(f"Error al obtener estadísticas del dentista: {e}")
        return {
            'total_pacientes': 0,
            'citas_totales': 0,
            'citas_completadas': 0,
            'citas_pendientes': 0,
            'citas_hoy': 0
        }

def obtener_todos_dentistas_activos() -> list:
    """
    Obtiene la lista de todos los dentistas activos del sistema.
    """
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre_completo, especialidad, telefono, email, 
                       numero_colegio, activo, fecha_registro, rol
                FROM personal_perfil
                WHERE rol = 'dentista' AND activo = true
                ORDER BY nombre_completo
            """)
            
            dentistas = cursor.fetchall()
            lista_dentistas = []
            
            for dentista in dentistas:
                perfil_id, nombre, especialidad, telefono, email, numero_colegio, activo, fecha_registro, rol = dentista
                
                # Buscar foto del dentista
                foto = None
                try:
                    cursor.execute("""
                        SELECT foto 
                        FROM personal_perfil 
                        WHERE id = %s
                    """, [perfil_id])
                    resultado_foto = cursor.fetchone()
                    if resultado_foto and resultado_foto[0]:
                        foto = resultado_foto[0]
                except Exception:
                    pass
                
                # Si no hay foto, usar placeholder con iniciales
                if not foto:
                    iniciales = ''.join([p[0].upper() for p in nombre.split()[:2]]) if nombre else 'DT'
                    foto = f'https://ui-avatars.com/api/?name={iniciales}&background=3b82f6&color=fff&size=200&bold=true'
                
                lista_dentistas.append({
                    'id': perfil_id,
                    'nombre': nombre,
                    'especialidad': especialidad or 'Odontología General',
                    'telefono': telefono or '+56 2 2345 6789',
                    'email': email or 'dentista@clinicasonrisas.cl',
                    'numero_colegio': numero_colegio or 'N/A',
                    'activo': activo if activo is not None else True,
                    'rol': rol or 'dentista',
                    'foto': foto
                })
            
            return lista_dentistas
                
    except Exception as e:
        logger.error(f"Error al obtener lista de dentistas: {e}")
        return []

def obtener_dentista_de_cita(cita_id: int) -> Optional[Dict]:
    """
    Obtiene la información del dentista asignado a una cita específica.
    """
    try:
        with connections['default'].cursor() as cursor:
            # Primero verificar qué dentista_id tiene la cita
            cursor.execute("""
                SELECT id, dentista_id, estado, fecha_hora, tipo_consulta
                FROM citas_cita
                WHERE id = %s
            """, [cita_id])
            
            cita_info = cursor.fetchone()
            
            if not cita_info:
                return None
            
            cita_id_db, dentista_id, estado, fecha_hora, tipo_consulta = cita_info
            
            if not dentista_id:
                return None
            
            # Buscar el dentista en personal_perfil
            cursor.execute("""
                SELECT id, nombre_completo, especialidad, telefono, email, 
                       numero_colegio, activo, fecha_registro, rol
                FROM personal_perfil
                WHERE id = %s
            """, [dentista_id])
            
            dentista = cursor.fetchone()
            
            if dentista:
                perfil_id, nombre, especialidad, telefono, email, numero_colegio, activo, fecha_registro, rol = dentista
                
                # Buscar foto del dentista (si existe campo foto en la tabla)
                foto = None
                try:
                    cursor.execute("""
                        SELECT foto 
                        FROM personal_perfil 
                        WHERE id = %s
                    """, [perfil_id])
                    resultado_foto = cursor.fetchone()
                    if resultado_foto and resultado_foto[0]:
                        foto_path = resultado_foto[0]
                        # Construir URL completa de la foto
                        # La foto se guarda en media/personal/ según el modelo
                        from django.conf import settings
                        if foto_path:
                            # Si es una ruta relativa, construir URL completa
                            if foto_path.startswith('http'):
                                foto = foto_path
                            else:
                                # Construir URL usando MEDIA_URL
                                media_url = getattr(settings, 'MEDIA_URL', '/media/')
                                # Obtener URL del sistema de gestión
                                gestion_url = getattr(settings, 'GESTION_BASE_URL', 'http://localhost:8001')
                                foto = f"{gestion_url}{media_url}{foto_path}"
                except Exception as e:
                    logger.warning(f"Error al obtener foto del dentista: {e}")
                    pass
                
                # Si no hay foto, usar placeholder con iniciales
                if not foto:
                    iniciales = ''.join([p[0].upper() for p in nombre.split()[:2]]) if nombre else 'DT'
                    foto = f'https://ui-avatars.com/api/?name={iniciales}&background=3b82f6&color=fff&size=200&bold=true'
                
                return {
                    'id': perfil_id,
                    'nombre': nombre,
                    'especialidad': especialidad or 'Odontología General',
                    'telefono': telefono or '+56 2 2345 6789',
                    'email': email or 'dentista@clinicasonrisas.cl',
                    'numero_colegio': numero_colegio or 'N/A',
                    'activo': activo if activo is not None else True,
                    'rol': rol or 'dentista',
                    'foto': foto
                }
            else:
                logger.warning(f"No se encontro dentista con ID {dentista_id} en personal_perfil")
                return None
                
    except Exception as e:
        logger.error(f"Error al obtener dentista de la cita {cita_id}: {e}", exc_info=True)
        return None
