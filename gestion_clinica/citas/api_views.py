from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Q
from .models import Cita
from pacientes.models import Cliente
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia
from .serializers import CitaSerializer, EvaluacionSerializer, ClienteSerializer, OdontogramaSerializer, RadiografiaSerializer


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_citas_disponibles(request):
    """
    Retorna todas las citas disponibles.
    
    Retorna:
    - 200: Lista de citas disponibles
    """
    qs = Cita.objects.filter(estado='disponible').order_by('fecha_hora')
    return Response(CitaSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_reservar_cita(request):
    """
    Reserva una cita disponible.
    
    Espera JSON:
    {
      "cita_id": 123,
      "nombre": "Juan Perez",
      "email": "juan@x.com",
      "telefono": "912345678"
    }
    
    Retorna:
    - 200: Cita reservada exitosamente
    - 400: Error (cita no disponible, datos inválidos, etc.)
    """
    data = request.data
    try:
        cita = Cita.objects.get(id=data.get('cita_id'), estado='disponible')
    except Cita.DoesNotExist:
        return Response(
            {"success": False, "detail": "Cita no disponible"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    nombre = data.get('nombre')
    email = data.get('email')
    telefono = data.get('telefono')
    
    if not nombre or not email:
        return Response(
            {"success": False, "detail": "Nombre y email son requeridos"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar o crear el cliente
    cliente, created = Cliente.objects.get_or_create(
        email=email,
        defaults={
            'nombre_completo': nombre,
            'telefono': telefono
        }
    )
    
    # Si el cliente ya existe, actualizar su información si es necesario
    if not created:
        if nombre and nombre != cliente.nombre_completo:
            cliente.nombre_completo = nombre
        if telefono and telefono != cliente.telefono:
            cliente.telefono = telefono
        cliente.save()
    
    # Asignar el cliente a la cita
    cita.cliente = cliente
    cita.paciente_nombre = nombre
    cita.paciente_email = email
    cita.paciente_telefono = telefono
    cita.estado = 'reservada'
    cita.save()
    
    return Response({
        "success": True,
        "message": "Cita reservada exitosamente",
        "data": CitaSerializer(cita).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_cliente(request):
    """
    Verifica si un cliente existe en el sistema.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: { "existe": true/false, "cliente": {...} }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
        return Response({
            "success": True,
            "existe": True,
            "cliente": {
                "id": cliente.id,
                "nombre_completo": cliente.nombre_completo,
                "email": cliente.email,
                "telefono": cliente.telefono,
                "rut": getattr(cliente, 'rut', None),
                "fecha_nacimiento": cliente.fecha_nacimiento.isoformat() if hasattr(cliente, 'fecha_nacimiento') and cliente.fecha_nacimiento else None,
                "alergias": getattr(cliente, 'alergias', None),
                "dentista_asignado": cliente.dentista_asignado.nombre_completo if hasattr(cliente, 'dentista_asignado') and cliente.dentista_asignado else None,
            }
        })
    except Cliente.DoesNotExist:
        return Response({
            "success": True,
            "existe": False,
            "mensaje": "Cliente no encontrado en el sistema."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_historial_citas(request):
    """
    Obtiene el historial de citas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de citas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener todas las citas del cliente (incluyendo por email por compatibilidad)
    citas = Cita.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_hora')
    
    return Response({
        "success": True,
        "total": citas.count(),
        "citas": CitaSerializer(citas, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_odontogramas_cliente(request):
    """
    Obtiene los odontogramas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de odontogramas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener odontogramas del cliente (incluyendo por email por compatibilidad)
    odontogramas = Odontograma.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_creacion')
    
    odontogramas_data = []
    for odontograma in odontogramas:
        odontogramas_data.append({
            "id": odontograma.id,
            "paciente_nombre": getattr(odontograma, 'paciente_nombre', None),
            "paciente_email": getattr(odontograma, 'paciente_email', None),
            "dentista": odontograma.dentista.nombre_completo if hasattr(odontograma, 'dentista') and odontograma.dentista else None,
            "fecha_creacion": odontograma.fecha_creacion.isoformat() if hasattr(odontograma, 'fecha_creacion') else None,
            "fecha_actualizacion": odontograma.fecha_actualizacion.isoformat() if hasattr(odontograma, 'fecha_actualizacion') else None,
            "motivo_consulta": getattr(odontograma, 'motivo_consulta', None),
            "estado_general": getattr(odontograma, 'estado_general', None),
            "higiene_oral": getattr(odontograma, 'higiene_oral', None),
            "plan_tratamiento": getattr(odontograma, 'plan_tratamiento', None),
            "total_dientes": odontograma.dientes.count() if hasattr(odontograma, 'dientes') else 0,
        })
    
    return Response({
        "success": True,
        "total": odontogramas.count(),
        "odontogramas": odontogramas_data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_radiografias_cliente(request):
    """
    Obtiene las radiografías de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de radiografías del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener radiografías del cliente (incluyendo por email por compatibilidad)
    radiografias = Radiografia.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_carga')
    
    radiografias_data = []
    for radiografia in radiografias:
        radiografias_data.append({
            "id": radiografia.id,
            "paciente_nombre": getattr(radiografia, 'paciente_nombre', None),
            "paciente_email": getattr(radiografia, 'paciente_email', None),
            "tipo": getattr(radiografia, 'tipo', None),
            "tipo_display": radiografia.get_tipo_display() if hasattr(radiografia, 'get_tipo_display') else None,
            "dentista": radiografia.dentista.nombre_completo if hasattr(radiografia, 'dentista') and radiografia.dentista else None,
            "fecha_carga": radiografia.fecha_carga.isoformat() if hasattr(radiografia, 'fecha_carga') else None,
            "fecha_tomada": radiografia.fecha_tomada.isoformat() if hasattr(radiografia, 'fecha_tomada') and radiografia.fecha_tomada else None,
            "descripcion": getattr(radiografia, 'descripcion', None),
            "imagen_url": radiografia.imagen.url if hasattr(radiografia, 'imagen') and radiografia.imagen else None,
            "imagen_anotada_url": radiografia.imagen_anotada.url if hasattr(radiografia, 'imagen_anotada') and radiografia.imagen_anotada else None,
        })
    
    return Response({
        "success": True,
        "total": radiografias.count(),
        "radiografias": radiografias_data
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_crear_evaluacion(request):
    """
    Endpoint para crear una evaluación desde el proyecto del cliente.
    
    Espera JSON:
    {
      "email_cliente": "cliente@example.com",
      "estrellas": 5,
      "comentario": "Excelente servicio"
    }
    
    Retorna:
    - 201: Evaluación creada exitosamente
    - 400: Error de validación (cliente no existe, ya envió evaluación, etc.)
    """
    serializer = EvaluacionSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        evaluacion = serializer.save()
        return Response(
            {
                "success": True,
                "message": "¡Gracias por tu evaluación! Tu opinión es muy importante para nosotros.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {
            "success": False,
            "message": "No se pudo enviar la evaluación. Por favor, verifica los datos.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_evaluacion(request):
    """
    Verifica si un cliente ya ha enviado una evaluación.
    
    Parámetros GET:
    - email: Email del cliente
    
    Retorna:
    - 200: { "puede_evaluar": true/false, "mensaje": "..." }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email)
        ya_evaluo = Evaluacion.objects.filter(cliente=cliente).exists()
        
        return Response({
            "success": True,
            "puede_evaluar": not ya_evaluo,
            "mensaje": "Ya has enviado una evaluación anteriormente." if ya_evaluo else "Puedes enviar tu evaluación."
        })
    
    except Cliente.DoesNotExist:
        return Response({
            "success": False,
            "puede_evaluar": False,
            "mensaje": "No se encontró un cliente registrado con este email. Debes tomar una cita primero para poder evaluar nuestro servicio."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_estadisticas_evaluaciones(request):
    """
    Retorna estadísticas públicas de las evaluaciones.
    
    Retorna:
    - Promedio de calificación
    - Total de evaluaciones
    - Distribución por estrellas
    """
    from django.db.models import Avg
    
    evaluaciones = Evaluacion.objects.filter(estado__in=['pendiente', 'revisada'])
    
    promedio = evaluaciones.aggregate(Avg('estrellas'))['estrellas__avg'] or 0
    total = evaluaciones.count()
    
    # Distribución por estrellas
    distribucion = {}
    for i in range(1, 6):
        count = evaluaciones.filter(estrellas=i).count()
        distribucion[f'{i}_estrellas'] = count
    
    return Response({
        "success": True,
        "promedio_calificacion": round(promedio, 2),
        "total_evaluaciones": total,
        "distribucion": distribucion
    })

from rest_framework import status, permissions
from django.db.models import Q
from .models import Cita
from pacientes.models import Cliente
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia
from .serializers import CitaSerializer, EvaluacionSerializer, ClienteSerializer, OdontogramaSerializer, RadiografiaSerializer


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_citas_disponibles(request):
    """
    Retorna todas las citas disponibles.
    
    Retorna:
    - 200: Lista de citas disponibles
    """
    qs = Cita.objects.filter(estado='disponible').order_by('fecha_hora')
    return Response(CitaSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_reservar_cita(request):
    """
    Reserva una cita disponible.
    
    Espera JSON:
    {
      "cita_id": 123,
      "nombre": "Juan Perez",
      "email": "juan@x.com",
      "telefono": "912345678"
    }
    
    Retorna:
    - 200: Cita reservada exitosamente
    - 400: Error (cita no disponible, datos inválidos, etc.)
    """
    data = request.data
    try:
        cita = Cita.objects.get(id=data.get('cita_id'), estado='disponible')
    except Cita.DoesNotExist:
        return Response(
            {"success": False, "detail": "Cita no disponible"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    nombre = data.get('nombre')
    email = data.get('email')
    telefono = data.get('telefono')
    
    if not nombre or not email:
        return Response(
            {"success": False, "detail": "Nombre y email son requeridos"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar o crear el cliente
    cliente, created = Cliente.objects.get_or_create(
        email=email,
        defaults={
            'nombre_completo': nombre,
            'telefono': telefono
        }
    )
    
    # Si el cliente ya existe, actualizar su información si es necesario
    if not created:
        if nombre and nombre != cliente.nombre_completo:
            cliente.nombre_completo = nombre
        if telefono and telefono != cliente.telefono:
            cliente.telefono = telefono
        cliente.save()
    
    # Asignar el cliente a la cita
    cita.cliente = cliente
    cita.paciente_nombre = nombre
    cita.paciente_email = email
    cita.paciente_telefono = telefono
    cita.estado = 'reservada'
    cita.save()
    
    return Response({
        "success": True,
        "message": "Cita reservada exitosamente",
        "data": CitaSerializer(cita).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_cliente(request):
    """
    Verifica si un cliente existe en el sistema.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: { "existe": true/false, "cliente": {...} }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
        return Response({
            "success": True,
            "existe": True,
            "cliente": {
                "id": cliente.id,
                "nombre_completo": cliente.nombre_completo,
                "email": cliente.email,
                "telefono": cliente.telefono,
                "rut": getattr(cliente, 'rut', None),
                "fecha_nacimiento": cliente.fecha_nacimiento.isoformat() if hasattr(cliente, 'fecha_nacimiento') and cliente.fecha_nacimiento else None,
                "alergias": getattr(cliente, 'alergias', None),
                "dentista_asignado": cliente.dentista_asignado.nombre_completo if hasattr(cliente, 'dentista_asignado') and cliente.dentista_asignado else None,
            }
        })
    except Cliente.DoesNotExist:
        return Response({
            "success": True,
            "existe": False,
            "mensaje": "Cliente no encontrado en el sistema."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_historial_citas(request):
    """
    Obtiene el historial de citas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de citas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener todas las citas del cliente (incluyendo por email por compatibilidad)
    citas = Cita.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_hora')
    
    return Response({
        "success": True,
        "total": citas.count(),
        "citas": CitaSerializer(citas, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_odontogramas_cliente(request):
    """
    Obtiene los odontogramas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de odontogramas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener odontogramas del cliente (incluyendo por email por compatibilidad)
    odontogramas = Odontograma.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_creacion')
    
    odontogramas_data = []
    for odontograma in odontogramas:
        odontogramas_data.append({
            "id": odontograma.id,
            "paciente_nombre": getattr(odontograma, 'paciente_nombre', None),
            "paciente_email": getattr(odontograma, 'paciente_email', None),
            "dentista": odontograma.dentista.nombre_completo if hasattr(odontograma, 'dentista') and odontograma.dentista else None,
            "fecha_creacion": odontograma.fecha_creacion.isoformat() if hasattr(odontograma, 'fecha_creacion') else None,
            "fecha_actualizacion": odontograma.fecha_actualizacion.isoformat() if hasattr(odontograma, 'fecha_actualizacion') else None,
            "motivo_consulta": getattr(odontograma, 'motivo_consulta', None),
            "estado_general": getattr(odontograma, 'estado_general', None),
            "higiene_oral": getattr(odontograma, 'higiene_oral', None),
            "plan_tratamiento": getattr(odontograma, 'plan_tratamiento', None),
            "total_dientes": odontograma.dientes.count() if hasattr(odontograma, 'dientes') else 0,
        })
    
    return Response({
        "success": True,
        "total": odontogramas.count(),
        "odontogramas": odontogramas_data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_radiografias_cliente(request):
    """
    Obtiene las radiografías de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de radiografías del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener radiografías del cliente (incluyendo por email por compatibilidad)
    radiografias = Radiografia.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_carga')
    
    radiografias_data = []
    for radiografia in radiografias:
        radiografias_data.append({
            "id": radiografia.id,
            "paciente_nombre": getattr(radiografia, 'paciente_nombre', None),
            "paciente_email": getattr(radiografia, 'paciente_email', None),
            "tipo": getattr(radiografia, 'tipo', None),
            "tipo_display": radiografia.get_tipo_display() if hasattr(radiografia, 'get_tipo_display') else None,
            "dentista": radiografia.dentista.nombre_completo if hasattr(radiografia, 'dentista') and radiografia.dentista else None,
            "fecha_carga": radiografia.fecha_carga.isoformat() if hasattr(radiografia, 'fecha_carga') else None,
            "fecha_tomada": radiografia.fecha_tomada.isoformat() if hasattr(radiografia, 'fecha_tomada') and radiografia.fecha_tomada else None,
            "descripcion": getattr(radiografia, 'descripcion', None),
            "imagen_url": radiografia.imagen.url if hasattr(radiografia, 'imagen') and radiografia.imagen else None,
            "imagen_anotada_url": radiografia.imagen_anotada.url if hasattr(radiografia, 'imagen_anotada') and radiografia.imagen_anotada else None,
        })
    
    return Response({
        "success": True,
        "total": radiografias.count(),
        "radiografias": radiografias_data
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_crear_evaluacion(request):
    """
    Endpoint para crear una evaluación desde el proyecto del cliente.
    
    Espera JSON:
    {
      "email_cliente": "cliente@example.com",
      "estrellas": 5,
      "comentario": "Excelente servicio"
    }
    
    Retorna:
    - 201: Evaluación creada exitosamente
    - 400: Error de validación (cliente no existe, ya envió evaluación, etc.)
    """
    serializer = EvaluacionSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        evaluacion = serializer.save()
        return Response(
            {
                "success": True,
                "message": "¡Gracias por tu evaluación! Tu opinión es muy importante para nosotros.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {
            "success": False,
            "message": "No se pudo enviar la evaluación. Por favor, verifica los datos.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_evaluacion(request):
    """
    Verifica si un cliente ya ha enviado una evaluación.
    
    Parámetros GET:
    - email: Email del cliente
    
    Retorna:
    - 200: { "puede_evaluar": true/false, "mensaje": "..." }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email)
        ya_evaluo = Evaluacion.objects.filter(cliente=cliente).exists()
        
        return Response({
            "success": True,
            "puede_evaluar": not ya_evaluo,
            "mensaje": "Ya has enviado una evaluación anteriormente." if ya_evaluo else "Puedes enviar tu evaluación."
        })
    
    except Cliente.DoesNotExist:
        return Response({
            "success": False,
            "puede_evaluar": False,
            "mensaje": "No se encontró un cliente registrado con este email. Debes tomar una cita primero para poder evaluar nuestro servicio."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_estadisticas_evaluaciones(request):
    """
    Retorna estadísticas públicas de las evaluaciones.
    
    Retorna:
    - Promedio de calificación
    - Total de evaluaciones
    - Distribución por estrellas
    """
    from django.db.models import Avg
    
    evaluaciones = Evaluacion.objects.filter(estado__in=['pendiente', 'revisada'])
    
    promedio = evaluaciones.aggregate(Avg('estrellas'))['estrellas__avg'] or 0
    total = evaluaciones.count()
    
    # Distribución por estrellas
    distribucion = {}
    for i in range(1, 6):
        count = evaluaciones.filter(estrellas=i).count()
        distribucion[f'{i}_estrellas'] = count
    
    return Response({
        "success": True,
        "promedio_calificacion": round(promedio, 2),
        "total_evaluaciones": total,
        "distribucion": distribucion
    })

from rest_framework import status, permissions
from django.db.models import Q
from .models import Cita
from pacientes.models import Cliente
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia
from .serializers import CitaSerializer, EvaluacionSerializer, ClienteSerializer, OdontogramaSerializer, RadiografiaSerializer


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_citas_disponibles(request):
    """
    Retorna todas las citas disponibles.
    
    Retorna:
    - 200: Lista de citas disponibles
    """
    qs = Cita.objects.filter(estado='disponible').order_by('fecha_hora')
    return Response(CitaSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_reservar_cita(request):
    """
    Reserva una cita disponible.
    
    Espera JSON:
    {
      "cita_id": 123,
      "nombre": "Juan Perez",
      "email": "juan@x.com",
      "telefono": "912345678"
    }
    
    Retorna:
    - 200: Cita reservada exitosamente
    - 400: Error (cita no disponible, datos inválidos, etc.)
    """
    data = request.data
    try:
        cita = Cita.objects.get(id=data.get('cita_id'), estado='disponible')
    except Cita.DoesNotExist:
        return Response(
            {"success": False, "detail": "Cita no disponible"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    nombre = data.get('nombre')
    email = data.get('email')
    telefono = data.get('telefono')
    
    if not nombre or not email:
        return Response(
            {"success": False, "detail": "Nombre y email son requeridos"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar o crear el cliente
    cliente, created = Cliente.objects.get_or_create(
        email=email,
        defaults={
            'nombre_completo': nombre,
            'telefono': telefono
        }
    )
    
    # Si el cliente ya existe, actualizar su información si es necesario
    if not created:
        if nombre and nombre != cliente.nombre_completo:
            cliente.nombre_completo = nombre
        if telefono and telefono != cliente.telefono:
            cliente.telefono = telefono
        cliente.save()
    
    # Asignar el cliente a la cita
    cita.cliente = cliente
    cita.paciente_nombre = nombre
    cita.paciente_email = email
    cita.paciente_telefono = telefono
    cita.estado = 'reservada'
    cita.save()
    
    return Response({
        "success": True,
        "message": "Cita reservada exitosamente",
        "data": CitaSerializer(cita).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_cliente(request):
    """
    Verifica si un cliente existe en el sistema.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: { "existe": true/false, "cliente": {...} }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
        return Response({
            "success": True,
            "existe": True,
            "cliente": {
                "id": cliente.id,
                "nombre_completo": cliente.nombre_completo,
                "email": cliente.email,
                "telefono": cliente.telefono,
                "rut": getattr(cliente, 'rut', None),
                "fecha_nacimiento": cliente.fecha_nacimiento.isoformat() if hasattr(cliente, 'fecha_nacimiento') and cliente.fecha_nacimiento else None,
                "alergias": getattr(cliente, 'alergias', None),
                "dentista_asignado": cliente.dentista_asignado.nombre_completo if hasattr(cliente, 'dentista_asignado') and cliente.dentista_asignado else None,
            }
        })
    except Cliente.DoesNotExist:
        return Response({
            "success": True,
            "existe": False,
            "mensaje": "Cliente no encontrado en el sistema."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_historial_citas(request):
    """
    Obtiene el historial de citas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de citas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener todas las citas del cliente (incluyendo por email por compatibilidad)
    citas = Cita.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_hora')
    
    return Response({
        "success": True,
        "total": citas.count(),
        "citas": CitaSerializer(citas, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_odontogramas_cliente(request):
    """
    Obtiene los odontogramas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de odontogramas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener odontogramas del cliente (incluyendo por email por compatibilidad)
    odontogramas = Odontograma.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_creacion')
    
    odontogramas_data = []
    for odontograma in odontogramas:
        odontogramas_data.append({
            "id": odontograma.id,
            "paciente_nombre": getattr(odontograma, 'paciente_nombre', None),
            "paciente_email": getattr(odontograma, 'paciente_email', None),
            "dentista": odontograma.dentista.nombre_completo if hasattr(odontograma, 'dentista') and odontograma.dentista else None,
            "fecha_creacion": odontograma.fecha_creacion.isoformat() if hasattr(odontograma, 'fecha_creacion') else None,
            "fecha_actualizacion": odontograma.fecha_actualizacion.isoformat() if hasattr(odontograma, 'fecha_actualizacion') else None,
            "motivo_consulta": getattr(odontograma, 'motivo_consulta', None),
            "estado_general": getattr(odontograma, 'estado_general', None),
            "higiene_oral": getattr(odontograma, 'higiene_oral', None),
            "plan_tratamiento": getattr(odontograma, 'plan_tratamiento', None),
            "total_dientes": odontograma.dientes.count() if hasattr(odontograma, 'dientes') else 0,
        })
    
    return Response({
        "success": True,
        "total": odontogramas.count(),
        "odontogramas": odontogramas_data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_radiografias_cliente(request):
    """
    Obtiene las radiografías de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de radiografías del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener radiografías del cliente (incluyendo por email por compatibilidad)
    radiografias = Radiografia.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_carga')
    
    radiografias_data = []
    for radiografia in radiografias:
        radiografias_data.append({
            "id": radiografia.id,
            "paciente_nombre": getattr(radiografia, 'paciente_nombre', None),
            "paciente_email": getattr(radiografia, 'paciente_email', None),
            "tipo": getattr(radiografia, 'tipo', None),
            "tipo_display": radiografia.get_tipo_display() if hasattr(radiografia, 'get_tipo_display') else None,
            "dentista": radiografia.dentista.nombre_completo if hasattr(radiografia, 'dentista') and radiografia.dentista else None,
            "fecha_carga": radiografia.fecha_carga.isoformat() if hasattr(radiografia, 'fecha_carga') else None,
            "fecha_tomada": radiografia.fecha_tomada.isoformat() if hasattr(radiografia, 'fecha_tomada') and radiografia.fecha_tomada else None,
            "descripcion": getattr(radiografia, 'descripcion', None),
            "imagen_url": radiografia.imagen.url if hasattr(radiografia, 'imagen') and radiografia.imagen else None,
            "imagen_anotada_url": radiografia.imagen_anotada.url if hasattr(radiografia, 'imagen_anotada') and radiografia.imagen_anotada else None,
        })
    
    return Response({
        "success": True,
        "total": radiografias.count(),
        "radiografias": radiografias_data
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_crear_evaluacion(request):
    """
    Endpoint para crear una evaluación desde el proyecto del cliente.
    
    Espera JSON:
    {
      "email_cliente": "cliente@example.com",
      "estrellas": 5,
      "comentario": "Excelente servicio"
    }
    
    Retorna:
    - 201: Evaluación creada exitosamente
    - 400: Error de validación (cliente no existe, ya envió evaluación, etc.)
    """
    serializer = EvaluacionSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        evaluacion = serializer.save()
        return Response(
            {
                "success": True,
                "message": "¡Gracias por tu evaluación! Tu opinión es muy importante para nosotros.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {
            "success": False,
            "message": "No se pudo enviar la evaluación. Por favor, verifica los datos.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_evaluacion(request):
    """
    Verifica si un cliente ya ha enviado una evaluación.
    
    Parámetros GET:
    - email: Email del cliente
    
    Retorna:
    - 200: { "puede_evaluar": true/false, "mensaje": "..." }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email)
        ya_evaluo = Evaluacion.objects.filter(cliente=cliente).exists()
        
        return Response({
            "success": True,
            "puede_evaluar": not ya_evaluo,
            "mensaje": "Ya has enviado una evaluación anteriormente." if ya_evaluo else "Puedes enviar tu evaluación."
        })
    
    except Cliente.DoesNotExist:
        return Response({
            "success": False,
            "puede_evaluar": False,
            "mensaje": "No se encontró un cliente registrado con este email. Debes tomar una cita primero para poder evaluar nuestro servicio."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_estadisticas_evaluaciones(request):
    """
    Retorna estadísticas públicas de las evaluaciones.
    
    Retorna:
    - Promedio de calificación
    - Total de evaluaciones
    - Distribución por estrellas
    """
    from django.db.models import Avg
    
    evaluaciones = Evaluacion.objects.filter(estado__in=['pendiente', 'revisada'])
    
    promedio = evaluaciones.aggregate(Avg('estrellas'))['estrellas__avg'] or 0
    total = evaluaciones.count()
    
    # Distribución por estrellas
    distribucion = {}
    for i in range(1, 6):
        count = evaluaciones.filter(estrellas=i).count()
        distribucion[f'{i}_estrellas'] = count
    
    return Response({
        "success": True,
        "promedio_calificacion": round(promedio, 2),
        "total_evaluaciones": total,
        "distribucion": distribucion
    })

from rest_framework import status, permissions
from django.db.models import Q
from .models import Cita
from pacientes.models import Cliente
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia
from .serializers import CitaSerializer, EvaluacionSerializer, ClienteSerializer, OdontogramaSerializer, RadiografiaSerializer


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_citas_disponibles(request):
    """
    Retorna todas las citas disponibles.
    
    Retorna:
    - 200: Lista de citas disponibles
    """
    qs = Cita.objects.filter(estado='disponible').order_by('fecha_hora')
    return Response(CitaSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_reservar_cita(request):
    """
    Reserva una cita disponible.
    
    Espera JSON:
    {
      "cita_id": 123,
      "nombre": "Juan Perez",
      "email": "juan@x.com",
      "telefono": "912345678"
    }
    
    Retorna:
    - 200: Cita reservada exitosamente
    - 400: Error (cita no disponible, datos inválidos, etc.)
    """
    data = request.data
    try:
        cita = Cita.objects.get(id=data.get('cita_id'), estado='disponible')
    except Cita.DoesNotExist:
        return Response(
            {"success": False, "detail": "Cita no disponible"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    nombre = data.get('nombre')
    email = data.get('email')
    telefono = data.get('telefono')
    
    if not nombre or not email:
        return Response(
            {"success": False, "detail": "Nombre y email son requeridos"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar o crear el cliente
    cliente, created = Cliente.objects.get_or_create(
        email=email,
        defaults={
            'nombre_completo': nombre,
            'telefono': telefono
        }
    )
    
    # Si el cliente ya existe, actualizar su información si es necesario
    if not created:
        if nombre and nombre != cliente.nombre_completo:
            cliente.nombre_completo = nombre
        if telefono and telefono != cliente.telefono:
            cliente.telefono = telefono
        cliente.save()
    
    # Asignar el cliente a la cita
    cita.cliente = cliente
    cita.paciente_nombre = nombre
    cita.paciente_email = email
    cita.paciente_telefono = telefono
    cita.estado = 'reservada'
    cita.save()
    
    return Response({
        "success": True,
        "message": "Cita reservada exitosamente",
        "data": CitaSerializer(cita).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_cliente(request):
    """
    Verifica si un cliente existe en el sistema.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: { "existe": true/false, "cliente": {...} }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
        return Response({
            "success": True,
            "existe": True,
            "cliente": {
                "id": cliente.id,
                "nombre_completo": cliente.nombre_completo,
                "email": cliente.email,
                "telefono": cliente.telefono,
                "rut": getattr(cliente, 'rut', None),
                "fecha_nacimiento": cliente.fecha_nacimiento.isoformat() if hasattr(cliente, 'fecha_nacimiento') and cliente.fecha_nacimiento else None,
                "alergias": getattr(cliente, 'alergias', None),
                "dentista_asignado": cliente.dentista_asignado.nombre_completo if hasattr(cliente, 'dentista_asignado') and cliente.dentista_asignado else None,
            }
        })
    except Cliente.DoesNotExist:
        return Response({
            "success": True,
            "existe": False,
            "mensaje": "Cliente no encontrado en el sistema."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_historial_citas(request):
    """
    Obtiene el historial de citas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de citas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener todas las citas del cliente (incluyendo por email por compatibilidad)
    citas = Cita.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_hora')
    
    return Response({
        "success": True,
        "total": citas.count(),
        "citas": CitaSerializer(citas, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_odontogramas_cliente(request):
    """
    Obtiene los odontogramas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de odontogramas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener odontogramas del cliente (incluyendo por email por compatibilidad)
    odontogramas = Odontograma.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_creacion')
    
    odontogramas_data = []
    for odontograma in odontogramas:
        odontogramas_data.append({
            "id": odontograma.id,
            "paciente_nombre": getattr(odontograma, 'paciente_nombre', None),
            "paciente_email": getattr(odontograma, 'paciente_email', None),
            "dentista": odontograma.dentista.nombre_completo if hasattr(odontograma, 'dentista') and odontograma.dentista else None,
            "fecha_creacion": odontograma.fecha_creacion.isoformat() if hasattr(odontograma, 'fecha_creacion') else None,
            "fecha_actualizacion": odontograma.fecha_actualizacion.isoformat() if hasattr(odontograma, 'fecha_actualizacion') else None,
            "motivo_consulta": getattr(odontograma, 'motivo_consulta', None),
            "estado_general": getattr(odontograma, 'estado_general', None),
            "higiene_oral": getattr(odontograma, 'higiene_oral', None),
            "plan_tratamiento": getattr(odontograma, 'plan_tratamiento', None),
            "total_dientes": odontograma.dientes.count() if hasattr(odontograma, 'dientes') else 0,
        })
    
    return Response({
        "success": True,
        "total": odontogramas.count(),
        "odontogramas": odontogramas_data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_radiografias_cliente(request):
    """
    Obtiene las radiografías de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de radiografías del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener radiografías del cliente (incluyendo por email por compatibilidad)
    radiografias = Radiografia.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_carga')
    
    radiografias_data = []
    for radiografia in radiografias:
        radiografias_data.append({
            "id": radiografia.id,
            "paciente_nombre": getattr(radiografia, 'paciente_nombre', None),
            "paciente_email": getattr(radiografia, 'paciente_email', None),
            "tipo": getattr(radiografia, 'tipo', None),
            "tipo_display": radiografia.get_tipo_display() if hasattr(radiografia, 'get_tipo_display') else None,
            "dentista": radiografia.dentista.nombre_completo if hasattr(radiografia, 'dentista') and radiografia.dentista else None,
            "fecha_carga": radiografia.fecha_carga.isoformat() if hasattr(radiografia, 'fecha_carga') else None,
            "fecha_tomada": radiografia.fecha_tomada.isoformat() if hasattr(radiografia, 'fecha_tomada') and radiografia.fecha_tomada else None,
            "descripcion": getattr(radiografia, 'descripcion', None),
            "imagen_url": radiografia.imagen.url if hasattr(radiografia, 'imagen') and radiografia.imagen else None,
            "imagen_anotada_url": radiografia.imagen_anotada.url if hasattr(radiografia, 'imagen_anotada') and radiografia.imagen_anotada else None,
        })
    
    return Response({
        "success": True,
        "total": radiografias.count(),
        "radiografias": radiografias_data
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_crear_evaluacion(request):
    """
    Endpoint para crear una evaluación desde el proyecto del cliente.
    
    Espera JSON:
    {
      "email_cliente": "cliente@example.com",
      "estrellas": 5,
      "comentario": "Excelente servicio"
    }
    
    Retorna:
    - 201: Evaluación creada exitosamente
    - 400: Error de validación (cliente no existe, ya envió evaluación, etc.)
    """
    serializer = EvaluacionSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        evaluacion = serializer.save()
        return Response(
            {
                "success": True,
                "message": "¡Gracias por tu evaluación! Tu opinión es muy importante para nosotros.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {
            "success": False,
            "message": "No se pudo enviar la evaluación. Por favor, verifica los datos.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_evaluacion(request):
    """
    Verifica si un cliente ya ha enviado una evaluación.
    
    Parámetros GET:
    - email: Email del cliente
    
    Retorna:
    - 200: { "puede_evaluar": true/false, "mensaje": "..." }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email)
        ya_evaluo = Evaluacion.objects.filter(cliente=cliente).exists()
        
        return Response({
            "success": True,
            "puede_evaluar": not ya_evaluo,
            "mensaje": "Ya has enviado una evaluación anteriormente." if ya_evaluo else "Puedes enviar tu evaluación."
        })
    
    except Cliente.DoesNotExist:
        return Response({
            "success": False,
            "puede_evaluar": False,
            "mensaje": "No se encontró un cliente registrado con este email. Debes tomar una cita primero para poder evaluar nuestro servicio."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_estadisticas_evaluaciones(request):
    """
    Retorna estadísticas públicas de las evaluaciones.
    
    Retorna:
    - Promedio de calificación
    - Total de evaluaciones
    - Distribución por estrellas
    """
    from django.db.models import Avg
    
    evaluaciones = Evaluacion.objects.filter(estado__in=['pendiente', 'revisada'])
    
    promedio = evaluaciones.aggregate(Avg('estrellas'))['estrellas__avg'] or 0
    total = evaluaciones.count()
    
    # Distribución por estrellas
    distribucion = {}
    for i in range(1, 6):
        count = evaluaciones.filter(estrellas=i).count()
        distribucion[f'{i}_estrellas'] = count
    
    return Response({
        "success": True,
        "promedio_calificacion": round(promedio, 2),
        "total_evaluaciones": total,
        "distribucion": distribucion
    })

from rest_framework import status, permissions
from django.db.models import Q
from .models import Cita
from pacientes.models import Cliente
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia
from .serializers import CitaSerializer, EvaluacionSerializer, ClienteSerializer, OdontogramaSerializer, RadiografiaSerializer


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_citas_disponibles(request):
    """
    Retorna todas las citas disponibles.
    
    Retorna:
    - 200: Lista de citas disponibles
    """
    qs = Cita.objects.filter(estado='disponible').order_by('fecha_hora')
    return Response(CitaSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_reservar_cita(request):
    """
    Reserva una cita disponible.
    
    Espera JSON:
    {
      "cita_id": 123,
      "nombre": "Juan Perez",
      "email": "juan@x.com",
      "telefono": "912345678"
    }
    
    Retorna:
    - 200: Cita reservada exitosamente
    - 400: Error (cita no disponible, datos inválidos, etc.)
    """
    data = request.data
    try:
        cita = Cita.objects.get(id=data.get('cita_id'), estado='disponible')
    except Cita.DoesNotExist:
        return Response(
            {"success": False, "detail": "Cita no disponible"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    nombre = data.get('nombre')
    email = data.get('email')
    telefono = data.get('telefono')
    
    if not nombre or not email:
        return Response(
            {"success": False, "detail": "Nombre y email son requeridos"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar o crear el cliente
    cliente, created = Cliente.objects.get_or_create(
        email=email,
        defaults={
            'nombre_completo': nombre,
            'telefono': telefono
        }
    )
    
    # Si el cliente ya existe, actualizar su información si es necesario
    if not created:
        if nombre and nombre != cliente.nombre_completo:
            cliente.nombre_completo = nombre
        if telefono and telefono != cliente.telefono:
            cliente.telefono = telefono
        cliente.save()
    
    # Asignar el cliente a la cita
    cita.cliente = cliente
    cita.paciente_nombre = nombre
    cita.paciente_email = email
    cita.paciente_telefono = telefono
    cita.estado = 'reservada'
    cita.save()
    
    return Response({
        "success": True,
        "message": "Cita reservada exitosamente",
        "data": CitaSerializer(cita).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_cliente(request):
    """
    Verifica si un cliente existe en el sistema.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: { "existe": true/false, "cliente": {...} }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
        return Response({
            "success": True,
            "existe": True,
            "cliente": {
                "id": cliente.id,
                "nombre_completo": cliente.nombre_completo,
                "email": cliente.email,
                "telefono": cliente.telefono,
                "rut": getattr(cliente, 'rut', None),
                "fecha_nacimiento": cliente.fecha_nacimiento.isoformat() if hasattr(cliente, 'fecha_nacimiento') and cliente.fecha_nacimiento else None,
                "alergias": getattr(cliente, 'alergias', None),
                "dentista_asignado": cliente.dentista_asignado.nombre_completo if hasattr(cliente, 'dentista_asignado') and cliente.dentista_asignado else None,
            }
        })
    except Cliente.DoesNotExist:
        return Response({
            "success": True,
            "existe": False,
            "mensaje": "Cliente no encontrado en el sistema."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_historial_citas(request):
    """
    Obtiene el historial de citas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de citas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener todas las citas del cliente (incluyendo por email por compatibilidad)
    citas = Cita.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_hora')
    
    return Response({
        "success": True,
        "total": citas.count(),
        "citas": CitaSerializer(citas, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_odontogramas_cliente(request):
    """
    Obtiene los odontogramas de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de odontogramas del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener odontogramas del cliente (incluyendo por email por compatibilidad)
    odontogramas = Odontograma.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_creacion')
    
    odontogramas_data = []
    for odontograma in odontogramas:
        odontogramas_data.append({
            "id": odontograma.id,
            "paciente_nombre": getattr(odontograma, 'paciente_nombre', None),
            "paciente_email": getattr(odontograma, 'paciente_email', None),
            "dentista": odontograma.dentista.nombre_completo if hasattr(odontograma, 'dentista') and odontograma.dentista else None,
            "fecha_creacion": odontograma.fecha_creacion.isoformat() if hasattr(odontograma, 'fecha_creacion') else None,
            "fecha_actualizacion": odontograma.fecha_actualizacion.isoformat() if hasattr(odontograma, 'fecha_actualizacion') else None,
            "motivo_consulta": getattr(odontograma, 'motivo_consulta', None),
            "estado_general": getattr(odontograma, 'estado_general', None),
            "higiene_oral": getattr(odontograma, 'higiene_oral', None),
            "plan_tratamiento": getattr(odontograma, 'plan_tratamiento', None),
            "total_dientes": odontograma.dientes.count() if hasattr(odontograma, 'dientes') else 0,
        })
    
    return Response({
        "success": True,
        "total": odontogramas.count(),
        "odontogramas": odontogramas_data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_radiografias_cliente(request):
    """
    Obtiene las radiografías de un cliente.
    
    Parámetros GET:
    - email: Email del cliente (requerido)
    
    Retorna:
    - 200: Lista de radiografías del cliente
    - 400: Email no proporcionado
    - 404: Cliente no encontrado
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email, activo=True)
    except Cliente.DoesNotExist:
        return Response(
            {
                "success": False,
                "mensaje": "Cliente no encontrado."
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener radiografías del cliente (incluyendo por email por compatibilidad)
    radiografias = Radiografia.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=email)
    ).order_by('-fecha_carga')
    
    radiografias_data = []
    for radiografia in radiografias:
        radiografias_data.append({
            "id": radiografia.id,
            "paciente_nombre": getattr(radiografia, 'paciente_nombre', None),
            "paciente_email": getattr(radiografia, 'paciente_email', None),
            "tipo": getattr(radiografia, 'tipo', None),
            "tipo_display": radiografia.get_tipo_display() if hasattr(radiografia, 'get_tipo_display') else None,
            "dentista": radiografia.dentista.nombre_completo if hasattr(radiografia, 'dentista') and radiografia.dentista else None,
            "fecha_carga": radiografia.fecha_carga.isoformat() if hasattr(radiografia, 'fecha_carga') else None,
            "fecha_tomada": radiografia.fecha_tomada.isoformat() if hasattr(radiografia, 'fecha_tomada') and radiografia.fecha_tomada else None,
            "descripcion": getattr(radiografia, 'descripcion', None),
            "imagen_url": radiografia.imagen.url if hasattr(radiografia, 'imagen') and radiografia.imagen else None,
            "imagen_anotada_url": radiografia.imagen_anotada.url if hasattr(radiografia, 'imagen_anotada') and radiografia.imagen_anotada else None,
        })
    
    return Response({
        "success": True,
        "total": radiografias.count(),
        "radiografias": radiografias_data
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_crear_evaluacion(request):
    """
    Endpoint para crear una evaluación desde el proyecto del cliente.
    
    Espera JSON:
    {
      "email_cliente": "cliente@example.com",
      "estrellas": 5,
      "comentario": "Excelente servicio"
    }
    
    Retorna:
    - 201: Evaluación creada exitosamente
    - 400: Error de validación (cliente no existe, ya envió evaluación, etc.)
    """
    serializer = EvaluacionSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        evaluacion = serializer.save()
        return Response(
            {
                "success": True,
                "message": "¡Gracias por tu evaluación! Tu opinión es muy importante para nosotros.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        {
            "success": False,
            "message": "No se pudo enviar la evaluación. Por favor, verifica los datos.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_verificar_evaluacion(request):
    """
    Verifica si un cliente ya ha enviado una evaluación.
    
    Parámetros GET:
    - email: Email del cliente
    
    Retorna:
    - 200: { "puede_evaluar": true/false, "mensaje": "..." }
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return Response(
            {
                "success": False,
                "mensaje": "Debes proporcionar un email."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cliente = Cliente.objects.get(email=email)
        ya_evaluo = Evaluacion.objects.filter(cliente=cliente).exists()
        
        return Response({
            "success": True,
            "puede_evaluar": not ya_evaluo,
            "mensaje": "Ya has enviado una evaluación anteriormente." if ya_evaluo else "Puedes enviar tu evaluación."
        })
    
    except Cliente.DoesNotExist:
        return Response({
            "success": False,
            "puede_evaluar": False,
            "mensaje": "No se encontró un cliente registrado con este email. Debes tomar una cita primero para poder evaluar nuestro servicio."
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_estadisticas_evaluaciones(request):
    """
    Retorna estadísticas públicas de las evaluaciones.
    
    Retorna:
    - Promedio de calificación
    - Total de evaluaciones
    - Distribución por estrellas
    """
    from django.db.models import Avg
    
    evaluaciones = Evaluacion.objects.filter(estado__in=['pendiente', 'revisada'])
    
    promedio = evaluaciones.aggregate(Avg('estrellas'))['estrellas__avg'] or 0
    total = evaluaciones.count()
    
    # Distribución por estrellas
    distribucion = {}
    for i in range(1, 6):
        count = evaluaciones.filter(estrellas=i).count()
        distribucion[f'{i}_estrellas'] = count
    
    return Response({
        "success": True,
        "promedio_calificacion": round(promedio, 2),
        "total_evaluaciones": total,
        "distribucion": distribucion
    })
