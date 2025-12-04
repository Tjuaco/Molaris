from personal.models import Perfil
from evaluaciones.models import Evaluacion

def perfil_context(request):
    """Context processor para incluir información del perfil en todos los templates"""
    if request.user.is_authenticated:
        try:
            perfil = Perfil.objects.get(user=request.user)
            
            # Obtener contador de evaluaciones pendientes
            evaluaciones_pendientes_count = Evaluacion.objects.filter(estado='pendiente').count()
            
            return {
                'perfil': perfil,
                'es_admin': perfil.es_administrativo(),
                'es_dentista': perfil.es_dentista(),
                'evaluaciones_pendientes': evaluaciones_pendientes_count,
            }
        except Perfil.DoesNotExist:
            return {
                'perfil': None,
                'es_admin': False,
                'es_dentista': False,
                'evaluaciones_pendientes': 0,
            }
    return {
        'perfil': None,
        'es_admin': False,
        'es_dentista': False,
        'evaluaciones_pendientes': 0,
    }


def info_clinica(request):
    """Context processor para incluir información de la clínica en todos los templates"""
    try:
        from configuracion.models import InformacionClinica
        info = InformacionClinica.obtener()
        return {
            'info_clinica': info,
            'nombre_clinica': info.nombre_clinica or 'Clínica Dental San Felipe',
            'direccion_clinica': info.direccion or '',
            'telefono_clinica': info.telefono or '',
            'email_clinica': info.email or '',
        }
    except Exception:
        # Si hay algún error, retornar valores por defecto
        return {
            'info_clinica': None,
            'nombre_clinica': 'Clínica Dental San Felipe',
            'direccion_clinica': '',
            'telefono_clinica': '',
            'email_clinica': '',
        }



































