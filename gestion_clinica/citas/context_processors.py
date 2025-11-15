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



































