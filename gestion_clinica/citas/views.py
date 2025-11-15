from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, F, Sum, Avg
from datetime import datetime, timedelta
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout, authenticate
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# PDF generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO

from .models import Cita, TipoServicio, HorarioDentista
from personal.models import Perfil
from pacientes.models import Cliente
from inventario.models import Insumo, MovimientoInsumo
from historial_clinico.models import Odontograma, EstadoDiente, Radiografia
from proveedores.models import Proveedor, SolicitudInsumo
from evaluaciones.models import Evaluacion
from finanzas.models import IngresoManual, EgresoManual
# Importar el modelo de clientes de la app cuentas
try:
    from cuentas.models import PerfilCliente
except ImportError:
    PerfilCliente = None
from .forms import RegistroTrabajadorForm, PerfilForm
import re


def normalizar_telefono_chileno(telefono):
    """
    Normaliza un número de teléfono chileno al formato +56912345678
    Prioriza el formato de 8 dígitos (los últimos 8 del número celular).
    Acepta varios formatos de entrada:
    - 12345678 (8 dígitos - formato preferido, se agrega 9 y código país)
    - 912345678 (9 dígitos con 9 inicial)
    - +56912345678 (formato completo)
    - 56912345678 (con código país pero sin +)
    
    Retorna el número normalizado como +56912345678 o None si no es válido
    """
    if not telefono:
        return None
    
    # Eliminar espacios, guiones, paréntesis y otros caracteres
    telefono_limpio = re.sub(r'[\s\-\(\)\.]', '', str(telefono).strip())
    
    # Si empieza con +, eliminarlo para procesar
    if telefono_limpio.startswith('+'):
        telefono_limpio = telefono_limpio[1:]
    
    # Si empieza con 0, eliminarlo (formato nacional antiguo)
    if telefono_limpio.startswith('0'):
        telefono_limpio = telefono_limpio[1:]
    
    # Validar que solo contenga dígitos
    if not telefono_limpio.isdigit():
        return None
    
    # CASO PREFERIDO: 8 dígitos (solo los últimos 8 del número celular)
    # Se agrega el 9 inicial y el código de país 56
    if len(telefono_limpio) == 8:
        return f"+569{telefono_limpio}"
    
    # CASO 2: Ya tiene código de país 56 y empieza con 9 (+56912345678 o 56912345678)
    if telefono_limpio.startswith('569') and len(telefono_limpio) == 11:
        return f"+{telefono_limpio}"
    
    # CASO 3: Solo tiene 9 dígitos empezando con 9 (912345678)
    if telefono_limpio.startswith('9') and len(telefono_limpio) == 9:
        return f"+56{telefono_limpio}"
    
    # CASO 4: Tiene código 56 seguido de 9 dígitos (56912345678)
    if telefono_limpio.startswith('56') and len(telefono_limpio) == 11:
        # Verificar que el tercer dígito sea 9 (celular)
        if telefono_limpio[2] == '9':
            return f"+{telefono_limpio}"
    
    # Si no coincide con ningún formato válido, retornar None
    return None

# Importar vistas del dashboard
from .views_dashboard import (
    dashboard_reportes,
    exportar_excel_citas,
    exportar_excel_clientes,
    exportar_excel_insumos,
    exportar_excel_finanzas
)

# Página de inicio (redirige al login)
def inicio(request):
    return redirect('login')

# Login personalizado para trabajadores
class TrabajadorLoginView(LoginView):
    template_name = 'citas/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Asegurar que el formulario esté en el contexto
        if 'form' not in context:
            from django.contrib.auth.forms import AuthenticationForm
            context['form'] = AuthenticationForm()
        return context
    
    def form_invalid(self, form):
        """Personalizar mensajes de error de autenticación"""
        # Obtener el username del POST directamente si cleaned_data no está disponible
        username = self.request.POST.get('username', '').strip()
        password = self.request.POST.get('password', '')
        
        # Limpiar mensajes anteriores
        storage = messages.get_messages(self.request)
        storage.used = True
        
        # Verificar si el usuario existe
        if username:
            try:
                user = User.objects.get(username=username)
                # Si el usuario existe, verificar la contraseña
                if password:
                    if not user.check_password(password):
                        messages.error(self.request, '❌ Contraseña incorrecta. Por favor, verifica tu contraseña.')
                    elif not user.is_active:
                        messages.error(self.request, '⚠️ Tu cuenta está desactivada. Contacta al administrador.')
                    else:
                        # Si la contraseña es correcta pero aún falla, puede ser otro problema
                        messages.error(self.request, '❌ Error al iniciar sesión. Por favor, intenta nuevamente.')
                else:
                    messages.error(self.request, '❌ Por favor, ingresa tu contraseña.')
            except User.DoesNotExist:
                messages.error(self.request, '❌ Este usuario no existe. Verifica que hayas ingresado correctamente tu nombre de usuario.')
            except Exception as e:
                messages.error(self.request, f'❌ Error al verificar credenciales. Por favor, intenta nuevamente.')
        else:
            messages.error(self.request, '❌ Por favor, ingresa tu nombre de usuario.')
        
        return super().form_invalid(form)

    def get_success_url(self):
        # Redirigir según rol del trabajador
        try:
            perfil = Perfil.objects.get(user=self.request.user)
            if perfil.activo:
                # Si es dentista, redirigir a Mi Perfil
                if perfil.es_dentista():
                    return reverse_lazy('mi_perfil')
                # Si es administrativo, redirigir al panel de trabajador
                else:
                    return reverse_lazy('panel_trabajador')
            else:
                messages.error(self.request, 'Tu cuenta está desactivada. Contacta al administrador.')
                return reverse_lazy('login')
        except Perfil.DoesNotExist:
            messages.error(self.request, 'No tienes un perfil de trabajador válido.')
            return reverse_lazy('login')

# Panel trabajador (recepción/dentista)
@login_required
def panel_trabajador(request):
    # Solo permitir usuarios con perfil de trabajador
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.activo:
            messages.error(request, 'Tu cuenta está desactivada.')
            return redirect('login')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a este panel.')
        return redirect('login')

    # Obtener estadísticas según el rol
    if perfil.es_administrativo():
        # Panel administrativo simplificado
        citas_hoy = Cita.objects.filter(
            fecha_hora__date=timezone.now().date()
        ).order_by('fecha_hora')
        
        # IMPORTANTE: Primero limpiar referencias inválidas a clientes que no existen
        # Esto evita errores de integridad referencial
        from pacientes.models import Cliente
        from django.db import connection
        
        # Buscar citas con cliente_id que no existe en la tabla Cliente
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.id 
                FROM citas_cita c
                LEFT JOIN pacientes_cliente p ON c.cliente_id = p.id
                WHERE c.cliente_id IS NOT NULL 
                AND p.id IS NULL
            """)
            citas_con_cliente_invalido = [row[0] for row in cursor.fetchall()]
        
        # Limpiar referencias inválidas
        if citas_con_cliente_invalido:
            Cita.objects.filter(id__in=citas_con_cliente_invalido).update(cliente=None)
        
        # Listas simplificadas (con select_related para optimizar consultas)
        citas_creadas = Cita.objects.filter(estado='disponible').select_related('tipo_servicio', 'dentista', 'cliente').order_by('fecha_hora')
        citas_tomadas = Cita.objects.filter(estado='reservada').select_related('tipo_servicio', 'dentista', 'cliente').order_by('fecha_hora')
        citas_completadas = Cita.objects.filter(estado='completada').select_related('tipo_servicio', 'dentista', 'cliente').order_by('-fecha_hora')
        
        # IMPORTANTE: Actualizar paciente_nombre en citas que tienen cliente pero paciente_nombre es username
        # Esto corrige citas antiguas que se reservaron antes de la corrección
        
        # Ahora actualizar los nombres
        for cita in list(citas_tomadas) + list(citas_completadas):
            try:
                if cita.cliente:
                    # Si tiene cliente vinculado, usar siempre el nombre completo del cliente
                    if cita.paciente_nombre != cita.cliente.nombre_completo:
                        cita.paciente_nombre = cita.cliente.nombre_completo
                        cita.save(update_fields=['paciente_nombre'])
                elif cita.paciente_nombre and ' ' not in cita.paciente_nombre:
                    # Si no tiene cliente pero paciente_nombre parece ser username (sin espacios)
                    # Intentar buscar un Cliente por email para obtener el nombre completo
                    if cita.paciente_email:
                        try:
                            cliente = Cliente.objects.get(email=cita.paciente_email)
                            cita.cliente = cliente
                            cita.paciente_nombre = cliente.nombre_completo
                            cita.save(update_fields=['cliente', 'paciente_nombre'])
                        except Cliente.DoesNotExist:
                            pass
            except Exception as e:
                # Si hay algún error al procesar una cita, continuar con las demás
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error al procesar cita {cita.id}: {e}")
                continue
        
        # Obtener información de fichas (odontogramas) para citas tomadas y completadas
        from historial_clinico.models import Odontograma
        odontogramas = Odontograma.objects.filter(cita__isnull=False).select_related('cita')
        citas_con_ficha = set(odontogramas.values_list('cita_id', flat=True))
        
        # Agregar información de ficha a cada cita tomada
        for cita in citas_tomadas:
            cita.tiene_ficha = cita.id in citas_con_ficha
            if cita.tiene_ficha:
                cita.odontograma = odontogramas.filter(cita_id=cita.id).first()
        
        # Agregar información de ficha a cada cita completada
        for cita in citas_completadas:
            cita.tiene_ficha = cita.id in citas_con_ficha
            if cita.tiene_ficha:
                cita.odontograma = odontogramas.filter(cita_id=cita.id).first()
        
        citas_proximas = Cita.objects.filter(
            fecha_hora__gte=timezone.now(),
            estado='reservada'
        ).order_by('fecha_hora')[:10]
        
        disponibles_count = Cita.objects.filter(estado='disponible').count()
        tomadas_count = Cita.objects.filter(estado='reservada').count()
        realizadas_count = Cita.objects.filter(estado='completada').count()
        total_agendables = disponibles_count + tomadas_count
        ocupacion_pct = int((tomadas_count / total_agendables) * 100) if total_agendables > 0 else 0

        estadisticas = {
            'citas_hoy': Cita.objects.filter(fecha_hora__date=timezone.now().date()).count(),
            'disponibles': disponibles_count,
            'realizadas': realizadas_count,
            'ocupacion': ocupacion_pct,
        }
        
        # Obtener lista de dentistas para el select
        dentistas = Perfil.objects.filter(rol='dentista', activo=True).select_related('user')
        
        # Obtener servicios activos para el selector
        servicios_activos = TipoServicio.objects.filter(activo=True).order_by('categoria', 'nombre')
        
        # Obtener clientes activos para el selector de pacientes
        clientes = Cliente.objects.filter(activo=True).order_by('nombre_completo')
        
        # Obtener horarios de dentistas para validación en el frontend
        horarios_dentistas_dict = {}
        for dentista in dentistas:
            horarios = HorarioDentista.objects.filter(dentista=dentista, activo=True).order_by('dia_semana', 'hora_inicio')
            horarios_dentistas_dict[str(dentista.id)] = [
                {
                    'dia_semana': h.dia_semana,
                    'hora_inicio': h.hora_inicio.strftime('%H:%M'),
                    'hora_fin': h.hora_fin.strftime('%H:%M'),
                }
                for h in horarios
            ]
        
        context = {
            'perfil': perfil,
            'citas_hoy': citas_hoy,
            'citas_proximas': citas_proximas,
            'citas_creadas': citas_creadas,
            'citas_tomadas': citas_tomadas,
            'citas_completadas': citas_completadas,
            'estadisticas': estadisticas,
            'dentistas': dentistas,
            'servicios': servicios_activos,
            'clientes': clientes,
            'horarios_dentistas': horarios_dentistas_dict,  # Pasar el dict directamente, json_script lo convierte
            'es_admin': True
        }
        
    else:  # Dentista
        # Panel dentista - ver solo sus citas
        citas_hoy = Cita.objects.filter(
            fecha_hora__date=timezone.now().date(),
            dentista=perfil
        ).order_by('fecha_hora')
        
        citas_proximas = Cita.objects.filter(
            fecha_hora__gte=timezone.now(),
            dentista=perfil,
            estado='reservada'
        ).order_by('fecha_hora')[:10]
        
        disponibles_count = Cita.objects.filter(estado='disponible').count()
        tomadas_count = Cita.objects.filter(dentista=perfil, estado='reservada').count()
        citas_completadas = Cita.objects.filter(dentista=perfil, estado='completada').select_related('tipo_servicio', 'dentista', 'cliente').order_by('-fecha_hora')
        total_agendables = disponibles_count + tomadas_count
        ocupacion_pct = int((tomadas_count / total_agendables) * 100) if total_agendables > 0 else 0

        estadisticas = {
            'citas_hoy': citas_hoy.count(),
            'disponibles': disponibles_count,
            'realizadas': Cita.objects.filter(dentista=perfil, estado='completada').count(),
            'ocupacion': ocupacion_pct,
        }
        
        # Obtener lista de dentistas para el select
        dentistas = Perfil.objects.filter(rol='dentista', activo=True).select_related('user')
        
        # Obtener servicios activos para el selector
        servicios_activos = TipoServicio.objects.filter(activo=True).order_by('categoria', 'nombre')
        
        context = {
            'perfil': perfil,
            'citas_hoy': citas_hoy,
            'citas_proximas': citas_proximas,
            'citas_completadas': citas_completadas,
            'estadisticas': estadisticas,
            'dentistas': dentistas,
            'servicios': servicios_activos,
            'horarios_dentistas': {},  # Los dentistas no pueden crear citas, pero necesitamos la variable
            'es_admin': False
        }
    
    return render(request, 'citas/panel_trabajador.html', context)

# Agregar hora disponible (solo administrativos)
# Esta vista solo procesa POST desde el modal, nunca renderiza una página
@login_required
def agregar_hora(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para agregar horas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Si es GET, redirigir al panel (no debería accederse directamente)
    if request.method == 'GET':
        return redirect('panel_trabajador')
    
    # Procesar POST desde el modal
    if request.method == 'POST':
        fecha_hora_str = request.POST.get('fecha_hora', '')
        tipo_consulta = request.POST.get('tipo_consulta', '').strip()
        notas = request.POST.get('notas', '')
        dentista_id = request.POST.get('dentista_id', '')
        tipo_servicio_id = request.POST.get('tipo_servicio', '').strip()
        
        errores = []
        
        try:
            # Validar campos requeridos
            if not fecha_hora_str:
                errores.append('Debe seleccionar una fecha y hora.')
            
            if not dentista_id:
                errores.append('Debe seleccionar un dentista.')
            
            # El modal puede enviar tipo_consulta (nombre del servicio) o tipo_servicio (ID)
            # Si viene tipo_consulta, buscar el servicio por nombre
            tipo_servicio = None
            if tipo_servicio_id:
                try:
                    tipo_servicio = TipoServicio.objects.get(id=tipo_servicio_id, activo=True)
                except TipoServicio.DoesNotExist:
                    errores.append('El servicio seleccionado no existe o está inactivo.')
            elif tipo_consulta:
                # Buscar servicio por nombre
                try:
                    tipo_servicio = TipoServicio.objects.get(nombre=tipo_consulta, activo=True)
                    tipo_servicio_id = str(tipo_servicio.id)
                except TipoServicio.DoesNotExist:
                    # Si no se encuentra, se creará la cita con tipo_consulta como texto libre
                    pass
            
            # Si hay errores, devolver JSON para mostrar alerta en el modal
            if errores:
                return JsonResponse({'success': False, 'error': errores[0]}, status=400)
            
            # Convertir fecha y hacerla timezone-aware
            from django.utils import timezone
            fecha_hora_naive = datetime.fromisoformat(fecha_hora_str)
            # Hacer el datetime aware usando la timezone del sistema
            fecha_hora = timezone.make_aware(fecha_hora_naive)
            
            # Validar que la fecha no sea en el pasado
            ahora = timezone.now()
            if fecha_hora < ahora:
                return JsonResponse({'success': False, 'error': 'No se pueden crear citas en fechas pasadas. Por favor, seleccione una fecha y hora futura.'}, status=400)
            
            # Obtener el dentista seleccionado
            try:
                dentista = Perfil.objects.get(id=dentista_id, rol='dentista', activo=True)
            except Perfil.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Dentista seleccionado no válido o inactivo.'}, status=400)
            
            # Validar que la fecha/hora esté dentro del horario de trabajo del dentista
            dia_semana = fecha_hora.weekday()  # 0=Lunes, 6=Domingo
            hora_cita = fecha_hora.time()
            
            # Obtener horarios activos del dentista para ese día
            horarios_dia = HorarioDentista.objects.filter(
                dentista=dentista,
                dia_semana=dia_semana,
                activo=True
            )
            
            if not horarios_dia.exists():
                dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                return JsonResponse({'success': False, 'error': f'El dentista {dentista.nombre_completo} no trabaja los {dias_nombres[dia_semana]}.'}, status=400)
            
            # Verificar que la hora esté dentro de algún bloque de horario
            hora_valida = False
            for horario in horarios_dia:
                if horario.hora_inicio <= hora_cita < horario.hora_fin:
                    hora_valida = True
                    break
            
            if not hora_valida:
                horarios_str = ', '.join([f"{h.hora_inicio.strftime('%H:%M')}-{h.hora_fin.strftime('%H:%M')}" for h in horarios_dia])
                return JsonResponse({'success': False, 'error': f'La hora seleccionada no está dentro del horario de trabajo del dentista. Horarios disponibles: {horarios_str}'}, status=400)
            
            # Validar duración de la cita
            duracion_minutos = 30  # Duración por defecto
            if tipo_servicio and tipo_servicio.duracion_estimada:
                duracion_minutos = tipo_servicio.duracion_estimada
            
            # Calcular hora de fin de la cita
            from datetime import timedelta
            fecha_hora_fin = fecha_hora + timedelta(minutes=duracion_minutos)
            hora_fin_cita = fecha_hora_fin.time()
            
            # Verificar que la duración completa quepa en el bloque de horario
            duracion_valida = False
            for horario in horarios_dia:
                if horario.hora_inicio <= hora_cita and hora_fin_cita <= horario.hora_fin:
                    duracion_valida = True
                    break
            
            if not duracion_valida:
                return JsonResponse({'success': False, 'error': f'La duración del servicio ({duracion_minutos} minutos) no cabe en el horario seleccionado. Por favor, seleccione una hora más temprana.'}, status=400)
            
            # Verificar que no se solape con otra cita del mismo dentista
            citas_existentes = Cita.objects.filter(
                dentista=dentista,
                fecha_hora__date=fecha_hora.date(),
                estado__in=['disponible', 'reservada', 'confirmada']
            ).exclude(id=None)  # Excluir la cita actual si se está editando
            
            for cita_existente in citas_existentes:
                fecha_hora_existente_fin = cita_existente.fecha_hora
                if cita_existente.tipo_servicio and cita_existente.tipo_servicio.duracion_estimada:
                    fecha_hora_existente_fin += timedelta(minutes=cita_existente.tipo_servicio.duracion_estimada)
                else:
                    fecha_hora_existente_fin += timedelta(minutes=30)  # Duración por defecto
                
                # Verificar solapamiento
                if (fecha_hora < fecha_hora_existente_fin and fecha_hora_fin > cita_existente.fecha_hora):
                    return JsonResponse({'success': False, 'error': f'La cita se solapa con otra cita existente del dentista a las {cita_existente.fecha_hora.strftime("%H:%M")}.'}, status=400)
            
            # Verificar que no exista ya una cita en esa fecha/hora exacta
            if Cita.objects.filter(fecha_hora=fecha_hora).exists():
                return JsonResponse({'success': False, 'error': 'Ya existe una cita en esa fecha y hora exacta.'}, status=400)
            
            # Obtener precio del servicio si existe
            precio_cobrado = None
            if tipo_servicio:
                precio_cobrado = tipo_servicio.precio_base
                
                # Si hay precio_cobrado en el formulario, usarlo (puede ser un ajuste)
                precio_cobrado_str = request.POST.get('precio_cobrado', '').strip()
                if precio_cobrado_str:
                    try:
                        # Limpiar formato si tiene puntos
                        precio_cobrado_limpio = precio_cobrado_str.replace('.', '').replace(',', '.')
                        precio_ajustado = float(precio_cobrado_limpio)
                        if precio_ajustado > 0:
                            precio_cobrado = precio_ajustado
                    except ValueError:
                        pass  # Usar precio base si el ajuste no es válido
            
            # Manejar asignación de paciente (cliente existente o nuevo)
            cliente_obj = None
            paciente_nombre = None
            paciente_email = None
            paciente_telefono = None
            estado_cita = 'disponible'
            
            cliente_id = request.POST.get('cliente_id', '')
            if cliente_id:
                if cliente_id == 'nuevo':
                    # Crear nuevo cliente
                    paciente_nombre = request.POST.get('paciente_nombre', '').strip()
                    paciente_email = request.POST.get('paciente_email', '').strip()
                    paciente_telefono_raw = request.POST.get('paciente_telefono', '').strip()
                    
                    if paciente_nombre and paciente_email:
                        # Normalizar teléfono si se proporcionó
                        paciente_telefono = normalizar_telefono_chileno(paciente_telefono_raw) if paciente_telefono_raw else None
                        
                        # Crear o obtener cliente
                        cliente_obj, created = Cliente.objects.get_or_create(
                            email=paciente_email,
                            defaults={
                                'nombre_completo': paciente_nombre,
                                'telefono': paciente_telefono or '',
                                'activo': True
                            }
                        )
                        # Si el cliente ya existía, actualizar información si es necesario
                        if not created:
                            cliente_obj.nombre_completo = paciente_nombre
                            if paciente_telefono:
                                cliente_obj.telefono = paciente_telefono
                            cliente_obj.activo = True
                            cliente_obj.save()
                        
                        estado_cita = 'reservada'
                else:
                    # Usar cliente existente
                    try:
                        cliente_obj = Cliente.objects.get(id=cliente_id, activo=True)
                        paciente_nombre = cliente_obj.nombre_completo
                        paciente_email = cliente_obj.email
                        paciente_telefono = cliente_obj.telefono
                        estado_cita = 'reservada'
                    except Cliente.DoesNotExist:
                        messages.warning(request, 'El cliente seleccionado no existe o está inactivo.')
            
            # Crear la cita
            cita = Cita.objects.create(
                fecha_hora=fecha_hora,
                tipo_consulta=tipo_consulta,
                tipo_servicio=tipo_servicio,
                precio_cobrado=precio_cobrado,
                notas=notas,
                dentista=dentista,
                creada_por=perfil,
                cliente=cliente_obj,
                paciente_nombre=paciente_nombre,
                paciente_email=paciente_email,
                paciente_telefono=paciente_telefono,
                estado=estado_cita
            )
            
            # Si todo salió bien, devolver JSON para que el modal muestre el mensaje
            if estado_cita == 'reservada':
                mensaje = f'Cita creada y asignada a {paciente_nombre} para {dentista.nombre_completo}.'
            else:
                mensaje = f'Cita creada correctamente para {dentista.nombre_completo}.'
            
            return JsonResponse({'success': True, 'message': mensaje})
            
        except ValueError as e:
            return JsonResponse({'success': False, 'error': f'Error en el formato de fecha: {e}'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al agregar hora: {e}'}, status=400)

# Editar cita creada (solo administrativos)
# - Citas disponibles: se puede editar todo
# - Citas reservadas/confirmadas: se puede editar fecha/hora, dentista, servicio, precio (NO cliente)
# - Citas completadas: NO se pueden editar (usar ajustar_precio_cita)
@login_required
def editar_cita(request, cita_id):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para editar citas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    cita = get_object_or_404(Cita, id=cita_id)
    
    # Restricción: No se pueden editar citas completadas
    if cita.estado == 'completada':
        messages.error(request, 'Las citas completadas no se pueden editar. Use "Ajustar Precio" para modificar el precio o notas.')
        return redirect('panel_trabajador')
    
    # Para citas reservadas/confirmadas: solo permitir editar ciertos campos (no cliente)
    puede_editar_cliente = (cita.estado == 'disponible')

    if request.method == 'POST':
        fecha_hora_str = request.POST.get('fecha_hora')
        tipo_consulta = request.POST.get('tipo_consulta', '')
        tipo_servicio_id = request.POST.get('tipo_servicio', '')
        precio_cobrado = request.POST.get('precio_cobrado', '')
        notas = request.POST.get('notas', '')
        dentista_id = request.POST.get('dentista', '')
        
        try:
            fecha_hora = datetime.fromisoformat(fecha_hora_str)
            cita.fecha_hora = fecha_hora
            cita.tipo_consulta = tipo_consulta
            
            # Para citas reservadas/confirmadas: permitir cambiar dentista
            if dentista_id and cita.estado in ['reservada', 'confirmada']:
                try:
                    dentista = Perfil.objects.get(id=dentista_id, es_dentista=True, activo=True)
                    cita.dentista = dentista
                except Perfil.DoesNotExist:
                    pass
            
            # Actualizar tipo de servicio
            if tipo_servicio_id:
                try:
                    tipo_servicio = TipoServicio.objects.get(id=tipo_servicio_id, activo=True)
                    cita.tipo_servicio = tipo_servicio
                    # Si no se especifica precio manualmente, usar el precio base del servicio
                    if not precio_cobrado:
                        cita.precio_cobrado = tipo_servicio.precio_base
                    else:
                        try:
                            cita.precio_cobrado = float(precio_cobrado)
                        except ValueError:
                            cita.precio_cobrado = tipo_servicio.precio_base
                except TipoServicio.DoesNotExist:
                    messages.warning(request, 'El servicio seleccionado no existe o está inactivo.')
                    cita.tipo_servicio = None
            else:
                # Si se cambia el precio manualmente sin servicio
                if precio_cobrado:
                    try:
                        cita.precio_cobrado = float(precio_cobrado)
                    except ValueError:
                        pass
                elif cita.estado == 'disponible':
                    # Solo para citas disponibles se puede quitar servicio
                    cita.tipo_servicio = None
                    cita.precio_cobrado = None
            
            cita.notas = notas
            cita.save()
            
            mensaje = 'Cita actualizada correctamente.'
            if cita.estado in ['reservada', 'confirmada']:
                mensaje += ' Nota: El cliente no se puede modificar en citas reservadas.'
            messages.success(request, mensaje)
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'message': mensaje})
            
            return redirect('panel_trabajador')
        except Exception as e:
            messages.error(request, f'Error al actualizar la cita: {e}')
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'message': f'Error al actualizar la cita: {e}'}, status=400)

    # Obtener servicios activos para el selector
    servicios_activos = TipoServicio.objects.filter(activo=True).order_by('categoria', 'nombre')
    
    # Obtener dentistas para el selector (solo si es reservada/confirmada)
    dentistas = None
    if cita.estado in ['reservada', 'confirmada']:
        dentistas = Perfil.objects.filter(es_dentista=True, activo=True).order_by('nombre', 'apellido')
    
    context = {
        'perfil': perfil,
        'cita': cita,
        'servicios': servicios_activos,
        'dentistas': dentistas,
        'puede_editar_cliente': puede_editar_cliente,
    }
    return render(request, 'citas/editar_cita.html', context)


# Acciones sobre citas

@login_required
def cancelar_cita_admin(request, cita_id):
    try:
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        return redirect('login')
    
    cita = get_object_or_404(Cita, id=cita_id)
    
    # Verificar permisos: administrativos pueden cancelar cualquier cita, dentistas solo las suyas
    if perfil.es_dentista() and cita.dentista != perfil:
        messages.error(request, 'No tienes permisos para cancelar esta cita.')
        return redirect('mis_citas_dentista')
    elif not perfil.es_administrativo() and not perfil.es_dentista():
        messages.error(request, 'No tienes permisos para cancelar citas.')
        return redirect('panel_trabajador')
    
    if cita.cancelar():
        messages.success(request, f'Cita cancelada para {cita.fecha_hora}')
        # Redirigir según el rol
        if perfil.es_dentista():
            return redirect('mis_citas_dentista')
        else:
            return redirect('panel_trabajador')
    else:
        messages.error(request, 'No se pudo cancelar la cita')
        if perfil.es_dentista():
            return redirect('mis_citas_dentista')
        else:
            return redirect('panel_trabajador')

@login_required
def confirmar_cita(request, cita_id):
    """
    Vista para confirmar una cita (cambiar de 'reservada' a 'confirmada')
    SOLO DISPONIBLE PARA ADMINISTRATIVOS (recepcionistas)
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para confirmar citas. Solo el personal administrativo puede realizar esta acción.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'Perfil no encontrado.')
        return redirect('login')
    
    cita = get_object_or_404(Cita, id=cita_id)
    
    # Verificar que la cita esté en estado "reservada"
    if cita.estado != 'reservada':
        messages.error(request, f'Esta cita está en estado "{cita.get_estado_display()}" y no puede ser confirmada.')
        return redirect('panel_trabajador')
    
    # Cambiar a estado confirmada
    cita.estado = 'confirmada'
    cita.save()
    
    messages.success(request, f'✅ Cita del {cita.fecha_hora.strftime("%d/%m/%Y a las %H:%M")} confirmada exitosamente.')
    return redirect('panel_trabajador')


@login_required
def completar_cita(request, cita_id):
    """
    Vista para marcar una cita como completada
    SOLO DISPONIBLE PARA ADMINISTRATIVOS (recepcionistas)
    Los dentistas NO pueden completar sus propias citas
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para completar citas. Solo el personal administrativo puede realizar esta acción.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'Perfil no encontrado.')
        return redirect('login')
    
    # Cargar la cita con el tipo_servicio relacionado para acceder al precio_base
    cita = get_object_or_404(Cita.objects.select_related('tipo_servicio', 'cliente', 'dentista'), id=cita_id)
    
    # Verificar que la cita esté en estado "confirmada" o "reservada"
    if cita.estado not in ['confirmada', 'reservada']:
        messages.error(request, f'Esta cita está en estado "{cita.get_estado_display()}" y no puede ser completada.')
        return redirect('panel_trabajador')
    
    # VALIDACIÓN CRÍTICA 1: Verificar que la cita no sea futura
    from django.utils import timezone
    ahora = timezone.now()
    if cita.fecha_hora > ahora:
        tiempo_faltante = cita.fecha_hora - ahora
        horas_faltantes = int(tiempo_faltante.total_seconds() / 3600)
        messages.error(
            request,
            f'⚠️ No se puede completar una cita futura. '
            f'Esta cita está programada para el {cita.fecha_hora.strftime("%d/%m/%Y a las %H:%M")} '
            f'(faltan aproximadamente {horas_faltantes} horas). '
            f'Solo se pueden completar citas que ya han ocurrido.'
        )
        return redirect('panel_trabajador')
    
    # VALIDACIÓN CRÍTICA 2: Verificar si la cita tiene ficha odontológica creada
    from historial_clinico.models import Odontograma
    tiene_ficha = Odontograma.objects.filter(cita=cita).exists()
    odontograma = None
    ficha_completa = False
    
    if tiene_ficha:
        odontograma = Odontograma.objects.filter(cita=cita).first()
        # Verificar que la ficha tenga los campos mínimos requeridos
        if odontograma:
            ficha_completa = (
                odontograma.paciente_nombre and
                odontograma.motivo_consulta and
                odontograma.dentista
            )
    
    # Si es POST, validar y actualizar
    if request.method == 'POST':
        # Validar que tenga ficha antes de completar
        if not tiene_ficha:
            messages.error(
                request, 
                '⚠️ No se puede completar la cita sin crear la ficha odontológica. '
                'Por favor, asegúrate de que el dentista haya creado la ficha antes de marcar la cita como completada.'
            )
            return redirect('completar_cita', cita_id=cita_id)
        
        # Validar que la ficha esté completa
        if tiene_ficha and not ficha_completa:
            messages.error(
                request,
                '⚠️ La ficha odontológica existe pero está incompleta. '
                'Por favor, asegúrate de que la ficha tenga al menos: nombre del paciente, motivo de consulta y dentista asignado.'
            )
            return redirect('completar_cita', cita_id=cita_id)
        precio_cobrado = request.POST.get('precio_cobrado', '')
        precio_servicio_base = request.POST.get('precio_servicio_base', '')
        
        # Si hay precio_servicio_base (campo oculto), usarlo si no se proporcionó precio_cobrado
        if not precio_cobrado and precio_servicio_base:
            try:
                precio = float(precio_servicio_base)
                if precio >= 0:
                    cita.precio_cobrado = precio
            except ValueError:
                pass
        
        # Si se proporcionó precio_cobrado, usarlo (puede ser un ajuste)
        if precio_cobrado:
            try:
                precio = float(precio_cobrado)
                if precio >= 0:
                    cita.precio_cobrado = precio
                else:
                    messages.error(request, 'El precio debe ser un valor positivo.')
                    return redirect('completar_cita', cita_id=cita_id)
            except ValueError:
                # Si no es válido, usar el precio del servicio
                if cita.tipo_servicio and cita.tipo_servicio.precio_base:
                    cita.precio_cobrado = cita.tipo_servicio.precio_base
                else:
                    messages.error(request, 'El precio ingresado no es válido. Por favor, ingrese un número válido.')
                    return redirect('completar_cita', cita_id=cita_id)
        
        # VALIDACIÓN CRÍTICA 3: Validar que el precio esté asignado
        # Si aún no hay precio pero hay tipo_servicio, usar el precio_base
        if not cita.precio_cobrado and cita.tipo_servicio and cita.tipo_servicio.precio_base:
            cita.precio_cobrado = cita.tipo_servicio.precio_base
        
        # Validación final: el precio es obligatorio
        if not cita.precio_cobrado or cita.precio_cobrado <= 0:
            messages.error(
                request, 
                '⚠️ Debe asignar un precio válido (mayor a 0) para completar la cita. '
                'Si el servicio no tiene precio base, debe ingresarlo manualmente.'
            )
            return redirect('completar_cita', cita_id=cita_id)
        
        # Todas las validaciones pasaron, marcar como completada
        if cita.completar():
            mensaje = f'✅ Cita del {cita.fecha_hora.strftime("%d/%m/%Y a las %H:%M")} marcada como completada exitosamente.'
            if cita.precio_cobrado:
                mensaje += f' Precio a cobrar: ${cita.precio_cobrado:,.0f}'
            messages.success(request, mensaje)
            return redirect('panel_trabajador')
        else:
            messages.error(request, 'No se pudo completar la cita. Intenta nuevamente.')
            return redirect('panel_trabajador')
    
    # Si es GET, mostrar formulario de confirmación con precio
    # Calcular validaciones para mostrar en el template
    validaciones = {
        'fecha_valida': cita.fecha_hora <= ahora,
        'tiene_ficha': tiene_ficha,
        'ficha_completa': ficha_completa,
        'tiene_precio': False,  # Se calculará después
        'puede_completar': False,  # Se calculará después
    }
    
    # Verificar si tiene precio (actual o del servicio)
    tiene_precio_actual = cita.precio_cobrado and cita.precio_cobrado > 0
    tiene_precio_servicio = (cita.tipo_servicio and 
                            cita.tipo_servicio.precio_base and 
                            cita.tipo_servicio.precio_base > 0)
    validaciones['tiene_precio'] = tiene_precio_actual or tiene_precio_servicio
    
    # Determinar si puede completar (todas las validaciones deben pasar)
    validaciones['puede_completar'] = (
        validaciones['fecha_valida'] and
        validaciones['tiene_ficha'] and
        validaciones['ficha_completa'] and
        validaciones['tiene_precio']
    )
    
    # Asegurar que el tipo_servicio se cargue correctamente
    # SIEMPRE recargar el tipo_servicio directamente desde la base de datos para obtener el precio actualizado
    from citas.models import TipoServicio
    precio_servicio = None
    tipo_servicio_encontrado = None
    
    # Primero intentar cargar por tipo_servicio_id
    if cita.tipo_servicio_id:
        try:
            tipo_servicio_obj = TipoServicio.objects.get(id=cita.tipo_servicio_id)
            cita.tipo_servicio = tipo_servicio_obj
            tipo_servicio_encontrado = tipo_servicio_obj
            
            if tipo_servicio_obj.precio_base is not None:
                try:
                    precio_servicio = float(tipo_servicio_obj.precio_base)
                except (ValueError, TypeError):
                    precio_servicio = tipo_servicio_obj.precio_base
        except TipoServicio.DoesNotExist:
            cita.tipo_servicio = None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al cargar tipo_servicio {cita.tipo_servicio_id}: {e}")
    
    # Si no se encontró por ID pero hay tipo_consulta, intentar buscar por nombre
    if not tipo_servicio_encontrado and cita.tipo_consulta:
        try:
            # Buscar servicio por nombre (case-insensitive, sin espacios)
            nombre_buscar = cita.tipo_consulta.strip()
            tipo_servicio_obj = TipoServicio.objects.filter(
                nombre__iexact=nombre_buscar,
                activo=True
            ).first()
            
            if tipo_servicio_obj:
                cita.tipo_servicio = tipo_servicio_obj
                tipo_servicio_encontrado = tipo_servicio_obj
                
                if tipo_servicio_obj.precio_base is not None:
                    try:
                        precio_servicio = float(tipo_servicio_obj.precio_base)
                    except (ValueError, TypeError):
                        precio_servicio = tipo_servicio_obj.precio_base
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error al buscar servicio por nombre '{cita.tipo_consulta}': {e}")
    
    # Si aún no se encontró, intentar búsqueda parcial
    if not tipo_servicio_encontrado and cita.tipo_consulta:
        try:
            nombre_buscar = cita.tipo_consulta.strip()
            # Buscar servicios que contengan el nombre (case-insensitive)
            tipo_servicio_obj = TipoServicio.objects.filter(
                nombre__icontains=nombre_buscar,
                activo=True
            ).first()
            
            if tipo_servicio_obj:
                cita.tipo_servicio = tipo_servicio_obj
                tipo_servicio_encontrado = tipo_servicio_obj
                
                if tipo_servicio_obj.precio_base is not None:
                    try:
                        precio_servicio = float(tipo_servicio_obj.precio_base)
                    except (ValueError, TypeError):
                        precio_servicio = tipo_servicio_obj.precio_base
        except Exception:
            pass
    
    context = {
        'perfil': perfil,
        'cita': cita,
        'tiene_ficha': tiene_ficha,
        'ficha_completa': ficha_completa,
        'odontograma': odontograma,
        'precio_servicio': precio_servicio,  # Pasar el precio directamente al template
        'validaciones': validaciones,  # Pasar validaciones al template
        'ahora': ahora,  # Para mostrar en el template si es necesario
    }
    return render(request, 'citas/completar_cita.html', context)


# Ajustar precio de cita completada (solo administrativos)
# Solo permite ajustar precio y notas, nada más
@login_required
def ajustar_precio_cita(request, cita_id):
    """
    Vista para ajustar precio y notas de una cita completada
    SOLO DISPONIBLE PARA ADMINISTRATIVOS (recepcionistas)
    Solo permite modificar precio y notas, nada más
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ajustar precios de citas. Solo el personal administrativo puede realizar esta acción.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'Perfil no encontrado.')
        return redirect('login')
    
    cita = get_object_or_404(Cita, id=cita_id)
    
    # Restricción: Solo citas completadas pueden ajustar precio
    if cita.estado != 'completada':
        messages.error(request, 'Solo se puede ajustar el precio de citas completadas. Para editar otros campos, use "Editar Cita".')
        return redirect('panel_trabajador')
    
    if request.method == 'POST':
        precio_cobrado = request.POST.get('precio_cobrado', '')
        notas = request.POST.get('notas', '')
        
        # Actualizar precio si se proporciona
        if precio_cobrado:
            try:
                precio = float(precio_cobrado)
                if precio >= 0:
                    cita.precio_cobrado = precio
                else:
                    messages.error(request, 'El precio debe ser un valor positivo.')
            except ValueError:
                messages.error(request, 'El precio ingresado no es válido.')
        else:
            # Si se envía vacío, mantener el precio actual o usar el del servicio
            if not cita.precio_cobrado and cita.tipo_servicio:
                cita.precio_cobrado = cita.tipo_servicio.precio_base
        
        # Actualizar notas
        cita.notas = notas
        cita.save()
        
        mensaje = f'✅ Precio y notas de la cita del {cita.fecha_hora.strftime("%d/%m/%Y a las %H:%M")} actualizados correctamente.'
        if cita.precio_cobrado:
            mensaje += f' Precio a cobrar: ${cita.precio_cobrado:,.0f}'
        messages.success(request, mensaje)
        return redirect('panel_trabajador')
    
    # Si es GET, mostrar formulario de ajuste
    # Asegurar que el tipo_servicio se cargue correctamente
    if cita.tipo_servicio_id:
        try:
            from citas.models import TipoServicio
            tipo_servicio_obj = TipoServicio.objects.get(id=cita.tipo_servicio_id)
            cita.tipo_servicio = tipo_servicio_obj
        except TipoServicio.DoesNotExist:
            pass
    
    context = {
        'perfil': perfil,
        'cita': cita,
    }
    return render(request, 'citas/ajustar_precio_cita.html', context)


# Eliminar cita (solo administrativos)
@login_required
def eliminar_cita(request, cita_id):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar citas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    cita = get_object_or_404(Cita, id=cita_id)
    fecha_texto = cita.fecha_hora
    try:
        cita.delete()
        messages.success(request, f'Cita eliminada: {fecha_texto}')
    except Exception as e:
        messages.error(request, f'No se pudo eliminar la cita: {e}')

    # Volver al panel del trabajador para ver los cambios
    return redirect('panel_trabajador')

# Listado de citas tomadas (reservadas o confirmadas) - solo administrativos
@login_required
def citas_tomadas(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver este listado.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    citas_list = Cita.objects.filter(estado__in=['reservada', 'confirmada']).order_by('fecha_hora')
    
    # Paginación - 10 registros por página
    paginator = Paginator(citas_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        citas = paginator.page(page)
    except PageNotAnInteger:
        citas = paginator.page(1)
    except EmptyPage:
        citas = paginator.page(paginator.num_pages)

    context = {
        'perfil': perfil,
        'citas': citas,
    }
    return render(request, 'citas/citas_tomadas.html', context)

# Listado de citas completadas - solo administrativos
@login_required
def citas_completadas(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver este listado.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    citas_list = Cita.objects.filter(estado='completada').order_by('-fecha_hora')
    
    # Paginación - 10 registros por página
    paginator = Paginator(citas_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        citas = paginator.page(page)
    except PageNotAnInteger:
        citas = paginator.page(1)
    except EmptyPage:
        citas = paginator.page(paginator.num_pages)

    context = {
        'perfil': perfil,
        'citas': citas,
    }
    return render(request, 'citas/citas_completadas.html', context)

# Registrar nuevo trabajador
def registro_trabajador(request):
    if request.method == 'POST':
        form = RegistroTrabajadorForm(request.POST)
        
        if not form.is_valid():
            # Validaciones personalizadas con mensajes específicos
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            
            # Limpiar mensajes anteriores
            storage = messages.get_messages(request)
            storage.used = True
            
            # Verificar si el usuario ya existe
            if username:
                if User.objects.filter(username=username).exists():
                    messages.error(request, '❌ Este usuario ya existe. Por favor, elige otro nombre de usuario.')
                elif len(username) < 3:
                    messages.error(request, '❌ El nombre de usuario debe tener al menos 3 caracteres.')
            
            # Verificar si el email ya existe
            if email:
                if User.objects.filter(email=email).exists():
                    messages.error(request, '❌ Este email ya está registrado. Por favor, usa otro email.')
                elif '@' not in email:
                    messages.error(request, '❌ Por favor, ingresa un email válido.')
            
            # Verificar contraseñas
            if password1 and password2:
                if password1 != password2:
                    messages.error(request, '❌ Las contraseñas no coinciden. Por favor, verifica que ambas sean iguales.')
                elif len(password1) < 8:
                    messages.error(request, '❌ La contraseña debe tener al menos 8 caracteres.')
            elif not password1:
                messages.error(request, '❌ Por favor, ingresa una contraseña.')
            elif not password2:
                messages.error(request, '❌ Por favor, confirma tu contraseña.')
            
            # Verificar campos requeridos
            if not request.POST.get('first_name', '').strip():
                messages.error(request, '❌ Por favor, ingresa tu nombre.')
            if not request.POST.get('last_name', '').strip():
                messages.error(request, '❌ Por favor, ingresa tu apellido.')
            if not request.POST.get('nombre_completo', '').strip():
                messages.error(request, '❌ Por favor, ingresa tu nombre completo.')
            if not request.POST.get('telefono', '').strip():
                messages.error(request, '❌ Por favor, ingresa tu teléfono.')
            if not request.POST.get('rol', ''):
                messages.error(request, '❌ Por favor, selecciona un rol.')
            
            # Mostrar otros errores del formulario si no se capturaron arriba
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        if 'username' in field.lower() and 'already exists' in error.lower():
                            continue  # Ya lo manejamos arriba
                        elif 'email' in field.lower() and 'already exists' in error.lower():
                            continue  # Ya lo manejamos arriba
                        else:
                            messages.error(request, f'❌ {error}')
        else:
            # Formulario válido, intentar guardar
            try:
                user = form.save()
                print(f"DEBUG - Usuario creado: {user.username}")
                messages.success(request, '✅ Trabajador registrado correctamente. Ya puedes iniciar sesión.')
                return redirect('login')
            except Exception as e:
                print(f"DEBUG - Error al crear usuario: {e}")
                if 'username' in str(e).lower() and 'already exists' in str(e).lower():
                    messages.error(request, '❌ Este usuario ya existe. Por favor, elige otro nombre de usuario.')
                elif 'email' in str(e).lower() and 'already exists' in str(e).lower():
                    messages.error(request, '❌ Este email ya está registrado. Por favor, usa otro email.')
                else:
                    messages.error(request, f'❌ Error al registrar trabajador: {str(e)}')
    else:
        form = RegistroTrabajadorForm()
    
    return render(request, 'citas/registro_trabajador.html', {'form': form})

# Editar perfil
@login_required
def editar_perfil(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes un perfil de trabajador válido.')
        return redirect('login')
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('panel_trabajador')
    else:
        form = PerfilForm(instance=perfil)
    
    return render(request, 'citas/editar_perfil.html', {'form': form, 'perfil': perfil})

# Dashboard con estadísticas
@login_required
def dashboard(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.activo:
            messages.error(request, 'Tu cuenta está desactivada.')
            return redirect('login')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Estadísticas generales
    hoy = timezone.now().date()
    semana_actual = hoy - timedelta(days=7)
    mes_actual = hoy - timedelta(days=30)
    
    if perfil.es_administrativo():
        # Estadísticas para administrativos
        estadisticas = {
            'citas_hoy': Cita.objects.filter(fecha_hora__date=hoy).count(),
            'citas_semana': Cita.objects.filter(fecha_hora__date__gte=semana_actual).count(),
            'citas_mes': Cita.objects.filter(fecha_hora__date__gte=mes_actual).count(),
            'citas_disponibles': Cita.objects.filter(estado='disponible').count(),
            'citas_reservadas': Cita.objects.filter(estado='reservada').count(),
            'citas_confirmadas': Cita.objects.filter(estado='confirmada').count(),
            'citas_completadas': Cita.objects.filter(estado='completada').count(),
        }
        
        # Citas por estado (últimos 7 días)
        citas_por_estado = Cita.objects.filter(
            fecha_hora__date__gte=semana_actual
        ).values('estado').annotate(total=Count('estado'))
        
    else:
        # Estadísticas para dentistas
        estadisticas = {
            'citas_hoy': Cita.objects.filter(fecha_hora__date=hoy, dentista=perfil).count(),
            'citas_semana': Cita.objects.filter(fecha_hora__date__gte=semana_actual, dentista=perfil).count(),
            'citas_mes': Cita.objects.filter(fecha_hora__date__gte=mes_actual, dentista=perfil).count(),
            'citas_pendientes': Cita.objects.filter(dentista=perfil, estado='reservada').count(),
            'citas_confirmadas': Cita.objects.filter(dentista=perfil, estado='confirmada').count(),
            'citas_completadas': Cita.objects.filter(dentista=perfil, estado='completada').count(),
        }
        
        # Citas por estado para el dentista (últimos 7 días)
        citas_por_estado = Cita.objects.filter(
            fecha_hora__date__gte=semana_actual,
            dentista=perfil
        ).values('estado').annotate(total=Count('estado'))
    
    context = {
        'perfil': perfil,
        'estadisticas': estadisticas,
        'citas_por_estado': citas_por_estado,
        'es_admin': perfil.es_administrativo()
    }
    
    return render(request, 'citas/dashboard.html', context)

# Vista de diagnóstico - Todas las citas (solo administrativos)
@login_required
def todas_las_citas(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver todas las citas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    # Obtener todas las citas sin filtros, incluyendo información de odontogramas vinculados
    todas_citas_list = Cita.objects.all().select_related('dentista', 'cliente').prefetch_related('odontogramas').order_by('fecha_hora')
    
    # Paginación - 10 registros por página
    paginator = Paginator(todas_citas_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        todas_citas = paginator.page(page)
    except PageNotAnInteger:
        todas_citas = paginator.page(1)
    except EmptyPage:
        todas_citas = paginator.page(paginator.num_pages)
    
    # Agrupar por estado para diagnóstico (usar la lista completa para estadísticas)
    citas_por_estado = {}
    for cita in todas_citas_list:
        estado = cita.estado
        if estado not in citas_por_estado:
            citas_por_estado[estado] = []
        citas_por_estado[estado].append(cita)
    
    context = {
        'perfil': perfil,
        'todas_citas': todas_citas,
        'citas_por_estado': citas_por_estado,
        'total_citas': todas_citas_list.count(),
        'estados_disponibles': Cita.ESTADO_CHOICES
    }
    
    return render(request, 'citas/todas_las_citas.html', context)

# Gestor de Clientes - solo administrativos
@login_required
def gestor_clientes(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar clientes.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    # Filtros de búsqueda
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    
    # Obtener clientes desde el modelo Cliente
    clientes_query = Cliente.objects.all()
    
    # Aplicar filtros de búsqueda
    if search:
        from django.db.models import Q
        clientes_query = clientes_query.filter(
            Q(nombre_completo__icontains=search) |
            Q(email__icontains=search) |
            Q(telefono__icontains=search) |
            Q(rut__icontains=search)  # Búsqueda por RUT
        )
    
    # Aplicar filtro de estado
    if estado == 'activo':
        clientes_query = clientes_query.filter(activo=True)
    elif estado == 'inactivo':
        clientes_query = clientes_query.filter(activo=False)
    
    # Anotar cada cliente con el número de citas que tiene
    from django.db.models import Count
    try:
        # Intentar anotar con todas las relaciones
        clientes_query = clientes_query.annotate(
            total_citas=Count('citas', distinct=True)
        )
        # Intentar agregar odontogramas y radiografias si las relaciones existen
        try:
            clientes_query = clientes_query.annotate(
                total_odontogramas=Count('odontogramas', distinct=True),
                total_radiografias=Count('radiografias', distinct=True)
            )
        except:
            # Si falla, solo usar total_citas
            pass
    except Exception as e:
        # Si hay error con las anotaciones, usar consulta sin anotaciones
        pass
    
    # Ordenar por nombre
    clientes_list = clientes_query.order_by('nombre_completo')
    
    # Paginación - 10 registros por página
    paginator = Paginator(clientes_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        clientes = paginator.page(page)
    except PageNotAnInteger:
        clientes = paginator.page(1)
    except EmptyPage:
        clientes = paginator.page(paginator.num_pages)
    
    # Estadísticas
    total_clientes = Cliente.objects.count()
    clientes_con_citas_count = Cliente.objects.filter(citas__isnull=False).distinct().count()
    
    estadisticas = {
        'total_clientes': total_clientes,
        'clientes_con_citas': clientes_con_citas_count,
    }
    
    # Debug: verificar que tenemos clientes
    # Si no hay clientes en la página pero hay en total, podría ser un problema de paginación
    total_en_query = clientes_list.count() if hasattr(clientes_list, 'count') else len(list(clientes_list))
    
    context = {
        'perfil': perfil,
        'clientes': clientes,
        'estadisticas': estadisticas,
        'search': search,
        'estado': estado,
        'es_admin': True,
        'total_en_query': total_en_query,  # Para debug
    }
    
    return render(request, 'citas/gestor_clientes.html', context)

# Gestor de Insumos - solo administrativos
@login_required
def gestor_insumos(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar insumos.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    # Filtros de búsqueda
    search = request.GET.get('search', '')
    categoria = request.GET.get('categoria', '')
    estado = request.GET.get('estado', '')
    
    insumos = Insumo.objects.all()
    
    if search:
        insumos = insumos.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(proveedor__icontains=search) |
            Q(ubicacion__icontains=search)
        )
    
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    if estado:
        insumos = insumos.filter(estado=estado)
    
    insumos_list = insumos.order_by('nombre')
    
    # Paginación - 10 registros por página
    paginator = Paginator(insumos_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        insumos = paginator.page(page)
    except PageNotAnInteger:
        insumos = paginator.page(1)
    except EmptyPage:
        insumos = paginator.page(paginator.num_pages)
    
    # Estadísticas de insumos
    total_insumos = Insumo.objects.count()
    insumos_stock_bajo = Insumo.objects.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    insumos_proximo_vencimiento = Insumo.objects.filter(
        fecha_vencimiento__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento__gte=timezone.now().date()
    ).count()
    insumos_agotados = Insumo.objects.filter(estado='agotado').count()
    
    estadisticas = {
        'total_insumos': total_insumos,
        'insumos_stock_bajo': insumos_stock_bajo,
        'insumos_proximo_vencimiento': insumos_proximo_vencimiento,
        'insumos_agotados': insumos_agotados,
    }
    
    context = {
        'perfil': perfil,
        'insumos': insumos,
        'estadisticas': estadisticas,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'estados': Insumo.ESTADO_CHOICES,
        'search': search,
        'categoria': categoria,
        'estado': estado,
        'es_admin': True
    }
    
    return render(request, 'citas/gestor_insumos.html', context)

# Agregar nuevo insumo
@login_required
def agregar_insumo(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para agregar insumos.')
            return redirect('gestor_insumos')
    except Perfil.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        categoria = request.POST.get('categoria', '')
        descripcion = request.POST.get('descripcion', '').strip()
        cantidad_actual_str = request.POST.get('cantidad_actual', '0')
        cantidad_minima_str = request.POST.get('cantidad_minima', '1')
        unidad_medida = request.POST.get('unidad_medida', 'unidad')
        precio_unitario_str = request.POST.get('precio_unitario', '')
        proveedor = request.POST.get('proveedor', '').strip()
        fecha_vencimiento = request.POST.get('fecha_vencimiento', '')
        ubicacion = request.POST.get('ubicacion', '').strip()
        notas = request.POST.get('notas', '').strip()
        
        # Validaciones
        errores = []
        
        if not nombre:
            errores.append('El nombre del insumo es obligatorio.')
        
        if not categoria:
            errores.append('La categoría es obligatoria.')
        
        try:
            cantidad_actual = int(cantidad_actual_str)
            if cantidad_actual < 0:
                errores.append('La cantidad actual no puede ser negativa.')
        except ValueError:
            errores.append('La cantidad actual debe ser un número válido.')
        
        try:
            cantidad_minima = int(cantidad_minima_str)
            if cantidad_minima < 1:
                errores.append('La cantidad mínima debe ser al menos 1.')
        except ValueError:
            errores.append('La cantidad mínima debe ser un número válido.')
        
        if cantidad_actual < cantidad_minima:
            errores.append('La cantidad actual no puede ser menor que la cantidad mínima.')
        
        precio_unitario = None
        if precio_unitario_str:
            try:
                precio_unitario = round(float(precio_unitario_str))  # Redondear a entero para pesos chilenos
                if precio_unitario < 0:
                    errores.append('El precio unitario no puede ser negativo.')
            except ValueError:
                errores.append('El precio unitario debe ser un número válido.')
        
        # Validar fecha de vencimiento
        fecha_vencimiento_obj = None
        if fecha_vencimiento:
            try:
                from datetime import datetime
                fecha_vencimiento_obj = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
                if fecha_vencimiento_obj < timezone.now().date():
                    errores.append('La fecha de vencimiento no puede ser anterior a hoy.')
            except ValueError:
                errores.append('La fecha de vencimiento debe tener un formato válido.')
        
        # Verificar si ya existe un insumo con el mismo nombre
        if Insumo.objects.filter(nombre__iexact=nombre).exists():
            errores.append('Ya existe un insumo con este nombre.')
        
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            try:
                insumo = Insumo.objects.create(
                    nombre=nombre,
                    categoria=categoria,
                    descripcion=descripcion,
                    cantidad_actual=cantidad_actual,
                    cantidad_minima=cantidad_minima,
                    unidad_medida=unidad_medida,
                    precio_unitario=precio_unitario,
                    proveedor=proveedor,
                    fecha_vencimiento=fecha_vencimiento_obj,
                    ubicacion=ubicacion,
                    notas=notas,
                    creado_por=perfil
                )
                
                # Crear movimiento inicial
                MovimientoInsumo.objects.create(
                    insumo=insumo,
                    tipo='entrada',
                    cantidad=cantidad_actual,
                    cantidad_anterior=0,
                    cantidad_nueva=cantidad_actual,
                    motivo='Stock inicial',
                    realizado_por=perfil
                )
                
                messages.success(request, f'Insumo "{nombre}" agregado correctamente.')
                return redirect('gestor_insumos')
            except Exception as e:
                messages.error(request, f'Error al agregar insumo: {str(e)}')
    
    context = {
        'perfil': perfil,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'es_admin': True,
        'form_data': request.POST if request.method == 'POST' else {}
    }
    
    return render(request, 'citas/agregar_insumo.html', context)

# Editar insumo
@login_required
def editar_insumo(request, insumo_id):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para editar insumos.')
            return redirect('gestor_insumos')
    except Perfil.DoesNotExist:
        return redirect('login')

    insumo = get_object_or_404(Insumo, id=insumo_id)
    
    if request.method == 'POST':
        insumo.nombre = request.POST.get('nombre')
        insumo.categoria = request.POST.get('categoria')
        insumo.descripcion = request.POST.get('descripcion', '')
        insumo.cantidad_minima = int(request.POST.get('cantidad_minima', 1))
        insumo.unidad_medida = request.POST.get('unidad_medida', 'unidad')
        precio_unitario_str = request.POST.get('precio_unitario')
        if precio_unitario_str:
            try:
                insumo.precio_unitario = round(float(precio_unitario_str))  # Redondear a entero para pesos chilenos
            except (ValueError, TypeError):
                insumo.precio_unitario = None
        else:
            insumo.precio_unitario = None
        insumo.proveedor = request.POST.get('proveedor', '')
        insumo.fecha_vencimiento = request.POST.get('fecha_vencimiento')
        insumo.ubicacion = request.POST.get('ubicacion', '')
        insumo.notas = request.POST.get('notas', '')
        
        try:
            insumo.save()
            messages.success(request, f'Insumo "{insumo.nombre}" actualizado correctamente.')
            return redirect('gestor_insumos')
        except Exception as e:
            messages.error(request, f'Error al actualizar insumo: {e}')
    
    context = {
        'perfil': perfil,
        'insumo': insumo,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'es_admin': True
    }
    
    return render(request, 'citas/editar_insumo.html', context)

# Movimiento de stock
@login_required
def movimiento_insumo(request, insumo_id):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para realizar movimientos de stock.')
            return redirect('gestor_insumos')
    except Perfil.DoesNotExist:
        return redirect('login')

    insumo = get_object_or_404(Insumo, id=insumo_id)
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', '')
        observaciones = request.POST.get('observaciones', '')
        
        if cantidad <= 0:
            messages.error(request, 'La cantidad debe ser mayor a 0.')
            return redirect('gestor_insumos')
        
        cantidad_anterior = insumo.cantidad_actual
        
        try:
            if tipo == 'entrada':
                insumo.cantidad_actual += cantidad
            elif tipo == 'salida':
                if cantidad > insumo.cantidad_actual:
                    messages.error(request, 'No hay suficiente stock disponible.')
                    return redirect('gestor_insumos')
                insumo.cantidad_actual -= cantidad
            elif tipo == 'ajuste':
                insumo.cantidad_actual = cantidad
            
            insumo.save()
            
            # Crear movimiento
            MovimientoInsumo.objects.create(
                insumo=insumo,
                tipo=tipo,
                cantidad=cantidad,
                cantidad_anterior=cantidad_anterior,
                cantidad_nueva=insumo.cantidad_actual,
                motivo=motivo,
                observaciones=observaciones,
                realizado_por=perfil
            )
            
            messages.success(request, f'Movimiento de stock realizado correctamente.')
            return redirect('gestor_insumos')
        except Exception as e:
            messages.error(request, f'Error al realizar movimiento: {e}')
    
    context = {
        'perfil': perfil,
        'insumo': insumo,
        'tipos_movimiento': MovimientoInsumo.TIPO_CHOICES,
        'es_admin': True
    }
    
    return render(request, 'citas/movimiento_insumo.html', context)

# Historial de movimientos
@login_required
def historial_movimientos(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para ver el historial de movimientos.')
            return redirect('gestor_insumos')
    except Perfil.DoesNotExist:
        return redirect('login')

    movimientos = MovimientoInsumo.objects.all().order_by('-fecha_movimiento')
    
    # Filtros
    insumo_id = request.GET.get('insumo')
    tipo = request.GET.get('tipo')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if insumo_id:
        movimientos = movimientos.filter(insumo_id=insumo_id)
    if tipo:
        movimientos = movimientos.filter(tipo=tipo)
    if fecha_desde:
        movimientos = movimientos.filter(fecha_movimiento__date__gte=fecha_desde)
    if fecha_hasta:
        movimientos = movimientos.filter(fecha_movimiento__date__lte=fecha_hasta)
    
    context = {
        'perfil': perfil,
        'movimientos': movimientos,
        'insumos': Insumo.objects.all().order_by('nombre'),
        'tipos_movimiento': MovimientoInsumo.TIPO_CHOICES,
        'insumo_actual': insumo_id,
        'tipo_actual': tipo,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'es_admin': True
    }
    
    return render(request, 'citas/historial_movimientos.html', context)

# Gestión de Personal - solo administrativos
@login_required
def gestor_personal(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para gestionar personal.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    # Filtros de búsqueda
    search = request.GET.get('search', '')
    rol = request.GET.get('rol', '')
    estado = request.GET.get('estado', '')
    
    personal = Perfil.objects.all()
    
    if search:
        personal = personal.filter(
            Q(nombre_completo__icontains=search) |
            Q(email__icontains=search) |
            Q(telefono__icontains=search) |
            Q(user__username__icontains=search) |
            Q(especialidad__icontains=search)
        )
    
    if rol:
        personal = personal.filter(rol=rol)
    
    if estado == 'activo':
        personal = personal.filter(activo=True)
    elif estado == 'inactivo':
        personal = personal.filter(activo=False)
    
    personal = personal.order_by('nombre_completo')
    
    # Estadísticas de personal
    total_personal = Perfil.objects.count()
    dentistas_count = Perfil.objects.filter(rol='dentista', activo=True).count()
    administrativos_count = Perfil.objects.filter(rol='administrativo', activo=True).count()
    personal_inactivo = Perfil.objects.filter(activo=False).count()
    
    # Estadísticas adicionales
    from datetime import datetime, timedelta
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    nuevos_este_mes = Perfil.objects.filter(fecha_registro__gte=inicio_mes).count()
    
    # Calcular porcentajes
    dentistas_porcentaje = round((dentistas_count / total_personal * 100) if total_personal > 0 else 0, 1)
    administrativos_porcentaje = round((administrativos_count / total_personal * 100) if total_personal > 0 else 0, 1)

    estadisticas = {
        'total_personal': total_personal,
        'dentistas': dentistas_count,
        'administrativos': administrativos_count,
        'inactivos': personal_inactivo,
        'nuevos_este_mes': nuevos_este_mes,
        'dentistas_porcentaje': dentistas_porcentaje,
        'administrativos_porcentaje': administrativos_porcentaje,
    }
    
    context = {
        'perfil': perfil,
        'personal': personal,
        'estadisticas': estadisticas,
        'roles': Perfil.ROLE_CHOICES,
        'search': search,
        'rol': rol,
        'estado': estado,
        'es_admin': True
    }
    
    return render(request, 'citas/gestor_personal.html', context)

# Agregar nuevo personal
@login_required
def agregar_personal(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para agregar personal.')
            return redirect('gestor_personal')
    except Perfil.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        rol = request.POST.get('rol', '')
        especialidad = request.POST.get('especialidad', '').strip()
        numero_colegio = request.POST.get('numero_colegio', '').strip()
        requiere_acceso = request.POST.get('requiere_acceso_sistema') == 'on'
        foto = request.FILES.get('foto')
        
        # Validaciones
        errores = []
        
        # Solo validar usuario y contraseña si requiere acceso al sistema
        if requiere_acceso:
            if not username:
                errores.append('El nombre de usuario es obligatorio para personal con acceso al sistema.')
            elif User.objects.filter(username=username).exists():
                errores.append('Ya existe un usuario con este nombre de usuario.')
            
            if not password:
                errores.append('La contraseña es obligatoria para personal con acceso al sistema.')
            elif len(password) < 8:
                errores.append('La contraseña debe tener al menos 8 caracteres.')
            
            if User.objects.filter(email=email).exists():
                errores.append('Ya existe un usuario con este email.')
        
        if not nombre_completo:
            errores.append('El nombre completo es obligatorio.')
        
        if not email:
            errores.append('El email es obligatorio.')
        
        if not telefono:
            errores.append('El teléfono es obligatorio.')
        
        if not rol:
            errores.append('El rol es obligatorio.')
        
        # Validaciones específicas para dentistas
        if rol == 'dentista':
            if not especialidad:
                errores.append('La especialidad es obligatoria para dentistas.')
            if not numero_colegio:
                errores.append('El número de colegio es obligatorio para dentistas.')
        
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            try:
                user = None
                # Solo crear usuario si requiere acceso al sistema
                if requiere_acceso:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=nombre_completo.split()[0] if nombre_completo.split() else '',
                        last_name=' '.join(nombre_completo.split()[1:]) if len(nombre_completo.split()) > 1 else ''
                    )
                
                # Crear perfil
                perfil_nuevo = Perfil.objects.create(
                    user=user,
                    nombre_completo=nombre_completo,
                    telefono=telefono,
                    email=email,
                    rol=rol,
                    especialidad=especialidad if rol == 'dentista' else '',
                    numero_colegio=numero_colegio if rol == 'dentista' else '',
                    requiere_acceso_sistema=requiere_acceso,
                    foto=foto if foto else None
                )
                
                tipo_personal = "con acceso al sistema" if requiere_acceso else "sin acceso al sistema"
                messages.success(request, f'Personal "{nombre_completo}" agregado correctamente ({tipo_personal}).')
                return redirect('gestor_personal')
            except Exception as e:
                messages.error(request, f'Error al agregar personal: {str(e)}')
    
    context = {
        'perfil': perfil,
        'roles': Perfil.ROLE_CHOICES,
        'es_admin': True,
        'form_data': request.POST if request.method == 'POST' else {}
    }
    
    return render(request, 'citas/agregar_personal.html', context)

# Editar personal
@login_required
def editar_personal(request, personal_id):
    try:
        perfil_admin = Perfil.objects.get(user=request.user)
        if not perfil_admin.es_administrativo():
            messages.error(request, 'No tienes permisos para editar personal.')
            return redirect('gestor_personal')
    except Perfil.DoesNotExist:
        return redirect('login')

    personal = get_object_or_404(Perfil, id=personal_id)
    
    if request.method == 'POST':
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        rol = request.POST.get('rol', '')
        especialidad = request.POST.get('especialidad', '').strip()
        numero_colegio = request.POST.get('numero_colegio', '').strip()
        activo = request.POST.get('activo') == 'on'
        requiere_acceso = request.POST.get('requiere_acceso_sistema') == 'on'
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        foto = request.FILES.get('foto')
        eliminar_foto = request.POST.get('eliminar_foto') == 'on'
        
        # Validaciones
        errores = []
        
        if not nombre_completo:
            errores.append('El nombre completo es obligatorio.')
        
        if not email:
            errores.append('El email es obligatorio.')
        
        # Validar email único considerando si tiene usuario o no
        if personal.user:
            if User.objects.filter(email=email).exclude(id=personal.user.id).exists():
                errores.append('Ya existe otro usuario con este email.')
        else:
            if requiere_acceso and User.objects.filter(email=email).exists():
                errores.append('Ya existe un usuario con este email.')
        
        if not telefono:
            errores.append('El teléfono es obligatorio.')
        
        if not rol:
            errores.append('El rol es obligatorio.')
        
        # Validaciones para personal con acceso al sistema
        if requiere_acceso and not personal.user:
            # Se está creando nuevo usuario
            if not username:
                errores.append('El nombre de usuario es obligatorio para personal con acceso al sistema.')
            elif User.objects.filter(username=username).exists():
                errores.append('Ya existe un usuario con este nombre de usuario.')
            
            if not password:
                errores.append('La contraseña es obligatoria al crear acceso al sistema.')
            elif len(password) < 8:
                errores.append('La contraseña debe tener al menos 8 caracteres.')
        
        # Validaciones específicas para dentistas
        if rol == 'dentista':
            if not especialidad:
                errores.append('La especialidad es obligatoria para dentistas.')
            if not numero_colegio:
                errores.append('El número de colegio es obligatorio para dentistas.')
        
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            try:
                # Gestionar usuario Django
                if requiere_acceso:
                    if personal.user:
                        # Actualizar usuario existente
                        personal.user.email = email
                        personal.user.first_name = nombre_completo.split()[0] if nombre_completo.split() else ''
                        personal.user.last_name = ' '.join(nombre_completo.split()[1:]) if len(nombre_completo.split()) > 1 else ''
                        personal.user.is_active = activo
                        if username:
                            personal.user.username = username
                        if password:
                            personal.user.set_password(password)
                        personal.user.save()
                    else:
                        # Crear nuevo usuario
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            first_name=nombre_completo.split()[0] if nombre_completo.split() else '',
                            last_name=' '.join(nombre_completo.split()[1:]) if len(nombre_completo.split()) > 1 else ''
                        )
                        personal.user = user
                else:
                    # No requiere acceso - eliminar usuario si existe
                    if personal.user:
                        user_to_delete = personal.user
                        personal.user = None
                        user_to_delete.delete()
                
                # Actualizar perfil
                personal.nombre_completo = nombre_completo
                personal.email = email
                personal.telefono = telefono
                personal.rol = rol
                personal.especialidad = especialidad if rol == 'dentista' else ''
                personal.numero_colegio = numero_colegio if rol == 'dentista' else ''
                personal.activo = activo
                personal.requiere_acceso_sistema = requiere_acceso
                
                # Gestionar foto
                if eliminar_foto and personal.foto:
                    personal.foto.delete()
                    personal.foto = None
                elif foto:
                    # Eliminar foto anterior si existe
                    if personal.foto:
                        personal.foto.delete()
                    personal.foto = foto
                
                personal.save()
                
                messages.success(request, f'Personal "{nombre_completo}" actualizado correctamente.')
                return redirect('gestor_personal')
            except Exception as e:
                messages.error(request, f'Error al actualizar personal: {str(e)}')
    
    context = {
        'perfil_admin': perfil_admin,
        'personal': personal,
        'roles': Perfil.ROLE_CHOICES,
        'es_admin': True
    }
    
    return render(request, 'citas/editar_personal.html', context)

# Eliminar personal
@login_required
def eliminar_personal(request, personal_id):
    try:
        perfil_admin = Perfil.objects.get(user=request.user)
        if not perfil_admin.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar personal.')
            return redirect('gestor_personal')
    except Perfil.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        personal = get_object_or_404(Perfil, id=personal_id)
        nombre_completo = personal.nombre_completo
        
        try:
            # Eliminar foto si existe
            if personal.foto:
                personal.foto.delete()
            
            # Eliminar usuario asociado si existe
            if personal.user:
                user = personal.user
                user.delete()
            
            # Eliminar perfil
            personal.delete()
            
            messages.success(request, f'Personal "{nombre_completo}" eliminado correctamente del sistema.')
        except Exception as e:
            messages.error(request, f'Error al eliminar personal: {str(e)}')
    
    return redirect('gestor_personal')

# Calendario personal para dentistas
@login_required
def calendario_personal(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden acceder al calendario personal.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    # Obtener parámetros de fecha
    fecha_actual = request.GET.get('fecha', timezone.now().strftime('%Y-%m-%d'))
    try:
        fecha_obj = datetime.strptime(fecha_actual, '%Y-%m-%d').date()
    except ValueError:
        fecha_obj = timezone.now().date()
        fecha_actual = fecha_obj.strftime('%Y-%m-%d')
    
    # Obtener citas del dentista para la fecha seleccionada
    citas_dia = Cita.objects.filter(
        dentista=perfil,
        fecha_hora__date=fecha_obj
    ).order_by('fecha_hora')
    
    # Obtener citas de la semana
    inicio_semana = fecha_obj - timedelta(days=fecha_obj.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    citas_semana = Cita.objects.filter(
        dentista=perfil,
        fecha_hora__date__range=[inicio_semana, fin_semana]
    ).order_by('fecha_hora')
    
    # Estadísticas del dentista
    citas_hoy = citas_dia.count()
    citas_semana_count = citas_semana.count()
    citas_pendientes = Cita.objects.filter(
        dentista=perfil,
        estado__in=['reservada', 'confirmada'],
        fecha_hora__gte=timezone.now()
    ).count()
    citas_completadas_mes = Cita.objects.filter(
        dentista=perfil,
        estado='completada',
        fecha_hora__date__gte=timezone.now().date() - timedelta(days=30)
    ).count()
    
    estadisticas = {
        'citas_hoy': citas_hoy,
        'citas_semana': citas_semana_count,
        'citas_pendientes': citas_pendientes,
        'citas_completadas_mes': citas_completadas_mes,
    }
    
    # Crear calendario semanal
    calendario_semana = []
    for i in range(7):
        fecha_dia = inicio_semana + timedelta(days=i)
        citas_dia_semana = citas_semana.filter(fecha_hora__date=fecha_dia)
        calendario_semana.append({
            'fecha': fecha_dia,
            'citas': citas_dia_semana,
            'es_hoy': fecha_dia == fecha_obj,
            'es_pasado': fecha_dia < timezone.now().date()
        })
    
    context = {
        'perfil': perfil,
        'fecha_actual': fecha_actual,
        'fecha_obj': fecha_obj,
        'citas_dia': citas_dia,
        'citas_semana': citas_semana,
        'calendario_semana': calendario_semana,
        'estadisticas': estadisticas,
        'es_dentista': True
    }
    
    return render(request, 'citas/calendario_personal.html', context)

# Vista para mostrar perfil del dentista
@login_required
def mi_perfil(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'Perfil no encontrado.')
        return redirect('login')
    
    # Obtener estadísticas del dentista
    citas_totales = Cita.objects.filter(dentista=perfil).count()
    citas_completadas = Cita.objects.filter(dentista=perfil, estado='completada').count()
    citas_pendientes = Cita.objects.filter(dentista=perfil, estado='reservada').count()
    
    context = {
        'perfil': perfil,
        'citas_totales': citas_totales,
        'citas_completadas': citas_completadas,
        'citas_pendientes': citas_pendientes,
    }
    
    return render(request, 'citas/mi_perfil.html', context)

# Vista para asignar dentista a una cita
@login_required
def asignar_dentista_cita(request, cita_id):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para asignar dentistas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        return redirect('login')

    cita = get_object_or_404(Cita, id=cita_id)
    
    if request.method == 'POST':
        dentista_id = request.POST.get('dentista') or request.POST.get('dentista_id')
        if dentista_id:
            try:
                dentista = Perfil.objects.get(id=dentista_id, rol='dentista', activo=True)
                # Asignar dentista usando ORM normal
                cita.dentista = dentista
                cita.save()
                messages.success(request, f'Dentista {dentista.nombre_completo} asignado correctamente.')
                return redirect('panel_trabajador')
            except Perfil.DoesNotExist:
                messages.error(request, 'Dentista no encontrado.')
        else:
            messages.error(request, 'Debe seleccionar un dentista.')
    
    # Obtener dentistas disponibles
    dentistas = Perfil.objects.filter(rol='dentista', activo=True).order_by('nombre_completo')
    
    context = {
        'perfil': perfil,
        'cita': cita,
        'dentistas': dentistas,
        'es_admin': True
    }
    
    return render(request, 'citas/asignar_dentista_cita.html', context)

# Vista para que los dentistas vean sus citas asignadas
@login_required
def mis_citas_dentista(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'No tienes permisos para acceder a esta función.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Filtros
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    tab = request.GET.get('tab', 'activas')  # 'activas' o 'completadas'
    
    # Obtener solo citas asignadas al dentista actual (no puede tomar citas disponibles)
    # Incluir relación con cliente para mostrar nombre completo
    from pacientes.models import Cliente
    from historial_clinico.models import Odontograma
    
    # Separar citas en dos grupos: activas (reservadas) y completadas
    citas_activas = Cita.objects.filter(
        dentista=perfil,
        estado='reservada'
    ).select_related('cliente', 'dentista', 'tipo_servicio')
    
    citas_completadas = Cita.objects.filter(
        dentista=perfil,
        estado='completada'
    ).select_related('cliente', 'dentista', 'tipo_servicio')
    
    # Aplicar filtros de fecha si existen
    if fecha_desde:
        citas_activas = citas_activas.filter(fecha_hora__date__gte=fecha_desde)
        citas_completadas = citas_completadas.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        citas_activas = citas_activas.filter(fecha_hora__date__lte=fecha_hasta)
        citas_completadas = citas_completadas.filter(fecha_hora__date__lte=fecha_hasta)
    
    citas_activas = citas_activas.order_by('-fecha_hora')
    citas_completadas = citas_completadas.order_by('-fecha_hora')
    
    # Obtener IDs de citas que tienen fichas asociadas
    odontogramas = Odontograma.objects.filter(dentista=perfil).exclude(cita__isnull=True)
    citas_con_ficha = set(odontogramas.values_list('cita_id', flat=True))
    
    # Procesar citas activas
    citas_activas_list = list(citas_activas)
    for cita in citas_activas_list:
        # Vincular cliente si no está vinculado pero tiene email
        if not cita.cliente and cita.paciente_email:
            try:
                cliente = Cliente.objects.get(email=cita.paciente_email, activo=True)
                cita.cliente = cliente
            except (Cliente.DoesNotExist, Cliente.MultipleObjectsReturned):
                cliente = Cliente.objects.filter(email=cita.paciente_email, activo=True).first()
                if cliente:
                    cita.cliente = cliente
        # Marcar si tiene ficha
        cita.tiene_ficha = cita.id in citas_con_ficha
        if cita.tiene_ficha:
            cita.odontograma = odontogramas.filter(cita_id=cita.id).first()
    
    # Procesar citas completadas
    citas_completadas_list = list(citas_completadas)
    for cita in citas_completadas_list:
        # Vincular cliente si no está vinculado pero tiene email
        if not cita.cliente and cita.paciente_email:
            try:
                cliente = Cliente.objects.get(email=cita.paciente_email, activo=True)
                cita.cliente = cliente
            except (Cliente.DoesNotExist, Cliente.MultipleObjectsReturned):
                cliente = Cliente.objects.filter(email=cita.paciente_email, activo=True).first()
                if cliente:
                    cita.cliente = cliente
        # Marcar si tiene ficha
        cita.tiene_ficha = cita.id in citas_con_ficha
        if cita.tiene_ficha:
            cita.odontograma = odontogramas.filter(cita_id=cita.id).first()
    
    # Calcular estadísticas solo para citas del dentista
    citas_dentista = Cita.objects.filter(dentista=perfil)
    total_citas = citas_dentista.count()
    citas_hoy = citas_dentista.filter(fecha_hora__date=timezone.now().date()).count()
    citas_reservadas = citas_dentista.filter(estado='reservada').count()
    citas_completadas_count = citas_dentista.filter(estado='completada').count()
    
    context = {
        'citas_activas': citas_activas_list,
        'citas_completadas': citas_completadas_list,
        'estados': Cita.ESTADO_CHOICES,
        'estado_actual': estado,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'tab': tab,
        'perfil': perfil,
        'total_citas': total_citas,
        'citas_hoy': citas_hoy,
        'citas_reservadas': citas_reservadas,
        'citas_completadas_count': citas_completadas_count
    }
    
    return render(request, 'citas/mis_citas_dentista.html', context)

# Vista para que el dentista tome una cita disponible
@login_required
def tomar_cita_dentista(request, cita_id):
    # Los dentistas ya no pueden tomar citas directamente
    # Solo los administrativos pueden asignar citas
    messages.error(request, 'Los dentistas no pueden tomar citas directamente. Contacta al administrador para que te asigne citas.')
    return redirect('mis_citas_dentista')

# ELIMINADO: Los dentistas ya no pueden completar sus propias citas
# Solo el personal administrativo puede marcar citas como completadas

# Exportar lista de insumos a PDF
@login_required
def exportar_insumos_pdf(request):
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para exportar insumos.')
            return redirect('gestor_insumos')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Obtener todos los insumos
    insumos = Insumo.objects.all().order_by('categoria', 'nombre')
    
    # Crear el buffer para el PDF
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para el título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#3b82f6')
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#1e293b')
    )
    
    # Estilo para información de la clínica
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#64748b')
    )
    
    # Contenido del PDF
    story = []
    
    # Título principal
    title = Paragraph("INVENTARIO DE INSUMOS", title_style)
    story.append(title)
    
    # Información de la clínica y fecha
    clinic_info = Paragraph(
        f"<b>Clínica Dental</b><br/>"
        f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y a las %H:%M')}<br/>"
        f"Generado por: {perfil.nombre_completo}",
        info_style
    )
    story.append(clinic_info)
    story.append(Spacer(1, 20))
    
    # Estadísticas generales
    total_insumos = insumos.count()
    stock_bajo = insumos.filter(cantidad_actual__lte=F('cantidad_minima')).count()
    agotados = insumos.filter(estado='agotado').count()
    
    stats_text = f"""
    <b>ESTADÍSTICAS GENERALES:</b><br/>
    • Total de insumos: {total_insumos}<br/>
    • Stock bajo: {stock_bajo}<br/>
    • Agotados: {agotados}
    """
    stats_para = Paragraph(stats_text, subtitle_style)
    story.append(stats_para)
    story.append(Spacer(1, 20))
    
    # Agrupar insumos por categoría
    categorias = {}
    for insumo in insumos:
        categoria = insumo.get_categoria_display()
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(insumo)
    
    # Crear tabla para cada categoría
    for categoria, insumos_categoria in categorias.items():
        # Subtítulo de categoría
        categoria_title = Paragraph(f"<b>{categoria.upper()}</b>", subtitle_style)
        story.append(categoria_title)
        story.append(Spacer(1, 10))
        
        # Crear tabla de insumos
        table_data = [
            ['Nombre', 'Stock Actual', 'Stock Mínimo', 'Estado', 'Proveedor', 'Ubicación']
        ]
        
        for insumo in insumos_categoria:
            # Determinar estado visual
            if insumo.estado == 'agotado':
                estado = "AGOTADO"
            elif insumo.stock_bajo:
                estado = "STOCK BAJO"
            elif insumo.proximo_vencimiento:
                estado = "PRÓXIMO A VENCER"
            else:
                estado = "DISPONIBLE"
            
            table_data.append([
                insumo.nombre,
                f"{insumo.cantidad_actual} {insumo.unidad_medida}",
                f"{insumo.cantidad_minima} {insumo.unidad_medida}",
                estado,
                insumo.proveedor or "N/A",
                insumo.ubicacion or "N/A"
            ])
        
        # Crear tabla
        table = Table(table_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 1.5*inch, 1*inch])
        
        # Estilo de la tabla
        table.setStyle(TableStyle([
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Filas de datos
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Colores de estado
            ('TEXTCOLOR', (3, 1), (3, -1), colors.black),
        ]))
        
        # Aplicar colores de estado
        for i, insumo in enumerate(insumos_categoria, 1):
            if insumo.estado == 'agotado':
                table.setStyle(TableStyle([
                    ('TEXTCOLOR', (3, i), (3, i), colors.red),
                ]))
            elif insumo.stock_bajo:
                table.setStyle(TableStyle([
                    ('TEXTCOLOR', (3, i), (3, i), colors.orange),
                ]))
            elif insumo.proximo_vencimiento:
                table.setStyle(TableStyle([
                    ('TEXTCOLOR', (3, i), (3, i), colors.red),
                ]))
            else:
                table.setStyle(TableStyle([
                    ('TEXTCOLOR', (3, i), (3, i), colors.green),
                ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
    
    # Pie de página
    footer_text = f"""
    <i>Este reporte fue generado automáticamente por el sistema de gestión de la clínica dental.<br/>
    Para más información, consulte el sistema en línea.</i>
    """
    footer_para = Paragraph(footer_text, info_style)
    story.append(Spacer(1, 30))
    story.append(footer_para)
    
    # Construir el PDF
    doc.build(story)
    
    # Obtener el contenido del buffer
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Crear respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="inventario_insumos_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    response.write(pdf_content)
    
    return response

# Vista personalizada de logout
def custom_logout(request):
    """Vista personalizada para cerrar sesión"""
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('login')

# ========== GESTIÓN DE PACIENTES POR DENTISTA ==========

# Vista para que los dentistas gestionen sus pacientes
@login_required
def gestionar_pacientes(request):
    """Vista principal para que los dentistas gestionen sus pacientes"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden gestionar pacientes.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Filtros de búsqueda
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    
    # Obtener pacientes asignados al dentista
    pacientes = perfil.get_pacientes_asignados()
    
    # Aplicar filtros
    if search:
        pacientes = [
            paciente for paciente in pacientes
            if (search.lower() in paciente['nombre_completo'].lower() or
                search.lower() in paciente['email'].lower() or
                search.lower() in paciente['telefono'].lower())
        ]
    
    if estado == 'activo':
        pacientes = [paciente for paciente in pacientes if paciente['activo']]
    elif estado == 'inactivo':
        pacientes = [paciente for paciente in pacientes if not paciente['activo']]
    
    # Ordenar por nombre
    pacientes.sort(key=lambda x: x['nombre_completo'])
    
    # Obtener estadísticas
    estadisticas = perfil.get_estadisticas_pacientes()
    
    # Obtener citas recientes de los pacientes
    citas_recientes = perfil.get_citas_pacientes().order_by('-fecha_hora')[:10]
    
    context = {
        'perfil': perfil,
        'pacientes': pacientes,
        'estadisticas': estadisticas,
        'citas_recientes': citas_recientes,
        'search': search,
        'estado': estado,
        'es_dentista': True
    }
    
    return render(request, 'citas/gestionar_pacientes.html', context)

# Vista para ver detalles de un paciente específico
@login_required
def detalle_paciente(request, paciente_id):
    """Vista para ver los detalles de un paciente específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden ver detalles de pacientes.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Obtener el paciente desde las citas asignadas al dentista
    pacientes = perfil.get_pacientes_asignados()
    paciente = None
    
    for p in pacientes:
        if p['id'] == int(paciente_id):
            paciente = p
            break
    
    if not paciente:
        messages.error(request, 'No tienes permisos para ver este paciente.')
        return redirect('gestionar_pacientes')
    
    # Obtener citas del paciente
    citas_paciente = Cita.objects.filter(
        paciente_email=paciente['email'],
        dentista=perfil
    ).order_by('-fecha_hora')
    
    # Estadísticas del paciente
    estadisticas_paciente = {
        'total_citas': citas_paciente.count(),
        'citas_completadas': citas_paciente.filter(estado='completada').count(),
        'citas_pendientes': citas_paciente.filter(estado='reservada').count(),
        'citas_canceladas': citas_paciente.filter(estado='cancelada').count(),
        'ultima_cita': citas_paciente.first(),
        'proxima_cita': citas_paciente.filter(
            fecha_hora__gte=timezone.now(),
            estado='reservada'
        ).first(),
    }
    
    context = {
        'perfil': perfil,
        'paciente': paciente,
        'citas_paciente': citas_paciente,
        'estadisticas_paciente': estadisticas_paciente,
        'es_dentista': True
    }
    
    return render(request, 'citas/detalle_paciente.html', context)

# Vista para agregar notas a un paciente
@login_required
def agregar_nota_paciente(request, paciente_id):
    """Vista para agregar o editar notas de un paciente"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden agregar notas a pacientes.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Obtener el paciente desde las citas asignadas al dentista
    pacientes = perfil.get_pacientes_asignados()
    paciente = None
    
    for p in pacientes:
        if p['id'] == int(paciente_id):
            paciente = p
            break
    
    if not paciente:
        messages.error(request, 'No tienes permisos para editar este paciente.')
        return redirect('gestionar_pacientes')
    
    if request.method == 'POST':
        notas = request.POST.get('notas', '').strip()
        
        try:
            # Actualizar las notas en todas las citas del paciente
            Cita.objects.filter(
                paciente_email=paciente['email'],
                dentista=perfil
            ).update(notas_paciente=notas)
            
            # Si es una petición AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'message': 'Notas del paciente actualizadas correctamente.'})
            
            messages.success(request, 'Notas del paciente actualizadas correctamente.')
            return redirect('detalle_paciente', paciente_id=paciente['id'])
        except Exception as e:
            # Si es una petición AJAX, devolver JSON con error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'message': f'Error al actualizar las notas: {e}'}, status=400)
            
            messages.error(request, f'Error al actualizar las notas: {e}')
    
    context = {
        'perfil': perfil,
        'paciente': paciente,
        'es_dentista': True
    }
    
    return render(request, 'citas/agregar_nota_paciente.html', context)

# Vista para que los dentistas vean sus estadísticas de pacientes
@login_required
def estadisticas_pacientes(request):
    """Vista para mostrar estadísticas detalladas de los pacientes del dentista"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden ver estadísticas de pacientes.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Obtener estadísticas básicas
    estadisticas = perfil.get_estadisticas_pacientes()
    
    # Estadísticas adicionales
    pacientes = perfil.get_pacientes_asignados()
    citas_pacientes = perfil.get_citas_pacientes()
    
    # Citas por mes (últimos 6 meses)
    from datetime import datetime, timedelta
    from django.db.models import Count
    
    hoy = timezone.now().date()
    citas_por_mes = []
    
    for i in range(6):
        fecha_inicio = (hoy.replace(day=1) - timedelta(days=30*i)).replace(day=1)
        fecha_fin = (fecha_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        citas_mes = citas_pacientes.filter(
            fecha_hora__date__range=[fecha_inicio, fecha_fin]
        ).count()
        
        citas_por_mes.append({
            'mes': fecha_inicio.strftime('%B %Y'),
            'citas': citas_mes
        })
    
    citas_por_mes.reverse()  # Mostrar del más antiguo al más reciente
    
    # Pacientes más activos (top 5)
    pacientes_activos = pacientes.annotate(
        total_citas=Count('citas')
    ).order_by('-total_citas')[:5]
    
    # Tipos de consulta más comunes
    tipos_consulta = citas_pacientes.exclude(
        tipo_consulta__isnull=True
    ).exclude(
        tipo_consulta=''
    ).values('tipo_consulta').annotate(
        total=Count('tipo_consulta')
    ).order_by('-total')[:10]
    
    context = {
        'perfil': perfil,
        'estadisticas': estadisticas,
        'citas_por_mes': citas_por_mes,
        'pacientes_activos': pacientes_activos,
        'tipos_consulta': tipos_consulta,
        'es_dentista': True
    }
    
    return render(request, 'citas/estadisticas_pacientes.html', context)

# Vista para asignar dentista a un cliente (solo administrativos)
@login_required
def asignar_dentista_cliente(request, cliente_id):
    """Vista para que los administrativos asignen un dentista a un cliente"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden asignar dentistas a clientes.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Buscar el cliente en el modelo Cliente
    try:
        cliente = Cliente.objects.get(id=cliente_id)
    except Cliente.DoesNotExist:
        messages.error(request, 'Cliente no encontrado.')
        return redirect('gestor_clientes')
    
    if request.method == 'POST':
        dentista_id = request.POST.get('dentista')
        if dentista_id:
            try:
                dentista = Perfil.objects.get(id=dentista_id, rol='dentista', activo=True)
                # Asignar dentista al cliente
                cliente.dentista_asignado = dentista
                cliente.save()
                
                # También actualizar las citas del cliente
                Cita.objects.filter(cliente=cliente).update(dentista=dentista)
                Cita.objects.filter(paciente_email=cliente.email).update(dentista=dentista)
                
                messages.success(request, f'Dentista {dentista.nombre_completo} asignado correctamente al cliente {cliente.nombre_completo}.')
                return redirect('gestor_clientes')
            except Perfil.DoesNotExist:
                messages.error(request, 'Dentista no encontrado.')
        else:
            # Remover dentista asignado del cliente
            cliente.dentista_asignado = None
            cliente.save()
            
            # También remover de las citas del cliente
            Cita.objects.filter(cliente=cliente).update(dentista=None)
            Cita.objects.filter(paciente_email=cliente.email).update(dentista=None)
            
            messages.success(request, f'Dentista removido del cliente {cliente.nombre_completo}.')
            return redirect('gestor_clientes')
    
    # Obtener dentistas disponibles
    dentistas = Perfil.objects.filter(rol='dentista', activo=True).order_by('nombre_completo')
    
    context = {
        'perfil': perfil,
        'cliente': cliente,
        'dentistas': dentistas,
        'es_admin': True
    }
    
    return render(request, 'citas/asignar_dentista_cliente.html', context)

# ========== GESTIÓN DE ODONTOGRAMAS ==========

# Vista principal para listar odontogramas del dentista
@login_required
def listar_odontogramas(request):
    """Vista para listar todos los odontogramas del dentista"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden acceder a los odontogramas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Filtros de búsqueda
    search = request.GET.get('search', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Obtener odontogramas del dentista
    odontogramas = Odontograma.objects.filter(dentista=perfil)
    
    # Aplicar filtros
    if search:
        odontogramas = odontogramas.filter(
            Q(paciente_nombre__icontains=search) |
            Q(paciente_email__icontains=search) |
            Q(motivo_consulta__icontains=search)
        )
    
    if fecha_desde:
        odontogramas = odontogramas.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        odontogramas = odontogramas.filter(fecha_creacion__date__lte=fecha_hasta)
    
    odontogramas = odontogramas.order_by('-fecha_creacion')
    
    # Estadísticas
    total_odontogramas = odontogramas.count()
    odontogramas_mes = odontogramas.filter(
        fecha_creacion__date__gte=timezone.now().date() - timedelta(days=30)
    ).count()
    
    estadisticas = {
        'total_odontogramas': total_odontogramas,
        'odontogramas_mes': odontogramas_mes,
    }
    
    context = {
        'perfil': perfil,
        'odontogramas': odontogramas,
        'estadisticas': estadisticas,
        'search': search,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'es_dentista': True
    }
    
    return render(request, 'citas/listar_odontogramas.html', context)

# Vista para crear un nuevo odontograma
@login_required
def crear_odontograma(request):
    """Vista para crear un nuevo odontograma"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden crear odontogramas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    if request.method == 'POST':
        # Obtener cita asociada (OBLIGATORIA)
        cita_id = request.POST.get('cita_id', '').strip()
        if not cita_id:
            messages.error(request, 'Debes seleccionar una cita para crear la ficha odontológica. Las fichas deben estar vinculadas a una cita específica.')
            return redirect('crear_odontograma')
        
        try:
            cita_obj = Cita.objects.select_related('cliente').get(id=cita_id, dentista=perfil)
        except Cita.DoesNotExist:
            messages.error(request, 'La cita seleccionada no existe o no pertenece a este dentista.')
            return redirect('crear_odontograma')
        
        # Obtener datos del formulario (registro manual)
        paciente_nombre = request.POST.get('paciente_nombre', '').strip()
        paciente_email = request.POST.get('paciente_email', '').strip()
        paciente_telefono = request.POST.get('paciente_telefono', '').strip()
        paciente_fecha_nacimiento = request.POST.get('paciente_fecha_nacimiento', '')
        
        # Intentar vincular con cliente existente si existe (opcional, solo para referencia)
        cliente_obj = None
        if paciente_email:
            try:
                cliente_obj = Cliente.objects.get(email=paciente_email, activo=True)
            except (Cliente.DoesNotExist, Cliente.MultipleObjectsReturned):
                cliente_obj = Cliente.objects.filter(email=paciente_email, activo=True).first()
        
        motivo_consulta = request.POST.get('motivo_consulta', '').strip()
        antecedentes_medicos = request.POST.get('antecedentes_medicos', '').strip()
        alergias = request.POST.get('alergias', '').strip()
        medicamentos_actuales = request.POST.get('medicamentos_actuales', '').strip()
        higiene_oral = request.POST.get('higiene_oral', 'buena')
        estado_general = request.POST.get('estado_general', 'buena')
        observaciones = request.POST.get('observaciones', '').strip()
        plan_tratamiento = request.POST.get('plan_tratamiento', '').strip()
        proxima_cita = request.POST.get('proxima_cita', '')
        
        # Validaciones
        errores = []
        
        if not paciente_nombre:
            errores.append('El nombre completo del paciente es obligatorio.')
        
        if not paciente_email:
            errores.append('El email del paciente es obligatorio.')
        
        if not paciente_telefono:
            errores.append('El teléfono del paciente es obligatorio.')
        
        if not paciente_fecha_nacimiento:
            errores.append('La fecha de nacimiento del paciente es obligatoria.')
        
        if not motivo_consulta:
            errores.append('El motivo de consulta es obligatorio.')
        
        # Validar fecha de nacimiento
        fecha_nacimiento_obj = None
        if paciente_fecha_nacimiento:
            try:
                fecha_nacimiento_obj = datetime.strptime(paciente_fecha_nacimiento, '%Y-%m-%d').date()
            except ValueError:
                errores.append('La fecha de nacimiento debe tener un formato válido.')
        
        # Validar próxima cita
        proxima_cita_obj = None
        if proxima_cita:
            try:
                # Usar timezone-aware datetime si es necesario
                if 'T' in proxima_cita:
                    proxima_cita_obj = datetime.fromisoformat(proxima_cita.replace('Z', '+00:00'))
                else:
                    proxima_cita_obj = datetime.strptime(proxima_cita, '%Y-%m-%dT%H:%M')
                # Asegurar que sea timezone-aware
                if timezone.is_naive(proxima_cita_obj):
                    proxima_cita_obj = timezone.make_aware(proxima_cita_obj)
            except (ValueError, AttributeError) as e:
                errores.append('La próxima cita debe tener un formato válido (YYYY-MM-DDTHH:MM).')
        
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            try:
                # Crear odontograma
                odontograma = Odontograma.objects.create(
                    cliente=cliente_obj,  # Cliente del sistema (opcional)
                    cita=cita_obj,  # Cita asociada (OBLIGATORIA)
                    paciente_nombre=paciente_nombre,
                    paciente_email=paciente_email,
                    paciente_telefono=paciente_telefono,
                    paciente_fecha_nacimiento=fecha_nacimiento_obj,
                    dentista=perfil,
                    motivo_consulta=motivo_consulta,
                    antecedentes_medicos=antecedentes_medicos,
                    alergias=alergias,
                    medicamentos_actuales=medicamentos_actuales,
                    higiene_oral=higiene_oral,
                    estado_general=estado_general,
                    observaciones=observaciones,
                    plan_tratamiento=plan_tratamiento,
                    proxima_cita=proxima_cita_obj
                )
                
                # Procesar datos del odontograma interactivo
                odontograma_data = request.POST.get('odontograma_data', '')
                if odontograma_data:
                    try:
                        import json
                        dientes_data = json.loads(odontograma_data)
                        
                        for numero_diente, caras_data in dientes_data.items():
                            # Determinar el estado general del diente
                            estados = list(caras_data.values())
                            if 'ausente' in estados:
                                estado_general_diente = 'ausente'
                            elif 'caries' in estados:
                                estado_general_diente = 'caries'
                            elif 'obturado' in estados:
                                estado_general_diente = 'obturado'
                            elif 'corona' in estados:
                                estado_general_diente = 'corona'
                            elif 'endodoncia' in estados:
                                estado_general_diente = 'endodoncia'
                            elif 'protesis' in estados:
                                estado_general_diente = 'protesis'
                            elif 'implante' in estados:
                                estado_general_diente = 'implante'
                            elif 'fractura' in estados:
                                estado_general_diente = 'fractura'
                            elif 'sellante' in estados:
                                estado_general_diente = 'sellante'
                            else:
                                estado_general_diente = 'sano'
                            
                            # Crear estado del diente
                            EstadoDiente.objects.create(
                                odontograma=odontograma,
                                numero_diente=int(numero_diente),
                                estado=estado_general_diente,
                                observaciones=f"Datos del odontograma interactivo: {json.dumps(caras_data)}"
                            )
                    except (json.JSONDecodeError, ValueError) as e:
                        messages.warning(request, f'Error al procesar datos del odontograma: {str(e)}')
                
                # Procesar insumos utilizados
                insumos_ids = request.POST.getlist('insumo_id[]')
                insumos_cantidades = request.POST.getlist('insumo_cantidad[]')
                
                # Debug: imprimir lo que recibimos
                print(f"DEBUG - IDs recibidos: {insumos_ids}")
                print(f"DEBUG - Cantidades recibidas: {insumos_cantidades}")
                print(f"DEBUG - POST completo: {request.POST}")
                
                insumos_procesados = 0
                insumos_errores = []
                
                for i, insumo_id in enumerate(insumos_ids):
                    # Saltar si el ID está vacío o es solo espacios
                    if not insumo_id or not insumo_id.strip():
                        continue
                        
                    if i < len(insumos_cantidades):
                        cantidad_str = insumos_cantidades[i].strip() if insumos_cantidades[i] else ''
                        
                        # Saltar si la cantidad está vacía
                        if not cantidad_str:
                            continue
                            
                        try:
                            cantidad = int(cantidad_str)
                            print(f"DEBUG - Procesando insumo ID {insumo_id}, cantidad {cantidad}")
                            if cantidad > 0:
                                # Obtener el insumo
                                from inventario.models import Insumo, MovimientoInsumo
                                from historial_clinico.models import InsumoOdontograma
                                insumo = Insumo.objects.get(id=insumo_id)
                                
                                # Verificar que haya suficiente stock
                                if insumo.cantidad_actual >= cantidad:
                                    # Crear registro de insumo utilizado
                                    InsumoOdontograma.objects.create(
                                        odontograma=odontograma,
                                        insumo=insumo,
                                        cantidad_utilizada=cantidad
                                    )
                                    
                                    # Actualizar cantidad del insumo
                                    cantidad_anterior = insumo.cantidad_actual
                                    insumo.cantidad_actual -= cantidad
                                    
                                    # Actualizar estado si se agotó
                                    if insumo.cantidad_actual == 0:
                                        insumo.estado = 'agotado'
                                    
                                    insumo.save()
                                    
                                    # Crear movimiento de insumo
                                    MovimientoInsumo.objects.create(
                                        insumo=insumo,
                                        tipo='salida',
                                        cantidad=cantidad,
                                        cantidad_anterior=cantidad_anterior,
                                        cantidad_nueva=insumo.cantidad_actual,
                                        motivo=f'Uso en odontograma - Paciente: {paciente_nombre}',
                                        observaciones=f'Odontograma ID: {odontograma.id}',
                                        realizado_por=perfil
                                    )
                                    
                                    insumos_procesados += 1
                                else:
                                    insumos_errores.append(f'{insumo.nombre}: Stock insuficiente (disponible: {insumo.cantidad_actual}, solicitado: {cantidad})')
                        except Insumo.DoesNotExist:
                            insumos_errores.append(f'Insumo con ID {insumo_id} no encontrado')
                        except (ValueError, TypeError):
                            insumos_errores.append(f'Cantidad inválida para el insumo')
                
                # Mensajes de resultado
                if insumos_procesados > 0:
                    messages.success(request, f'Odontograma creado correctamente para {paciente_nombre}. Se registraron {insumos_procesados} insumo(s) utilizado(s).')
                else:
                    messages.success(request, f'Odontograma creado correctamente para {paciente_nombre}.')
                
                if insumos_errores:
                    for error in insumos_errores:
                        messages.warning(request, f'Insumo: {error}')
                
                return redirect('listar_odontogramas')
            except Exception as e:
                messages.error(request, f'Error al crear odontograma: {str(e)}')
    
    # Obtener insumos disponibles
    from inventario.models import Insumo
    insumos_disponibles = Insumo.objects.filter(
        estado='disponible',
        cantidad_actual__gt=0
    ).order_by('nombre')
    
    # Obtener citas del dentista (reservadas o completadas) para asociar con la ficha
    citas_disponibles = Cita.objects.filter(
        dentista=perfil,
        estado__in=['reservada', 'completada']
    ).select_related('cliente').order_by('-fecha_hora')[:50]  # Últimas 50 citas
    
    # Si viene desde una cita, auto-rellenar datos
    form_data = {}
    cita_pre_seleccionada = None
    
    if request.method == 'GET':
        cita_id = request.GET.get('cita_id', '')
        if not cita_id:
            # Si no viene cita_id, redirigir al listado de odontogramas
            messages.info(request, 'Por favor, selecciona una cita desde el listado para crear la ficha. Las fichas deben estar vinculadas a una cita específica.')
            return redirect('listar_odontogramas')
        
        if cita_id:
            try:
                # Obtener cita con relación al cliente para acceder a nombre_completo
                cita_pre_seleccionada = Cita.objects.select_related('cliente', 'dentista').get(id=cita_id, dentista=perfil)
                
                # Intentar obtener el cliente (prioridad: cliente vinculado > búsqueda por email)
                cliente_obj = cita_pre_seleccionada.cliente
                
                # Si no tiene cliente vinculado pero tiene email, buscar por email
                if not cliente_obj and cita_pre_seleccionada.paciente_email:
                    try:
                        cliente_obj = Cliente.objects.get(email=cita_pre_seleccionada.paciente_email, activo=True)
                    except (Cliente.DoesNotExist, Cliente.MultipleObjectsReturned):
                        cliente_obj = Cliente.objects.filter(email=cita_pre_seleccionada.paciente_email, activo=True).first()
                
                # Auto-rellenar datos del paciente desde la cita
                # Prioridad: Cliente encontrado (con nombre_completo) > Datos de la cita
                if cliente_obj:
                    # Si encontramos cliente, usar SIEMPRE sus datos completos (nombre_completo, no username)
                    paciente_nombre_final = cliente_obj.nombre_completo
                    paciente_email_final = cliente_obj.email
                    paciente_telefono_final = cliente_obj.telefono or ''
                    paciente_fecha_nacimiento_final = cliente_obj.fecha_nacimiento.strftime('%Y-%m-%d') if cliente_obj.fecha_nacimiento else ''
                    alergias_final = cliente_obj.alergias or ''
                else:
                    # Si no hay cliente, usar datos de la cita (paciente de recepción)
                    # IMPORTANTE: Si paciente_nombre parece ser un username (sin espacios, corto), 
                    # se debe completar manualmente
                    paciente_nombre_final = cita_pre_seleccionada.paciente_nombre or ''
                    paciente_email_final = cita_pre_seleccionada.paciente_email or ''
                    paciente_telefono_final = cita_pre_seleccionada.paciente_telefono or ''
                    # La cita no tiene fecha de nacimiento, se debe completar manualmente
                    paciente_fecha_nacimiento_final = ''
                    alergias_final = ''
                
                form_data = {
                    'paciente_nombre': paciente_nombre_final,
                    'paciente_email': paciente_email_final,
                    'paciente_telefono': paciente_telefono_final,
                    'paciente_fecha_nacimiento': paciente_fecha_nacimiento_final,
                    'alergias': alergias_final,
                    'cita_id': str(cita_pre_seleccionada.id),
                }
            except Cita.DoesNotExist:
                messages.warning(request, 'La cita seleccionada no existe o no pertenece a este dentista.')
    elif request.method == 'POST':
        form_data = request.POST
    
    context = {
        'perfil': perfil,
        'condiciones': Odontograma.CONDICION_CHOICES,
        'es_dentista': True,
        'form_data': form_data,
        'insumos_disponibles': insumos_disponibles,
        'cita_pre_seleccionada': cita_pre_seleccionada
    }
    
    return render(request, 'citas/crear_odontograma.html', context)

# Vista para ver detalles de un odontograma
@login_required
def detalle_odontograma(request, odontograma_id):
    """Vista para ver los detalles de un odontograma específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not (perfil.es_dentista() or perfil.es_administrativo()):
            messages.error(request, 'Solo los dentistas y administrativos pueden ver odontogramas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Los administrativos pueden ver cualquier odontograma, los dentistas solo los suyos
    if perfil.es_administrativo():
        odontograma = get_object_or_404(Odontograma, id=odontograma_id)
    else:
        odontograma = get_object_or_404(Odontograma, id=odontograma_id, dentista=perfil)
    
    # Obtener estados de los dientes
    estados_dientes = odontograma.dientes.all().order_by('numero_diente')
    
    # Crear diccionario de dientes para facilitar el acceso
    dientes_dict = {diente.numero_diente: diente for diente in estados_dientes}
    
    # Números de dientes según numeración FDI (adultos)
    numeros_dientes_adultos = [
        18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28,  # Superior
        48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38   # Inferior
    ]
    
    # Determinar URL de retorno
    # Prioridad: parámetro return > referer del perfil del cliente > referer general > listar odontogramas
    referer = request.META.get('HTTP_REFERER', '')
    return_url = request.GET.get('return', '')
    
    if return_url:
        # Si se pasó un parámetro return, usarlo directamente
        url_retorno = return_url
    elif odontograma.cliente:
        # Si el odontograma tiene un cliente asociado, volver al perfil del cliente
        url_retorno = reverse('perfil_cliente', args=[odontograma.cliente.id])
    elif referer and referer.startswith(request.build_absolute_uri('/')[:-1]):
        # Si el referer es de nuestro sitio, usarlo
        url_retorno = referer
    else:
        # Por defecto, volver a listar odontogramas
        url_retorno = reverse('listar_odontogramas')
    
    context = {
        'perfil': perfil,
        'odontograma': odontograma,
        'estados_dientes': estados_dientes,
        'dientes_dict': dientes_dict,
        'numeros_dientes': numeros_dientes_adultos,
        'estados_diente': Odontograma.ESTADO_DIENTE_CHOICES,
        'es_dentista': perfil.es_dentista(),
        'es_admin': perfil.es_administrativo(),
        'url_retorno': url_retorno
    }
    
    return render(request, 'citas/detalle_odontograma.html', context)

# Vista para editar un odontograma
@login_required
def editar_odontograma(request, odontograma_id):
    """Vista para editar un odontograma existente"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden editar odontogramas.')
            # Redirigir de vuelta a la vista de detalle del odontograma para mostrar el mensaje
            return redirect('detalle_odontograma', odontograma_id=odontograma_id)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Los administrativos pueden ver el odontograma pero no editarlo
    if perfil.es_administrativo():
        odontograma = get_object_or_404(Odontograma, id=odontograma_id)
    else:
        odontograma = get_object_or_404(Odontograma, id=odontograma_id, dentista=perfil)
    
    if request.method == 'POST':
        # Actualizar cita asociada (opcional)
        cita_id = request.POST.get('cita_id', '').strip()
        if cita_id:
            try:
                cita_obj = Cita.objects.get(id=cita_id, dentista=perfil)
                odontograma.cita = cita_obj
            except Cita.DoesNotExist:
                messages.warning(request, 'La cita seleccionada no existe o no pertenece a este dentista.')
        else:
            # Si no se selecciona ninguna cita, dejar en None
            odontograma.cita = None
        
        # Actualizar datos del odontograma
        odontograma.paciente_nombre = request.POST.get('paciente_nombre', '').strip()
        odontograma.paciente_email = request.POST.get('paciente_email', '').strip()
        odontograma.paciente_telefono = request.POST.get('paciente_telefono', '').strip()
        odontograma.motivo_consulta = request.POST.get('motivo_consulta', '').strip()
        odontograma.antecedentes_medicos = request.POST.get('antecedentes_medicos', '').strip()
        odontograma.alergias = request.POST.get('alergias', '').strip()
        odontograma.medicamentos_actuales = request.POST.get('medicamentos_actuales', '').strip()
        odontograma.higiene_oral = request.POST.get('higiene_oral', 'buena')
        odontograma.estado_general = request.POST.get('estado_general', 'buena')
        odontograma.observaciones = request.POST.get('observaciones', '').strip()
        odontograma.plan_tratamiento = request.POST.get('plan_tratamiento', '').strip()
        
        # Importar datetime una vez para usar en ambas secciones
        from datetime import datetime
        
        # Actualizar fecha de nacimiento
        paciente_fecha_nacimiento = request.POST.get('paciente_fecha_nacimiento', '')
        if paciente_fecha_nacimiento:
            try:
                odontograma.paciente_fecha_nacimiento = datetime.strptime(paciente_fecha_nacimiento, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'La fecha de nacimiento debe tener un formato válido.')
                return redirect('editar_odontograma', odontograma_id=odontograma.id)
        
        # Actualizar próxima cita
        proxima_cita = request.POST.get('proxima_cita', '')
        if proxima_cita:
            try:
                odontograma.proxima_cita = datetime.fromisoformat(proxima_cita)
            except ValueError:
                messages.error(request, 'La próxima cita debe tener un formato válido.')
                return redirect('editar_odontograma', odontograma_id=odontograma.id)
        else:
            odontograma.proxima_cita = None
        
        try:
            odontograma.save()
            # Procesar datos interactivos si vienen del formulario de edición
            odontograma_data = request.POST.get('odontograma_data', '')
            if odontograma_data:
                try:
                    import json
                    dientes_data = json.loads(odontograma_data)
                    from django.db import transaction
                    with transaction.atomic():
                        for numero_diente, caras_data in dientes_data.items():
                            estados = list(caras_data.values())
                            if 'ausente' in estados:
                                estado_general_diente = 'perdido'
                            elif 'caries' in estados:
                                estado_general_diente = 'cariado'
                            elif 'obturado' in estados:
                                estado_general_diente = 'obturado'
                            elif 'corona' in estados:
                                estado_general_diente = 'corona'
                            elif 'endodoncia' in estados:
                                estado_general_diente = 'endodoncia'
                            elif 'protesis' in estados:
                                estado_general_diente = 'protesis'
                            elif 'implante' in estados:
                                estado_general_diente = 'implante'
                            elif 'fractura' in estados:
                                estado_general_diente = 'extraccion' if 'extraccion' in estados else 'cariado'
                            elif 'sellante' in estados:
                                estado_general_diente = 'obturado'
                            else:
                                estado_general_diente = 'sano'
                            # Upsert EstadoDiente
                            estado_obj, _ = EstadoDiente.objects.get_or_create(
                                odontograma=odontograma,
                                numero_diente=int(numero_diente),
                                defaults={'estado': estado_general_diente}
                            )
                            estado_obj.estado = estado_general_diente
                            estado_obj.observaciones = f"Datos del odontograma interactivo: {json.dumps(caras_data)}"
                            estado_obj.save()
                except Exception as e:
                    messages.warning(request, f'Error al procesar datos del odontograma: {str(e)}')

            messages.success(request, 'Odontograma actualizado correctamente.')
            return redirect('listar_odontogramas')
        except Exception as e:
            messages.error(request, f'Error al actualizar odontograma: {str(e)}')
    
    # Obtener citas del dentista (reservadas o completadas) para asociar con la ficha
    citas_disponibles = Cita.objects.filter(
        dentista=perfil,
        estado__in=['reservada', 'completada']
    ).order_by('-fecha_hora')[:50]  # Últimas 50 citas
    
    context = {
        'perfil': perfil,
        'odontograma': odontograma,
        'condiciones': Odontograma.CONDICION_CHOICES,
        'es_dentista': True,
        'citas_disponibles': citas_disponibles
    }
    
    return render(request, 'citas/editar_odontograma.html', context)

# Vista para actualizar el estado de un diente
@login_required
def actualizar_diente(request, odontograma_id, numero_diente):
    """Vista para actualizar el estado de un diente específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden actualizar estados de dientes.')
            # Redirigir de vuelta a la vista de detalle del odontograma
            return redirect('detalle_odontograma', odontograma_id=odontograma_id)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    odontograma = get_object_or_404(Odontograma, id=odontograma_id, dentista=perfil)
    
    if request.method == 'POST':
        estado = request.POST.get('estado', 'sano')
        observaciones = request.POST.get('observaciones', '').strip()
        fecha_tratamiento = request.POST.get('fecha_tratamiento', '')
        costo_tratamiento = request.POST.get('costo_tratamiento', '')
        
        # Validar fecha de tratamiento
        fecha_tratamiento_obj = None
        if fecha_tratamiento:
            try:
                from datetime import datetime
                fecha_tratamiento_obj = datetime.strptime(fecha_tratamiento, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'La fecha de tratamiento debe tener un formato válido.')
                return redirect('detalle_odontograma', odontograma_id=odontograma.id)
        
        # Validar costo
        costo_obj = None
        if costo_tratamiento:
            try:
                costo_obj = float(costo_tratamiento)
                if costo_obj < 0:
                    messages.error(request, 'El costo no puede ser negativo.')
                    return redirect('detalle_odontograma', odontograma_id=odontograma.id)
            except ValueError:
                messages.error(request, 'El costo debe ser un número válido.')
                return redirect('detalle_odontograma', odontograma_id=odontograma.id)
        
        try:
            # Obtener o crear el estado del diente
            estado_diente, created = EstadoDiente.objects.get_or_create(
                odontograma=odontograma,
                numero_diente=numero_diente,
                defaults={
                    'estado': estado,
                    'observaciones': observaciones,
                    'fecha_tratamiento': fecha_tratamiento_obj,
                    'costo_tratamiento': costo_obj
                }
            )
            
            if not created:
                estado_diente.estado = estado
                estado_diente.observaciones = observaciones
                estado_diente.fecha_tratamiento = fecha_tratamiento_obj
                estado_diente.costo_tratamiento = costo_obj
                estado_diente.save()
            
            messages.success(request, f'Estado del diente {numero_diente} actualizado correctamente.')
            return redirect('detalle_odontograma', odontograma_id=odontograma.id)
        except Exception as e:
            messages.error(request, f'Error al actualizar el diente: {str(e)}')
    
    # Obtener el estado actual del diente
    try:
        estado_diente = EstadoDiente.objects.get(odontograma=odontograma, numero_diente=numero_diente)
    except EstadoDiente.DoesNotExist:
        estado_diente = None
    
    context = {
        'perfil': perfil,
        'odontograma': odontograma,
        'numero_diente': numero_diente,
        'estado_diente': estado_diente,
        'estados_diente': Odontograma.ESTADO_DIENTE_CHOICES,
        'es_dentista': True
    }
    
    return render(request, 'citas/actualizar_diente.html', context)

# Vista para eliminar un odontograma
@login_required
def eliminar_odontograma(request, odontograma_id):
    """Vista para eliminar un odontograma"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden eliminar odontogramas.')
            # Redirigir de vuelta a la vista de detalle del odontograma
            return redirect('detalle_odontograma', odontograma_id=odontograma_id)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    odontograma = get_object_or_404(Odontograma, id=odontograma_id, dentista=perfil)
    
    if request.method == 'POST':
        paciente_nombre = odontograma.paciente_nombre
        try:
            odontograma.delete()
            messages.success(request, f'Odontograma de {paciente_nombre} eliminado correctamente.')
            return redirect('listar_odontogramas')
        except Exception as e:
            messages.error(request, f'Error al eliminar odontograma: {str(e)}')
    
    context = {
        'perfil': perfil,
        'odontograma': odontograma,
        'es_dentista': True
    }
    
    return render(request, 'citas/eliminar_odontograma.html', context)

# Vista para exportar odontograma a PDF
@login_required
def exportar_odontograma_pdf(request, odontograma_id):
    """Vista para exportar un odontograma a PDF"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden exportar odontogramas.')
            # Redirigir de vuelta a la vista de detalle del odontograma
            return redirect('detalle_odontograma', odontograma_id=odontograma_id)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Los administrativos pueden ver el odontograma pero no exportarlo
    if perfil.es_administrativo():
        odontograma = get_object_or_404(Odontograma, id=odontograma_id)
    else:
        odontograma = get_object_or_404(Odontograma, id=odontograma_id, dentista=perfil)
    
    # Obtener estados de los dientes
    estados_dientes = odontograma.dientes.all().order_by('numero_diente')
    
    # Crear diccionario de dientes para facilitar el acceso
    dientes_dict = {diente.numero_diente: diente for diente in estados_dientes}
    
    # Función para extraer datos del odontograma interactivo desde observaciones
    def get_tooth_interactive_data(estado_diente):
        """Extrae los datos de las caras del odontograma interactivo desde observaciones"""
        if not estado_diente or not estado_diente.observaciones:
            return None
        if estado_diente.observaciones.startswith('Datos del odontograma interactivo: '):
            try:
                import json
                json_str = estado_diente.observaciones.replace('Datos del odontograma interactivo: ', '')
                return json.loads(json_str)
            except:
                return None
        return None
    
    # Crear el buffer para el PDF
    buffer = BytesIO()
    
    # Crear el documento PDF con márgenes mejorados
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=40,
        bottomMargin=30
    )
    
    # Estilos mejorados
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para el título principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=11,
        spaceAfter=8,
        spaceBefore=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold',
        borderColor=colors.HexColor('#3b82f6'),
        borderWidth=1,
        borderPadding=6
    )
    
    # Estilo para información de la clínica
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#64748b')
    )
    
    # Estilo para texto normal
    normal_style = ParagraphStyle(
        'NormalCompact',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=4,
        alignment=TA_LEFT,
        leading=12
    )
    
    # Estilo para texto de secciones
    section_text_style = ParagraphStyle(
        'SectionText',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=6,
        alignment=TA_LEFT,
        leading=13,
        textColor=colors.HexColor('#374151')
    )
    
    # Contenido del PDF
    story = []
    
    # Título principal con diseño mejorado
    title = Paragraph("<b>FICHA ODONTOLÓGICA</b>", title_style)
    story.append(title)
    
    # Información de la clínica y fecha
    clinic_info = Paragraph(
        f"<b>Clínica Dental</b> | Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        info_style
    )
    story.append(clinic_info)
    story.append(Spacer(1, 12))
    
    # Sección: Información del Paciente
    paciente_title = Paragraph("<b>📋 INFORMACIÓN DEL PACIENTE</b>", subtitle_style)
    story.append(paciente_title)
    
    # Tabla de información del paciente
    paciente_data = [
        ['Nombre Completo:', odontograma.paciente_nombre],
        ['Email:', odontograma.paciente_email],
        ['Teléfono:', odontograma.paciente_telefono or 'No especificado'],
        ['Fecha de Nacimiento:', odontograma.paciente_fecha_nacimiento.strftime('%d/%m/%Y') if odontograma.paciente_fecha_nacimiento else 'No especificado']
    ]
    paciente_table = Table(paciente_data, colWidths=[2*inch, 4.5*inch])
    paciente_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#374151')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    paciente_table.setStyle(paciente_table_style)
    story.append(paciente_table)
    story.append(Spacer(1, 12))
    
    # Sección: Información Clínica
    clinica_title = Paragraph("<b>🏥 INFORMACIÓN CLÍNICA</b>", subtitle_style)
    story.append(clinica_title)
    
    # Motivo de consulta
    motivo_text = Paragraph(f"<b>Motivo de Consulta:</b><br/>{odontograma.motivo_consulta}", section_text_style)
    story.append(motivo_text)
    story.append(Spacer(1, 6))
    
    # Estado e higiene en tabla
    estado_data = [
        ['Higiene Oral:', odontograma.get_higiene_oral_display()],
        ['Estado General:', odontograma.get_estado_general_display()]
    ]
    estado_table = Table(estado_data, colWidths=[2*inch, 4.5*inch])
    estado_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#374151')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    estado_table.setStyle(estado_table_style)
    story.append(estado_table)
    story.append(Spacer(1, 8))
    
    # Antecedentes médicos
    if odontograma.antecedentes_medicos:
        antecedentes_text = Paragraph(f"<b>Antecedentes Médicos:</b><br/>{odontograma.antecedentes_medicos}", section_text_style)
        story.append(antecedentes_text)
        story.append(Spacer(1, 6))
    
    # Alergias
    if odontograma.alergias:
        alergias_text = Paragraph(f"<b>Alergias:</b><br/>{odontograma.alergias}", section_text_style)
        story.append(alergias_text)
        story.append(Spacer(1, 6))
    
    # Medicamentos actuales
    if odontograma.medicamentos_actuales:
        medicamentos_text = Paragraph(f"<b>Medicamentos Actuales:</b><br/>{odontograma.medicamentos_actuales}", section_text_style)
        story.append(medicamentos_text)
        story.append(Spacer(1, 8))
    
    # Sección: Odontograma Visual
    odontograma_title = Paragraph("<b>🦷 ODONTOGRAMA DENTAL</b>", subtitle_style)
    story.append(odontograma_title)
    story.append(Spacer(1, 6))
    
    # Función para obtener color según estado
    def get_tooth_color(estado):
        color_map = {
            'sano': colors.HexColor('#10b981'),      # Verde
            'cariado': colors.HexColor('#dc2626'),    # Rojo
            'caries': colors.HexColor('#dc2626'),     # Rojo
            'obturado': colors.HexColor('#f59e0b'),  # Amarillo
            'corona': colors.HexColor('#fbbf24'),    # Dorado
            'perdido': colors.HexColor('#6b7280'),   # Gris
            'ausente': colors.HexColor('#6b7280'),    # Gris
            'endodoncia': colors.HexColor('#0ea5e9'), # Azul
            'protesis': colors.HexColor('#8b5cf6'),  # Púrpura
            'implante': colors.HexColor('#06b6d4'),  # Cian
            'sellante': colors.HexColor('#84cc16'),   # Verde claro
            'fractura': colors.HexColor('#ef4444'),  # Rojo oscuro
            'extraccion': colors.HexColor('#991b1b'), # Rojo muy oscuro
        }
        return color_map.get(estado, colors.HexColor('#f3f4f6'))  # Gris claro por defecto
    
    # Función para obtener el estado principal del diente (considerando datos interactivos)
    def get_tooth_main_state(numero_diente):
        estado_diente = dientes_dict.get(numero_diente)
        if not estado_diente:
            return 'sano', None
        
        # Intentar obtener datos interactivos
        interactive_data = get_tooth_interactive_data(estado_diente)
        
        if interactive_data:
            # Si hay datos interactivos, determinar el estado principal
            estados = list(interactive_data.values())
            if 'ausente' in estados or 'perdido' in estados:
                return 'ausente', interactive_data
            elif 'caries' in estados or 'cariado' in estados:
                return 'caries', interactive_data
            elif 'obturado' in estados:
                return 'obturado', interactive_data
            elif 'corona' in estados:
                return 'corona', interactive_data
            elif 'endodoncia' in estados:
                return 'endodoncia', interactive_data
            elif 'protesis' in estados:
                return 'protesis', interactive_data
            elif 'implante' in estados:
                return 'implante', interactive_data
            elif 'fractura' in estados:
                return 'fractura', interactive_data
            elif 'sellante' in estados:
                return 'sellante', interactive_data
            else:
                return 'sano', interactive_data
        
        # Si no hay datos interactivos, usar el estado general
        return estado_diente.estado, None
    
    # Función para obtener símbolo según estado
    def get_tooth_symbol(estado):
        symbol_map = {
            'sano': '✓',
            'caries': '●',
            'cariado': '●',
            'obturado': '■',
            'corona': '◊',
            'perdido': '✕',
            'ausente': '✕',
            'endodoncia': '◐',
            'protesis': '◈',
            'implante': '◉',
            'sellante': '◯',
            'fractura': '◢',
            'extraccion': '✕',
        }
        return symbol_map.get(estado, '?')
    
    # Función para obtener texto del diente con caras (si hay datos interactivos)
    def get_tooth_display(numero_diente, estado_val, interactive_data):
        base_text = f"{numero_diente}\n{get_tooth_symbol(estado_val)}"
        
        if interactive_data:
            # Mostrar caras con condiciones
            caras_info = []
            cara_symbols = {'oclusal': 'O', 'vestibular': 'V', 'lingual': 'L', 'mesial': 'M', 'distal': 'D'}
            for cara, condicion in interactive_data.items():
                if condicion != 'sano':
                    caras_info.append(f"{cara_symbols.get(cara, cara[0].upper())}:{get_tooth_symbol(condicion)}")
            
            if caras_info:
                base_text += f"\n{', '.join(caras_info[:3])}"  # Mostrar hasta 3 caras
                if len(caras_info) > 3:
                    base_text += f"\n+{len(caras_info)-3}"
        
        return base_text
    
    # Crear estructura del odontograma anatómico
    odontograma_data = []
    
    # Encabezado con nombres de dientes
    header_row = ['CUADRANTE', 'Molar 3', 'Molar 2', 'Molar 1', 'Premolar 2', 'Premolar 1', 'Canino', 'Incisivo 2', 'Incisivo 1']
    odontograma_data.append(header_row)
    
    # Cuadrante Superior Derecho (vista del paciente)
    superior_derecho = ['SUPERIOR\nDERECHO']
    for numero in [18, 17, 16, 15, 14, 13, 12, 11]:
        estado_val, interactive_data = get_tooth_main_state(numero)
        display_text = get_tooth_display(numero, estado_val, interactive_data)
        superior_derecho.append(display_text)
    odontograma_data.append(superior_derecho)
    
    # Cuadrante Superior Izquierdo (vista del paciente)
    superior_izquierdo = ['SUPERIOR\nIZQUIERDO']
    for numero in [21, 22, 23, 24, 25, 26, 27, 28]:
        estado_val, interactive_data = get_tooth_main_state(numero)
        display_text = get_tooth_display(numero, estado_val, interactive_data)
        superior_izquierdo.append(display_text)
    odontograma_data.append(superior_izquierdo)
    
    # Separador visual
    odontograma_data.append(['─' * 10, '─' * 10, '─' * 10, '─' * 10, '─' * 10, '─' * 10, '─' * 10, '─' * 10, '─' * 10])
    
    # Cuadrante Inferior Izquierdo (vista del paciente)
    inferior_izquierdo = ['INFERIOR\nIZQUIERDO']
    for numero in [38, 37, 36, 35, 34, 33, 32, 31]:
        estado_val, interactive_data = get_tooth_main_state(numero)
        display_text = get_tooth_display(numero, estado_val, interactive_data)
        inferior_izquierdo.append(display_text)
    odontograma_data.append(inferior_izquierdo)
    
    # Cuadrante Inferior Derecho (vista del paciente)
    inferior_derecho = ['INFERIOR\nDERECHO']
    for numero in [41, 42, 43, 44, 45, 46, 47, 48]:
        estado_val, interactive_data = get_tooth_main_state(numero)
        display_text = get_tooth_display(numero, estado_val, interactive_data)
        inferior_derecho.append(display_text)
    odontograma_data.append(inferior_derecho)
    
    # Crear tabla del odontograma mejorada
    odontograma_table = Table(odontograma_data, colWidths=[0.9*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch])
    
    # Estilo de la tabla del odontograma mejorada
    table_style = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Cuadrantes - colores diferenciados
        ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#3b82f6')),  # Sup Der
        ('BACKGROUND', (0, 2), (0, 2), colors.HexColor('#2563eb')),  # Sup Izq
        ('BACKGROUND', (0, 4), (0, 4), colors.HexColor('#10b981')),  # Inf Izq
        ('BACKGROUND', (0, 5), (0, 5), colors.HexColor('#059669')),  # Inf Der
        
        # Texto de cuadrantes
        ('TEXTCOLOR', (0, 1), (0, 5), colors.white),
        ('FONTNAME', (0, 1), (0, 5), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, 5), 8),
        
        # Dientes
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e293b')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (1, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (1, 1), (-1, -1), 6),
        ('LEFTPADDING', (1, 1), (-1, -1), 4),
        ('RIGHTPADDING', (1, 1), (-1, -1), 4),
    ])
    
    # Aplicar colores específicos a dientes según su estado
    for row_idx in range(1, len(odontograma_data)):
        if row_idx == 3:  # Fila separadora
            continue
        
        for col_idx in range(1, len(odontograma_data[row_idx])):
            # Determinar el número del diente
            if row_idx == 1:  # Superior derecho
                tooth_nums = [18, 17, 16, 15, 14, 13, 12, 11]
            elif row_idx == 2:  # Superior izquierdo
                tooth_nums = [21, 22, 23, 24, 25, 26, 27, 28]
            elif row_idx == 4:  # Inferior izquierdo
                tooth_nums = [38, 37, 36, 35, 34, 33, 32, 31]
            elif row_idx == 5:  # Inferior derecho
                tooth_nums = [41, 42, 43, 44, 45, 46, 47, 48]
            else:
                continue
            
            if col_idx - 1 < len(tooth_nums):
                tooth_num = tooth_nums[col_idx - 1]
                estado_val, interactive_data = get_tooth_main_state(tooth_num)
                color = get_tooth_color(estado_val)
                table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), color)
                # Usar texto blanco solo si el color es oscuro
                if estado_val in ['ausente', 'perdido', 'caries', 'cariado', 'fractura', 'extraccion']:
                    table_style.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.white)
                else:
                    table_style.add('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#1e293b'))
    
    # Estilo para la fila separadora
    table_style.add('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e2e8f0'))
    table_style.add('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor('#64748b'))
    table_style.add('FONTSIZE', (0, 3), (-1, 3), 6)
    
    odontograma_table.setStyle(table_style)
    story.append(odontograma_table)
    story.append(Spacer(1, 10))
    
    # Leyenda de símbolos mejorada
    leyenda_title = Paragraph("<b>LEYENDA DE SÍMBOLOS</b>", ParagraphStyle(
        'LeyendaTitle',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=6,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold'
    ))
    story.append(leyenda_title)
    
    leyenda_data = [
        ['Estado', 'Símbolo', 'Descripción', 'Estado', 'Símbolo', 'Descripción'],
        ['Sano', '✓', 'Diente sano', 'Endodoncia', '◐', 'Tratamiento endodóncico'],
        ['Caries', '●', 'Diente cariado', 'Prótesis', '◈', 'Prótesis dental'],
        ['Obturado', '■', 'Diente obturado', 'Implante', '◉', 'Implante dental'],
        ['Corona', '◊', 'Corona dental', 'Sellante', '◯', 'Sellante dental'],
        ['Ausente', '✕', 'Diente ausente/perdido', 'Fractura', '◢', 'Fractura dental']
    ]
    
    leyenda_table = Table(leyenda_data, colWidths=[1*inch, 0.5*inch, 1.5*inch, 1*inch, 0.5*inch, 1.5*inch])
    leyenda_style = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        # Filas de datos
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 1), (-1, -1), 6),
        ('RIGHTPADDING', (0, 1), (-1, -1), 6),
        ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ])
    # Colorear símbolos de la leyenda
    leyenda_style.add('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#10b981'))  # Sano
    leyenda_style.add('TEXTCOLOR', (1, 2), (1, 2), colors.HexColor('#dc2626'))  # Caries
    leyenda_style.add('TEXTCOLOR', (1, 3), (1, 3), colors.HexColor('#f59e0b'))  # Obturado
    leyenda_style.add('TEXTCOLOR', (1, 4), (1, 4), colors.HexColor('#fbbf24'))  # Corona
    leyenda_style.add('TEXTCOLOR', (1, 5), (1, 5), colors.HexColor('#6b7280'))  # Ausente
    leyenda_style.add('TEXTCOLOR', (4, 1), (4, 1), colors.HexColor('#0ea5e9'))  # Endodoncia
    leyenda_style.add('TEXTCOLOR', (4, 2), (4, 2), colors.HexColor('#8b5cf6'))  # Prótesis
    leyenda_style.add('TEXTCOLOR', (4, 3), (4, 3), colors.HexColor('#06b6d4'))  # Implante
    leyenda_style.add('TEXTCOLOR', (4, 4), (4, 4), colors.HexColor('#84cc16'))  # Sellante
    leyenda_style.add('TEXTCOLOR', (4, 5), (4, 5), colors.HexColor('#ef4444'))  # Fractura
    leyenda_table.setStyle(leyenda_style)
    
    story.append(leyenda_table)
    story.append(Spacer(1, 12))
    
    # Sección: Plan de Tratamiento y Observaciones
    if odontograma.plan_tratamiento or odontograma.proxima_cita or odontograma.observaciones:
        plan_title = Paragraph("<b>📋 PLAN DE TRATAMIENTO Y OBSERVACIONES</b>", subtitle_style)
        story.append(plan_title)
        
        plan_data = []
        if odontograma.plan_tratamiento:
            plan_data.append(['Plan de Tratamiento:', odontograma.plan_tratamiento])
        
        if odontograma.proxima_cita:
            plan_data.append(['Próxima Cita:', odontograma.proxima_cita.strftime('%d/%m/%Y %H:%M')])
        
        if odontograma.observaciones:
            plan_data.append(['Observaciones:', odontograma.observaciones])
        
        if plan_data:
            plan_table = Table(plan_data, colWidths=[2*inch, 4.5*inch])
            plan_table_style = TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e293b')),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ])
            plan_table.setStyle(plan_table_style)
            story.append(plan_table)
            story.append(Spacer(1, 10))
    
    # Información del sistema (footer)
    system_info = Paragraph(
        f"<b>Odontólogo responsable:</b> Dr. {odontograma.dentista.nombre_completo} | "
        f"<b>Fecha de creación:</b> {odontograma.fecha_creacion.strftime('%d/%m/%Y %H:%M')} | "
        f"<b>Última actualización:</b> {odontograma.fecha_actualizacion.strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle(
            'SystemInfo',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#64748b'),
            spaceBefore=12
        )
    )
    story.append(system_info)
    
    # Construir el PDF
    doc.build(story)
    
    # Obtener el contenido del buffer
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Crear respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ficha_odontologica_{odontograma.paciente_nombre.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    response.write(pdf_content)
    
    return response


# ============================================================================
# VISTAS DE GESTIÓN DE EVALUACIONES
# ============================================================================

@login_required
def marcar_evaluacion_revisada(request, evaluacion_id):
    """
    Marca una evaluación como revisada
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('login')
    
    try:
        evaluacion = Evaluacion.objects.get(id=evaluacion_id)
        
        if evaluacion.estado == 'pendiente':
            evaluacion.marcar_como_revisada(perfil)
            messages.success(request, f'Evaluación de {evaluacion.cliente.nombre_completo} marcada como revisada.')
        else:
            messages.info(request, 'Esta evaluación ya fue revisada anteriormente.')
    
    except Evaluacion.DoesNotExist:
        messages.error(request, 'Evaluación no encontrada.')
    
    return redirect('gestor_evaluaciones')


@login_required
def archivar_evaluacion(request, evaluacion_id):
    """
    Archiva una evaluación
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('login')
    
    try:
        evaluacion = Evaluacion.objects.get(id=evaluacion_id)
        evaluacion.archivar()
        messages.success(request, f'Evaluación de {evaluacion.cliente.nombre_completo} archivada.')
    
    except Evaluacion.DoesNotExist:
        messages.error(request, 'Evaluación no encontrada.')
    
    return redirect('gestor_evaluaciones')


@login_required
def eliminar_evaluacion(request, evaluacion_id):
    """
    Elimina una evaluación (solo admin)
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar evaluaciones.')
            return redirect('gestor_evaluaciones')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('login')
    
    try:
        evaluacion = Evaluacion.objects.get(id=evaluacion_id)
        nombre_cliente = evaluacion.cliente.nombre_completo
        evaluacion.delete()
        messages.success(request, f'Evaluación de {nombre_cliente} eliminada permanentemente.')
    
    except Evaluacion.DoesNotExist:
        messages.error(request, 'Evaluación no encontrada.')
    
    return redirect('gestor_evaluaciones')


@login_required
def gestor_finanzas(request):
    """
    Vista dedicada para gestionar las finanzas de la clínica
    Muestra ingresos de citas completadas y estadísticas financieras
    SOLO DISPONIBLE PARA ADMINISTRATIVOS
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.activo:
            messages.error(request, 'Tu cuenta está desactivada.')
            return redirect('login')
        
        # Solo permitir acceso a administrativos
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para acceder a esta sección. Solo el personal administrativo puede ver las finanzas.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('login')
    
    # Obtener fechas para filtros
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    inicio_año = hoy.replace(month=1, day=1)
    
    # Obtener todas las citas completadas (excluir las que tienen precio_cobrado = None y no tienen tipo_servicio, que fueron eliminadas del historial)
    # Nota: Las citas que tienen precio_cobrado = None pero tienen tipo_servicio aún se incluyen porque tienen precio base
    citas_completadas = Cita.objects.filter(
        estado='completada'
    ).exclude(
        precio_cobrado__isnull=True,
        tipo_servicio__isnull=True
    ).select_related('tipo_servicio', 'cliente', 'dentista').order_by('-fecha_hora')
    
    # ===== INGRESOS MANUALES =====
    ingresos_manuales = IngresoManual.objects.all().select_related('creado_por').order_by('-fecha', '-creado_el')
    
    # Estadísticas financieras generales
    # Calcular ingresos considerando precio_cobrado o precio del servicio
    total_ingresos = 0
    for cita in citas_completadas:
        if cita.precio_cobrado:
            total_ingresos += float(cita.precio_cobrado)
        elif cita.tipo_servicio and cita.tipo_servicio.precio_base:
            total_ingresos += float(cita.tipo_servicio.precio_base)
    
    # Sumar ingresos manuales
    for ingreso_manual in ingresos_manuales:
        total_ingresos += float(ingreso_manual.monto)
    
    # Ingresos del mes actual
    citas_completadas_mes = citas_completadas.filter(
        fecha_hora__date__gte=inicio_mes,
        fecha_hora__date__lte=fin_mes
    )
    ingresos_mes = 0
    for cita in citas_completadas_mes:
        if cita.precio_cobrado:
            ingresos_mes += float(cita.precio_cobrado)
        elif cita.tipo_servicio and cita.tipo_servicio.precio_base:
            ingresos_mes += float(cita.tipo_servicio.precio_base)
    
    # Sumar ingresos manuales del mes
    ingresos_manuales_mes = ingresos_manuales.filter(
        fecha__gte=inicio_mes,
        fecha__lte=fin_mes
    )
    for ingreso_manual in ingresos_manuales_mes:
        ingresos_mes += float(ingreso_manual.monto)
    
    # Ingresos del año actual
    citas_completadas_año = citas_completadas.filter(
        fecha_hora__date__gte=inicio_año
    )
    ingresos_año = 0
    for cita in citas_completadas_año:
        if cita.precio_cobrado:
            ingresos_año += float(cita.precio_cobrado)
        elif cita.tipo_servicio and cita.tipo_servicio.precio_base:
            ingresos_año += float(cita.tipo_servicio.precio_base)
    
    # Sumar ingresos manuales del año
    ingresos_manuales_año = ingresos_manuales.filter(
        fecha__gte=inicio_año
    )
    for ingreso_manual in ingresos_manuales_año:
        ingresos_año += float(ingreso_manual.monto)
    
    # Cantidad de citas
    total_citas_completadas = citas_completadas.count()
    citas_mes = citas_completadas_mes.count()
    citas_año = citas_completadas_año.count()
    
    # Ingresos por servicio (calcular manualmente para considerar precio_cobrado o precio del servicio)
    ingresos_por_servicio_dict = {}
    for cita in citas_completadas:
        servicio_nombre = cita.tipo_servicio.nombre if cita.tipo_servicio else 'Sin servicio'
        servicio_categoria = cita.tipo_servicio.categoria if cita.tipo_servicio else 'otros'
        
        if servicio_nombre not in ingresos_por_servicio_dict:
            ingresos_por_servicio_dict[servicio_nombre] = {
                'tipo_servicio__nombre': servicio_nombre,
                'tipo_servicio__categoria': servicio_categoria,
                'total_ingresos': 0,
                'cantidad_citas': 0
            }
        
        ingresos_por_servicio_dict[servicio_nombre]['cantidad_citas'] += 1
        if cita.precio_cobrado:
            ingresos_por_servicio_dict[servicio_nombre]['total_ingresos'] += float(cita.precio_cobrado)
        elif cita.tipo_servicio and cita.tipo_servicio.precio_base:
            ingresos_por_servicio_dict[servicio_nombre]['total_ingresos'] += float(cita.tipo_servicio.precio_base)
    
    ingresos_por_servicio = sorted(ingresos_por_servicio_dict.values(), key=lambda x: x['total_ingresos'], reverse=True)
    
    # Ingresos por mes (últimos 12 meses)
    ingresos_por_mes = []
    from calendar import monthrange
    for i in range(11, -1, -1):
        # Calcular fecha del mes
        mes_fecha = hoy - timedelta(days=30 * i)
        mes_inicio = mes_fecha.replace(day=1)
        # Obtener último día del mes
        ultimo_dia = monthrange(mes_fecha.year, mes_fecha.month)[1]
        mes_fin = mes_fecha.replace(day=ultimo_dia)
        
        citas_mes_actual = citas_completadas.filter(
            fecha_hora__date__gte=mes_inicio,
            fecha_hora__date__lte=mes_fin
        )
        
        ingresos_mes_actual = 0
        for cita in citas_mes_actual:
            if cita.precio_cobrado:
                ingresos_mes_actual += float(cita.precio_cobrado)
            elif cita.tipo_servicio and cita.tipo_servicio.precio_base:
                ingresos_mes_actual += float(cita.tipo_servicio.precio_base)
        
        ingresos_por_mes.append({
            'mes': mes_fecha.strftime('%B %Y'),
            'ingresos': ingresos_mes_actual,
            'citas': citas_mes_actual.count()
        })
    
    # Precio promedio por cita
    if total_citas_completadas > 0:
        precio_promedio = total_ingresos / total_citas_completadas
    else:
        precio_promedio = 0
    
    # Ingresos por dentista (calcular manualmente)
    ingresos_por_dentista_dict = {}
    for cita in citas_completadas.filter(dentista__isnull=False):
        if not cita.dentista:
            continue
        dentista_nombre = cita.dentista.nombre_completo
        
        if dentista_nombre not in ingresos_por_dentista_dict:
            ingresos_por_dentista_dict[dentista_nombre] = {
                'dentista__nombre_completo': dentista_nombre,
                'total_ingresos': 0,
                'cantidad_citas': 0
            }
        
        ingresos_por_dentista_dict[dentista_nombre]['cantidad_citas'] += 1
        if cita.precio_cobrado:
            ingresos_por_dentista_dict[dentista_nombre]['total_ingresos'] += float(cita.precio_cobrado)
        elif cita.tipo_servicio and cita.tipo_servicio.precio_base:
            ingresos_por_dentista_dict[dentista_nombre]['total_ingresos'] += float(cita.tipo_servicio.precio_base)
    
    ingresos_por_dentista = sorted(ingresos_por_dentista_dict.values(), key=lambda x: x['total_ingresos'], reverse=True)
    
    # Combinar todos los ingresos (citas + manuales) para la tabla
    todos_ingresos_list = []
    
    # Agregar citas completadas (solo las que tienen precio o servicio)
    for cita in citas_completadas:
        # Solo incluir citas que tienen precio_cobrado o tipo_servicio (no las eliminadas del historial)
        if cita.precio_cobrado is not None or (cita.tipo_servicio and cita.tipo_servicio.precio_base):
            monto_cita = 0
            if cita.precio_cobrado:
                monto_cita = float(cita.precio_cobrado)
            elif cita.tipo_servicio and cita.tipo_servicio.precio_base:
                monto_cita = float(cita.tipo_servicio.precio_base)
            
            todos_ingresos_list.append({
                'cita': cita,
                'monto': monto_cita,
                'tipo': 'cita',
                'fecha': cita.fecha_hora
            })
    
    # Agregar ingresos manuales
    for ingreso_manual in ingresos_manuales:
        from datetime import datetime
        fecha_ingreso = datetime.combine(ingreso_manual.fecha, datetime.min.time())
        todos_ingresos_list.append({
            'ingreso_manual': ingreso_manual,
            'monto': float(ingreso_manual.monto),
            'tipo': 'ingreso_manual',
            'fecha': fecha_ingreso
        })
    
    # Ordenar por fecha (más recientes primero)
    todos_ingresos_list.sort(key=lambda x: x['fecha'], reverse=True)
    todos_ingresos = todos_ingresos_list[:50]  # Mostrar los últimos 50
    
    # Citas recientes (últimas 10) - para compatibilidad
    citas_recientes = citas_completadas[:10]
    
    # ===== EGRESOS (Gastos) =====
    # Obtener movimientos de insumos tipo "entrada" (compras) como egresos
    from inventario.models import MovimientoInsumo
    from proveedores.models import SolicitudInsumo
    movimientos_entrada = MovimientoInsumo.objects.filter(tipo='entrada').select_related('insumo', 'realizado_por').order_by('-fecha_movimiento')
    
    # Obtener solicitudes de insumos marcadas como egreso automático
    solicitudes_egreso = SolicitudInsumo.objects.filter(
        registrar_como_egreso=True,
        monto_egreso__isnull=False
    ).select_related('insumo', 'proveedor', 'solicitado_por').order_by('-fecha_solicitud')
    
    # Obtener egresos manuales
    egresos_manuales = EgresoManual.objects.all().select_related('creado_por').order_by('-fecha', '-creado_el')
    
    # Calcular egresos totales (basado en compras de insumos con precio)
    total_egresos = 0
    for movimiento in movimientos_entrada:
        if movimiento.insumo and movimiento.insumo.precio_unitario:
            total_egresos += float(movimiento.insumo.precio_unitario) * movimiento.cantidad
    
    # Sumar egresos automáticos de solicitudes
    for solicitud in solicitudes_egreso:
        if solicitud.monto_egreso:
            total_egresos += float(solicitud.monto_egreso)
    
    # Sumar egresos manuales
    for egreso_manual in egresos_manuales:
        total_egresos += float(egreso_manual.monto)
    
    # Egresos del mes
    movimientos_mes = movimientos_entrada.filter(
        fecha_movimiento__date__gte=inicio_mes,
        fecha_movimiento__date__lte=fin_mes
    )
    egresos_mes = 0
    for movimiento in movimientos_mes:
        if movimiento.insumo and movimiento.insumo.precio_unitario:
            egresos_mes += float(movimiento.insumo.precio_unitario) * movimiento.cantidad
    
    # Sumar egresos automáticos del mes
    solicitudes_mes = solicitudes_egreso.filter(
        fecha_solicitud__date__gte=inicio_mes,
        fecha_solicitud__date__lte=fin_mes
    )
    for solicitud in solicitudes_mes:
        if solicitud.monto_egreso:
            egresos_mes += float(solicitud.monto_egreso)
    
    # Sumar egresos manuales del mes
    egresos_manuales_mes = egresos_manuales.filter(
        fecha__gte=inicio_mes,
        fecha__lte=fin_mes
    )
    for egreso_manual in egresos_manuales_mes:
        egresos_mes += float(egreso_manual.monto)
    
    # Egresos del año
    movimientos_año = movimientos_entrada.filter(
        fecha_movimiento__date__gte=inicio_año
    )
    egresos_año = 0
    for movimiento in movimientos_año:
        if movimiento.insumo and movimiento.insumo.precio_unitario:
            egresos_año += float(movimiento.insumo.precio_unitario) * movimiento.cantidad
    
    # Sumar egresos automáticos del año
    solicitudes_año = solicitudes_egreso.filter(
        fecha_solicitud__date__gte=inicio_año
    )
    for solicitud in solicitudes_año:
        if solicitud.monto_egreso:
            egresos_año += float(solicitud.monto_egreso)
    
    # Sumar egresos manuales del año
    egresos_manuales_año = egresos_manuales.filter(
        fecha__gte=inicio_año
    )
    for egreso_manual in egresos_manuales_año:
        egresos_año += float(egreso_manual.monto)
    
    # Egresos por mes (últimos 12 meses)
    egresos_por_mes = []
    from calendar import monthrange
    for i in range(11, -1, -1):
        mes_fecha = hoy - timedelta(days=30 * i)
        mes_inicio = mes_fecha.replace(day=1)
        ultimo_dia = monthrange(mes_fecha.year, mes_fecha.month)[1]
        mes_fin = mes_fecha.replace(day=ultimo_dia)
        
        movimientos_mes_actual = movimientos_entrada.filter(
            fecha_movimiento__date__gte=mes_inicio,
            fecha_movimiento__date__lte=mes_fin
        )
        
        egresos_mes_actual = 0
        for movimiento in movimientos_mes_actual:
            if movimiento.insumo and movimiento.insumo.precio_unitario:
                egresos_mes_actual += float(movimiento.insumo.precio_unitario) * movimiento.cantidad
        
        # Sumar egresos automáticos del mes
        solicitudes_mes_actual = solicitudes_egreso.filter(
            fecha_solicitud__date__gte=mes_inicio,
            fecha_solicitud__date__lte=mes_fin
        )
        for solicitud in solicitudes_mes_actual:
            if solicitud.monto_egreso:
                egresos_mes_actual += float(solicitud.monto_egreso)
        
        # Sumar egresos manuales del mes
        egresos_manuales_mes_actual = egresos_manuales.filter(
            fecha__gte=mes_inicio,
            fecha__lte=mes_fin
        )
        for egreso_manual in egresos_manuales_mes_actual:
            egresos_mes_actual += float(egreso_manual.monto)
        
        egresos_por_mes.append({
            'mes': mes_fecha.strftime('%B %Y'),
            'egresos': egresos_mes_actual,
            'movimientos': movimientos_mes_actual.count() + solicitudes_mes_actual.count() + egresos_manuales_mes_actual.count()
        })
    
    # Todos los egresos combinados para la tabla (compras, solicitudes, manuales)
    todos_egresos_list = []
    
    # Agregar compras
    for movimiento in movimientos_entrada:
        total_movimiento = 0
        if movimiento.insumo and movimiento.insumo.precio_unitario:
            total_movimiento = float(movimiento.insumo.precio_unitario) * movimiento.cantidad
        
        todos_egresos_list.append({
            'movimiento': movimiento,
            'total': total_movimiento,
            'tipo': 'compra'
        })
    
    # Agregar solicitudes
    for solicitud in solicitudes_egreso:
        todos_egresos_list.append({
            'solicitud': solicitud,
            'total': float(solicitud.monto_egreso) if solicitud.monto_egreso else 0,
            'tipo': 'solicitud'
        })
    
    # Agregar egresos manuales
    for egreso_manual in egresos_manuales:
        todos_egresos_list.append({
            'egreso_manual': egreso_manual,
            'total': float(egreso_manual.monto),
            'tipo': 'egreso_manual'
        })
    
    # Ordenar por fecha (más recientes primero)
    def get_fecha(item):
        if item['tipo'] == 'compra':
            return item['movimiento'].fecha_movimiento
        elif item['tipo'] == 'solicitud':
            return item['solicitud'].fecha_solicitud
        else:  # egreso_manual
            from datetime import datetime
            return datetime.combine(item['egreso_manual'].fecha, datetime.min.time())
    
    todos_egresos_list.sort(key=get_fecha, reverse=True)
    movimientos_recientes = todos_egresos_list[:50]  # Mostrar los últimos 50
    
    # Balance (Ingresos - Egresos)
    balance_total = total_ingresos - total_egresos
    balance_mes = ingresos_mes - egresos_mes
    balance_año = ingresos_año - egresos_año
    
    context = {
        'perfil': perfil,
        'es_admin': perfil.es_administrativo(),
        # Ingresos
        'total_ingresos': total_ingresos,
        'ingresos_mes': ingresos_mes,
        'ingresos_año': ingresos_año,
        'total_citas_completadas': total_citas_completadas,
        'citas_mes': citas_mes,
        'citas_año': citas_año,
        'precio_promedio': precio_promedio,
        'ingresos_por_servicio': ingresos_por_servicio[:5],  # Solo top 5
        'ingresos_por_mes': ingresos_por_mes,
        'ingresos_por_dentista': ingresos_por_dentista[:5],  # Solo top 5
        'citas_recientes': citas_recientes,
        'todos_ingresos': todos_ingresos,  # Todos los ingresos combinados
        'ingresos_manuales': ingresos_manuales,  # Para referencia
        # Egresos
        'total_egresos': total_egresos,
        'egresos_mes': egresos_mes,
        'egresos_año': egresos_año,
        'egresos_por_mes': egresos_por_mes,
        'movimientos_recientes': movimientos_recientes,  # Todos los egresos combinados
        'egresos_manuales': egresos_manuales,  # Para referencia
        # Balance
        'balance_total': balance_total,
        'balance_mes': balance_mes,
        'balance_año': balance_año,
    }
    
    return render(request, 'citas/gestor_finanzas.html', context)


# Vistas para Ingresos y Egresos Manuales
@login_required
def agregar_ingreso_manual(request):
    """Vista para agregar un ingreso manual"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para agregar ingresos manuales.')
            return redirect('gestor_finanzas')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        monto_str = request.POST.get('monto', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha = request.POST.get('fecha', '')
        notas = request.POST.get('notas', '').strip()
        
        # Validaciones
        if not monto_str or not descripcion or not fecha:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('gestor_finanzas')
        
        try:
            monto = round(float(monto_str))  # Redondear a entero para pesos chilenos
            if monto <= 0:
                messages.error(request, 'El monto debe ser mayor a cero.')
                return redirect('gestor_finanzas')
        except ValueError:
            messages.error(request, 'El monto debe ser un número válido.')
            return redirect('gestor_finanzas')
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('gestor_finanzas')
        
        # Crear ingreso manual
        IngresoManual.objects.create(
            monto=monto,
            descripcion=descripcion,
            fecha=fecha_obj,
            notas=notas if notas else None,
            creado_por=perfil
        )
        
        messages.success(request, f'Ingreso manual de ${monto:,} agregado correctamente.')
    
    return redirect('gestor_finanzas')


@login_required
def eliminar_ingreso_manual(request, ingreso_id):
    """Vista para eliminar un ingreso manual"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar ingresos manuales.')
            return redirect('gestor_finanzas')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    ingreso = get_object_or_404(IngresoManual, id=ingreso_id)
    monto = ingreso.monto
    ingreso.delete()
    
    messages.success(request, f'Ingreso manual de ${monto:,} eliminado correctamente.')
    return redirect('gestor_finanzas')


@login_required
def agregar_egreso_manual(request):
    """Vista para agregar un egreso manual"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para agregar egresos manuales.')
            return redirect('gestor_finanzas')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        monto_str = request.POST.get('monto', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha = request.POST.get('fecha', '')
        notas = request.POST.get('notas', '').strip()
        
        # Validaciones
        if not monto_str or not descripcion or not fecha:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('gestor_finanzas')
        
        try:
            monto = round(float(monto_str))  # Redondear a entero para pesos chilenos
            if monto <= 0:
                messages.error(request, 'El monto debe ser mayor a cero.')
                return redirect('gestor_finanzas')
        except ValueError:
            messages.error(request, 'El monto debe ser un número válido.')
            return redirect('gestor_finanzas')
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('gestor_finanzas')
        
        # Crear egreso manual
        EgresoManual.objects.create(
            monto=monto,
            descripcion=descripcion,
            fecha=fecha_obj,
            notas=notas if notas else None,
            creado_por=perfil
        )
        
        messages.success(request, f'Egreso manual de ${monto:,} agregado correctamente.')
    
    return redirect('gestor_finanzas')


@login_required
def eliminar_egreso_manual(request, egreso_id):
    """Vista para eliminar un egreso manual"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar egresos manuales.')
            return redirect('gestor_finanzas')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    egreso = get_object_or_404(EgresoManual, id=egreso_id)
    monto = egreso.monto
    egreso.delete()
    
    messages.success(request, f'Egreso manual de ${monto:,} eliminado correctamente.')
    return redirect('gestor_finanzas')


@login_required
def eliminar_ingreso_cita(request, cita_id):
    """
    Vista para eliminar un ingreso de una cita completada del historial financiero
    Marca el precio_cobrado como None para que no aparezca en los cálculos
    SOLO DISPONIBLE PARA ADMINISTRATIVOS
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar ingresos de citas.')
            return redirect('gestor_finanzas')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    cita = get_object_or_404(Cita, id=cita_id)
    
    # Solo permitir eliminar ingresos de citas completadas
    if cita.estado != 'completada':
        messages.error(request, 'Solo se pueden eliminar ingresos de citas completadas.')
        return redirect('gestor_finanzas')
    
    # Guardar el monto para el mensaje
    monto_anterior = cita.precio_cobrado or (cita.tipo_servicio.precio_base if cita.tipo_servicio else 0)
    
    # Marcar precio_cobrado como None para que no aparezca en los cálculos financieros
    cita.precio_cobrado = None
    cita.save()
    
    messages.success(request, f'Ingreso de cita eliminado correctamente del historial financiero.')
    return redirect('gestor_finanzas')


@login_required
def eliminar_egreso_compra(request, movimiento_id):
    """
    Vista para eliminar un egreso de compra (MovimientoInsumo) del historial financiero
    Elimina el movimiento de insumo
    SOLO DISPONIBLE PARA ADMINISTRATIVOS
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar egresos de compras.')
            return redirect('gestor_finanzas')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    from inventario.models import MovimientoInsumo
    movimiento = get_object_or_404(MovimientoInsumo, id=movimiento_id)
    
    # Solo permitir eliminar movimientos de entrada (compras)
    if movimiento.tipo != 'entrada':
        messages.error(request, 'Solo se pueden eliminar movimientos de entrada (compras).')
        return redirect('gestor_finanzas')
    
    # Guardar información para el mensaje
    insumo_nombre = movimiento.insumo.nombre if movimiento.insumo else "Sin nombre"
    cantidad = movimiento.cantidad
    monto = float(movimiento.insumo.precio_unitario) * cantidad if movimiento.insumo and movimiento.insumo.precio_unitario else 0
    
    # Eliminar el movimiento
    movimiento.delete()
    
    messages.success(request, f'Compra de {insumo_nombre} eliminada correctamente del historial financiero.')
    return redirect('gestor_finanzas')


@login_required
def eliminar_egreso_solicitud(request, solicitud_id):
    """
    Vista para eliminar un egreso de solicitud de insumo del historial financiero
    Desmarca el flag registrar_como_egreso y pone monto_egreso a None
    SOLO DISPONIBLE PARA ADMINISTRATIVOS
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para eliminar egresos de solicitudes.')
            return redirect('gestor_finanzas')
    except Perfil.DoesNotExist:
        return redirect('login')
    
    from proveedores.models import SolicitudInsumo
    solicitud = get_object_or_404(SolicitudInsumo, id=solicitud_id)
    
    # Solo permitir eliminar si estaba marcada como egreso
    if not solicitud.registrar_como_egreso:
        messages.error(request, 'Esta solicitud no está registrada como egreso.')
        return redirect('gestor_finanzas')
    
    # Guardar el monto para el mensaje
    monto_anterior = solicitud.monto_egreso or 0
    
    # Desmarcar como egreso
    solicitud.registrar_como_egreso = False
    solicitud.monto_egreso = None
    solicitud.save()
    
    messages.success(request, f'Egreso de solicitud eliminado correctamente del historial financiero.')
    return redirect('gestor_finanzas')


# =====================================================
# VISTAS PARA INFORMACIÓN DE LA CLÍNICA
# =====================================================

@login_required
def obtener_informacion_clinica(request):
    """
    Vista AJAX para obtener la información de contacto de la clínica
    """
    try:
        from configuracion.models import InformacionClinica
        info = InformacionClinica.obtener()
        
        data = {
            'success': True,
            'data': {
                'nombre_clinica': info.nombre_clinica,
                'direccion': info.direccion,
                'telefono': info.telefono,
                'telefono_secundario': info.telefono_secundario or '',
                'email': info.email,
                'email_alternativo': info.email_alternativo or '',
                'horario_atencion': info.horario_atencion,
                'sitio_web': info.sitio_web or '',
                'whatsapp': info.whatsapp or '',
                'facebook': info.facebook or '',
                'instagram': info.instagram or '',
                'notas_adicionales': info.notas_adicionales or '',
                'actualizado_el': info.actualizado_el.strftime('%d/%m/%Y %H:%M') if info.actualizado_el else '',
                'actualizado_por': info.actualizado_por.nombre_completo if info.actualizado_por else ''
            }
        }
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def editar_informacion_clinica(request):
    """
    Vista para editar la información de contacto de la clínica
    Solo disponible para administrativos
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para editar la información de la clínica.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('login')
    
    from configuracion.models import InformacionClinica
    info = InformacionClinica.obtener()
    
    if request.method == 'POST':
        try:
            # Actualizar los campos
            info.nombre_clinica = request.POST.get('nombre_clinica', info.nombre_clinica)
            info.direccion = request.POST.get('direccion', info.direccion)
            info.telefono = request.POST.get('telefono', info.telefono)
            info.telefono_secundario = request.POST.get('telefono_secundario', '')
            info.email = request.POST.get('email', info.email)
            info.email_alternativo = request.POST.get('email_alternativo', '')
            info.horario_atencion = request.POST.get('horario_atencion', info.horario_atencion)
            info.sitio_web = request.POST.get('sitio_web', '')
            info.whatsapp = request.POST.get('whatsapp', '')
            info.facebook = request.POST.get('facebook', '')
            info.instagram = request.POST.get('instagram', '')
            info.notas_adicionales = request.POST.get('notas_adicionales', '')
            info.actualizado_por = perfil
            
            info.save()
            
            # Si es una petición AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Información actualizada correctamente'
                })
            
            messages.success(request, 'Información de la clínica actualizada correctamente.')
            return redirect('panel_trabajador')
        
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            
            messages.error(request, f'Error al actualizar la información: {str(e)}')
    
    context = {
        'perfil': perfil,
        'info': info
    }
    
    return render(request, 'citas/editar_informacion_clinica.html', context)


# =====================================================
# VISTAS PARA GESTIÓN DE CLIENTES
# =====================================================

@login_required
def validar_username(request):
    """
    Vista AJAX para validar si un username ya existe
    """
    username = request.GET.get('username', '').strip()
    
    if not username:
        return JsonResponse({'existe': False})
    
    from django.contrib.auth.models import User
    existe = User.objects.filter(username=username).exists()
    
    return JsonResponse({'existe': existe})


@login_required
def crear_cliente_presencial(request):
    """
    Vista para crear un cliente que se registra presencialmente
    También crea su cuenta en el sistema de citas online con credenciales manuales
    Solo disponible para administrativos
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para crear clientes.')
            return redirect('gestor_clientes')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            from django.contrib.auth.models import User
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Obtener datos del formulario
            nombre_completo = request.POST.get('nombre_completo')
            email = request.POST.get('email')
            telefono_raw = request.POST.get('telefono')
            rut = request.POST.get('rut', '').strip()
            fecha_nacimiento_str = request.POST.get('fecha_nacimiento', '').strip()
            alergias = request.POST.get('alergias', '').strip()
            
            # Validar campos obligatorios
            if not rut:
                messages.error(request, 'El RUT es obligatorio.')
                return redirect('gestor_clientes')
            
            if not fecha_nacimiento_str:
                messages.error(request, 'La fecha de nacimiento es obligatoria.')
                return redirect('gestor_clientes')
            
            if not alergias:
                messages.error(request, 'Las alergias son obligatorias. Si no tiene alergias, escriba "Ninguna".')
                return redirect('gestor_clientes')
            notas = request.POST.get('notas', '')
            crear_usuario_online = request.POST.get('crear_usuario_online') == 'on'
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            enviar_email = request.POST.get('enviar_credenciales_email') == 'on'
            
            # Normalizar el número de teléfono chileno
            telefono = normalizar_telefono_chileno(telefono_raw)
            if not telefono:
                messages.error(
                    request, 
                    'El número de teléfono no es válido. '
                    'Ingrese solo los 8 dígitos del celular (ejemplo: 12345678). '
                    'El sistema agregará automáticamente el 9 y el código de país (+56).'
                )
                return redirect('gestor_clientes')
            
            # Validar que el email no exista en Cliente
            if Cliente.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe un cliente con ese email en la clínica.')
                return redirect('gestor_clientes')
            
            # Validar que el RUT no exista si se proporcionó
            if rut and Cliente.objects.filter(rut=rut).exists():
                messages.error(request, 'Ya existe un cliente con ese RUT en la clínica.')
                return redirect('gestor_clientes')
            
            # Procesar fecha de nacimiento (ahora obligatorio)
            try:
                from datetime import datetime
                fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'La fecha de nacimiento no tiene un formato válido.')
                return redirect('gestor_clientes')
            
            # Crear el cliente en la clínica
            # Todos los campos ahora son obligatorios (rut, fecha_nacimiento, alergias)
            cliente = Cliente.objects.create(
                nombre_completo=nombre_completo,
                email=email,
                telefono=telefono,
                rut=rut,
                fecha_nacimiento=fecha_nacimiento,
                alergias=alergias,
                notas=notas,
                activo=True
            )
            
            # Si se solicitó, crear también el usuario en el sistema de citas online
            if crear_usuario_online:
                # Validar que se hayan proporcionado username y password
                if not username or not password:
                    messages.error(request, 'Debes proporcionar nombre de usuario y contraseña para crear el acceso web.')
                    return redirect('gestor_clientes')
                
                # Validar longitud mínima de contraseña
                if len(password) < 8:
                    messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
                    return redirect('gestor_clientes')
                
                try:
                    # Validar que el username no exista
                    if User.objects.filter(username=username).exists():
                        messages.error(request, f'El nombre de usuario "{username}" ya existe. Por favor elige otro.')
                        cliente.delete()  # Eliminar el cliente creado
                        return redirect('gestor_clientes')
                    
                    # Validar que el email no exista en User
                    if User.objects.filter(email=email).exists():
                        messages.error(request, 'Ya existe un usuario con ese email en el sistema de citas online.')
                        cliente.delete()
                        return redirect('gestor_clientes')
                    
                    # Crear el usuario de Django con las credenciales proporcionadas
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=nombre_completo.split()[0] if nombre_completo.split() else '',
                        last_name=' '.join(nombre_completo.split()[1:]) if len(nombre_completo.split()) > 1 else ''
                    )
                    
                    # Intentar crear el perfil de cliente si existe el módulo
                    # IMPORTANTE: Sincronizar TODOS los campos del Cliente al PerfilCliente
                    try:
                        from cuentas.models import PerfilCliente
                        PerfilCliente.objects.create(
                            user=user,
                            nombre_completo=nombre_completo,
                            telefono=telefono,
                            email=email,
                            telefono_verificado=False,
                            rut=rut if rut else None,  # Sincronizar RUT
                            fecha_nacimiento=fecha_nacimiento,  # Sincronizar fecha de nacimiento
                            alergias=alergias if alergias else None  # Sincronizar alergias
                        )
                    except ImportError:
                        # El módulo de cuentas no existe, pero no es problema
                        # El usuario de Django es suficiente para hacer login
                        pass
                    
                    # Guardar las credenciales en las notas del cliente
                    notas_completas = f"{notas}\n\n[ACCESO WEB]\nUsuario: {username}\nContraseña: {password}\n(Registrado el {timezone.now().strftime('%d/%m/%Y %H:%M')})"
                    cliente.notas = notas_completas
                    cliente.save()
                    
                    # Enviar correo si se solicitó
                    if enviar_email:
                        try:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Intentando enviar correo a: {email}")
                            
                            asunto = f'Credenciales de Acceso - {nombre_completo}'
                            mensaje = f"""Hola {nombre_completo},

Se ha creado tu cuenta para reservar citas online en nuestra clínica dental.

Tus credenciales de acceso son:

Usuario: {username}
Contraseña: {password}

Puedes iniciar sesión en nuestro portal de citas online y cambiar tu contraseña en cualquier momento.

Esperamos verte pronto!

Saludos,
Equipo de la Clinica Dental
"""
                            
                            send_mail(
                                asunto,
                                mensaje,
                                settings.DEFAULT_FROM_EMAIL,
                                [email],
                                fail_silently=False,
                            )
                            
                            logger.info(f"Correo enviado exitosamente a: {email}")
                            
                            messages.success(
                                request,
                                f'✅ Cliente {nombre_completo} creado exitosamente. '
                                f'Usuario web: {username}. '
                                f'📧 Correo con credenciales enviado a {email}.'
                            )
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
                            
                            messages.error(
                                request,
                                f'⚠️ Cliente creado exitosamente, pero NO se pudo enviar el correo. '
                                f'Error: {str(e)}. '
                                f'Las credenciales están guardadas en las notas del cliente.'
                            )
                    else:
                        messages.success(
                            request,
                            f'✅ Cliente {nombre_completo} creado exitosamente. '
                            f'Usuario web: {username}. '
                            f'Las credenciales están guardadas en las notas.'
                        )
                    
                except Exception as e:
                    # Si falla la creación del usuario web, eliminar el cliente
                    cliente.delete()
                    messages.error(
                        request,
                        f'Error al crear el usuario web: {str(e)}'
                    )
                    return redirect('gestor_clientes')
            else:
                messages.success(request, f'Cliente {nombre_completo} creado exitosamente.')
            
            return redirect('gestor_clientes')
            
        except Exception as e:
            messages.error(request, f'Error al crear el cliente: {str(e)}')
            return redirect('gestor_clientes')
    
    return redirect('gestor_clientes')


@login_required
def editar_cliente(request, cliente_id):
    """
    Vista para editar la información de un cliente
    También permite editar las credenciales web si existen
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'No tienes permisos para editar clientes.')
            return redirect('gestor_clientes')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('login')
    
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    if request.method == 'POST':
        try:
            from django.contrib.auth.models import User
            import re
            
            # Actualizar información del cliente
            cliente.nombre_completo = request.POST.get('nombre_completo', cliente.nombre_completo)
            
            # Actualizar RUT
            rut = request.POST.get('rut', '').strip()
            if rut:
                # Validar que el RUT no exista en otro cliente
                if Cliente.objects.filter(rut=rut).exclude(id=cliente_id).exists():
                    messages.error(request, 'Ya existe otro cliente con ese RUT.')
                    return redirect('gestor_clientes')
                cliente.rut = rut
            else:
                cliente.rut = None
            
            # Actualizar fecha de nacimiento
            fecha_nacimiento_str = request.POST.get('fecha_nacimiento', '').strip()
            if fecha_nacimiento_str:
                try:
                    from datetime import datetime
                    cliente.fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
                except ValueError:
                    messages.error(request, 'La fecha de nacimiento no tiene un formato válido.')
                    return redirect('gestor_clientes')
            else:
                cliente.fecha_nacimiento = None
            
            # Actualizar alergias
            alergias = request.POST.get('alergias', '').strip()
            cliente.alergias = alergias if alergias else None
            
            # Normalizar el número de teléfono chileno si se proporcionó uno nuevo
            telefono_raw = request.POST.get('telefono', cliente.telefono)
            telefono_normalizado = normalizar_telefono_chileno(telefono_raw)
            if not telefono_normalizado:
                messages.error(
                    request, 
                    'El número de teléfono no es válido. '
                    'Ingrese solo los 8 dígitos del celular (ejemplo: 12345678). '
                    'El sistema agregará automáticamente el 9 y el código de país (+56).'
                )
                return redirect('gestor_clientes')
            cliente.telefono = telefono_normalizado
            cliente.notas = request.POST.get('notas', cliente.notas)
            
            # Validar si se cambió el email
            email_anterior = cliente.email
            nuevo_email = request.POST.get('email')
            if nuevo_email != email_anterior:
                # Verificar que el nuevo email no exista
                if Cliente.objects.filter(email=nuevo_email).exclude(id=cliente_id).exists():
                    messages.error(request, 'Ya existe un cliente con ese email.')
                    return redirect('gestor_clientes')
                
                # Actualizar email del cliente
                cliente.email = nuevo_email
                
                # Actualizar radiografías asociadas con el email anterior
                from historial_clinico.models import Radiografia
                # Primero actualizar las que tienen el cliente asociado
                radiografias_con_cliente = Radiografia.objects.filter(
                    paciente_email=email_anterior,
                    cliente=cliente
                )
                radiografias_con_cliente.update(paciente_email=nuevo_email)
                
                # También actualizar radiografías que tienen el email anterior pero no tienen cliente asociado
                # Esto incluye todas las radiografías con ese email, independientemente del cliente
                radiografias_sin_cliente = Radiografia.objects.filter(
                    paciente_email=email_anterior,
                    cliente__isnull=True
                )
                
                # Actualizar todas las radiografías con el email anterior, asociándolas al cliente
                for radiografia in radiografias_sin_cliente:
                    radiografia.paciente_email = nuevo_email
                    radiografia.paciente_nombre = cliente.nombre_completo  # Actualizar también el nombre
                    radiografia.cliente = cliente
                    radiografia.save()
                
                # También actualizar radiografías que tienen el email pero están asociadas a otro cliente
                # o sin cliente, pero que claramente pertenecen a este cliente
                radiografias_por_email = Radiografia.objects.filter(
                    paciente_email=email_anterior
                ).exclude(cliente=cliente)
                
                # Si hay un cliente con el email anterior, actualizar esas radiografías también
                # (por si acaso hay duplicados o inconsistencias)
                for radiografia in radiografias_por_email:
                    # Solo actualizar si no tiene cliente o si el cliente es el mismo que estamos editando
                    if not radiografia.cliente or radiografia.cliente.id == cliente_id:
                        radiografia.paciente_email = nuevo_email
                        radiografia.paciente_nombre = cliente.nombre_completo
                        radiografia.cliente = cliente
                        radiografia.save()
            
            # Manejar credenciales web si existen
            nuevo_username = request.POST.get('username_web', '').strip()
            nueva_password = request.POST.get('password_web', '').strip()
            
            # Buscar si el cliente tiene usuario web
            try:
                user_web = User.objects.get(email=cliente.email)
                cambios_credenciales = []
                
                # Cambiar username si se proporcionó uno nuevo
                if nuevo_username and nuevo_username != user_web.username:
                    # Validar que el nuevo username no exista
                    if User.objects.filter(username=nuevo_username).exclude(id=user_web.id).exists():
                        messages.error(request, f'El nombre de usuario "{nuevo_username}" ya existe.')
                        return redirect('gestor_clientes')
                    
                    user_web.username = nuevo_username
                    cambios_credenciales.append(f'Usuario: {nuevo_username}')
                
                # Cambiar password si se proporcionó una nueva
                if nueva_password:
                    if len(nueva_password) < 8:
                        messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
                        return redirect('gestor_clientes')
                    
                    user_web.set_password(nueva_password)
                    cambios_credenciales.append('Contraseña actualizada')
                
                # Actualizar email del usuario si cambió
                if nuevo_email != user_web.email:
                    # Validar que el nuevo email no esté en uso por otro usuario
                    if User.objects.filter(email=nuevo_email).exclude(id=user_web.id).exists():
                        messages.error(request, 'Ya existe un usuario web con ese email.')
                        return redirect('gestor_clientes')
                    user_web.email = nuevo_email
                
                if cambios_credenciales:
                    user_web.save()
                    # Actualizar las notas con las nuevas credenciales
                    notas = cliente.notas
                    # Eliminar la sección antigua de credenciales
                    notas = re.sub(r'\[ACCESO WEB\].*?(?=\n\n|\Z)', '', notas, flags=re.DOTALL).strip()
                    # Agregar nuevas credenciales
                    info_credenciales = f"\n\n[ACCESO WEB]\nUsuario: {user_web.username}\n"
                    if nueva_password:
                        info_credenciales += f"Contraseña: {nueva_password}\n"
                    else:
                        info_credenciales += "Contraseña: [sin cambios]\n"
                    info_credenciales += f"(Actualizado el {timezone.now().strftime('%d/%m/%Y %H:%M')})"
                    cliente.notas = notas + info_credenciales
            except User.DoesNotExist:
                pass  # El cliente no tiene usuario web
            
            cliente.save()
            
            if 'cambios_credenciales' in locals() and cambios_credenciales:
                messages.success(
                    request, 
                    f'Cliente {cliente.nombre_completo} actualizado exitosamente. ' + 
                    'Cambios: ' + ', '.join(cambios_credenciales) + '.'
                )
            else:
                messages.success(request, f'Cliente {cliente.nombre_completo} actualizado exitosamente.')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el cliente: {str(e)}')
    
    return redirect('gestor_clientes')


@login_required
def obtener_cliente(request, cliente_id):
    """
    Vista AJAX para obtener los datos de un cliente
    Incluye información del usuario web si existe
    """
    try:
        from django.contrib.auth.models import User
        
        cliente = Cliente.objects.get(id=cliente_id)
        
        # Buscar si tiene usuario web
        username_web = None
        tiene_usuario_web = False
        try:
            user = User.objects.get(email=cliente.email)
            username_web = user.username
            tiene_usuario_web = True
        except User.DoesNotExist:
            pass
        
        data = {
            'success': True,
            'cliente': {
                'id': cliente.id,
                'nombre_completo': cliente.nombre_completo,
                'email': cliente.email,
                'telefono': cliente.telefono,
                'rut': cliente.rut or '',
                'fecha_nacimiento': cliente.fecha_nacimiento.strftime('%Y-%m-%d') if cliente.fecha_nacimiento else '',
                'alergias': cliente.alergias or '',
                'notas': cliente.notas or '',
                'activo': cliente.activo,
                'fecha_registro': cliente.fecha_registro.strftime('%d/%m/%Y'),
                'tiene_usuario_web': tiene_usuario_web,
                'username_web': username_web,
            }
        }
        return JsonResponse(data)
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente no encontrado'
        }, status=404)


@login_required
def obtener_citas_cliente(request, cliente_id):
    """
    Vista AJAX para obtener las citas de un cliente
    """
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        citas = Cita.objects.filter(cliente=cliente).order_by('-fecha_hora')
        
        citas_data = []
        for cita in citas:
            citas_data.append({
                'id': cita.id,
                'fecha_hora': cita.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                'estado': cita.get_estado_display(),
                'estado_class': cita.estado,
                'tipo_consulta': cita.tipo_consulta or 'No especificado',
                'dentista': cita.dentista.nombre_completo if cita.dentista else 'Sin asignar',
                'notas': cita.notas or '',
            })
        
        data = {
            'success': True,
            'cliente': {
                'nombre': cliente.nombre_completo,
                'email': cliente.email,
            },
            'citas': citas_data,
            'total_citas': len(citas_data)
        }
        return JsonResponse(data)
        
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente no encontrado'
        }, status=404)


@login_required
def toggle_estado_cliente(request, cliente_id):
    """
    Vista para activar/desactivar un cliente
    También desactiva/activa su cuenta de usuario web si existe
    ÚTIL PARA BANEAR USUARIOS PROBLEMÁTICOS
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para realizar esta acción'
            }, status=403)
    except Perfil.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos'
        }, status=403)
    
    try:
        from django.contrib.auth.models import User
        
        cliente = Cliente.objects.get(id=cliente_id)
        nuevo_estado = not cliente.activo
        cliente.activo = nuevo_estado
        cliente.save()
        
        # Buscar si existe un usuario web asociado (por email)
        try:
            user = User.objects.get(email=cliente.email)
            # Desactivar/activar también el usuario de Django
            user.is_active = nuevo_estado
            user.save()
            
            mensaje = f'Cliente {"activado" if nuevo_estado else "desactivado"} exitosamente. '
            mensaje += f'Usuario web también {"activado" if nuevo_estado else "desactivado"} (no podrá hacer login).'
        except User.DoesNotExist:
            # El cliente no tiene usuario web
            mensaje = f'Cliente {"activado" if nuevo_estado else "desactivado"} exitosamente.'
        
        return JsonResponse({
            'success': True,
            'activo': cliente.activo,
            'message': mensaje
        })
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente no encontrado'
        }, status=404)


@login_required
def eliminar_cliente(request, cliente_id):
    """
    Vista para eliminar un cliente del sistema
    También elimina su cuenta de usuario web si existe
    ESTA ACCIÓN ES PERMANENTE
    """
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para realizar esta acción'
            }, status=403)
    except Perfil.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos'
        }, status=403)
    
    try:
        from django.contrib.auth.models import User
        
        cliente = Cliente.objects.get(id=cliente_id)
        nombre_cliente = cliente.nombre_completo
        email_cliente = cliente.email
        
        # ANTES de eliminar: Manejar las citas reservadas del cliente
        citas_reservadas = cliente.citas.filter(estado='reservada')
        citas_actualizadas = 0
        
        for cita in citas_reservadas:
            # Asegurarse de que los campos de respaldo estén llenos antes de eliminar el cliente
            if not cita.paciente_nombre:
                cita.paciente_nombre = cliente.nombre_completo
            if not cita.paciente_email:
                cita.paciente_email = cliente.email
            if not cita.paciente_telefono:
                cita.paciente_telefono = cliente.telefono
            
            # Cambiar el estado de "reservada" a "disponible" para que aparezca como disponible en el calendario
            # O podrías cambiarlo a "cancelada" si prefieres
            cita.estado = 'disponible'
            cita.save()
            citas_actualizadas += 1
        
        # Verificar relaciones antes de eliminar (para debugging)
        try:
            citas_count = cliente.citas.count()
            odontogramas_count = cliente.odontogramas.count()
            radiografias_count = cliente.radiografias.count() if hasattr(cliente, 'radiografias') else 0
            mensajes_count = cliente.mensajes.count() if hasattr(cliente, 'mensajes') else 0
            evaluaciones_count = cliente.evaluaciones.count() if hasattr(cliente, 'evaluaciones') else 0
            
            # Log para debugging (opcional)
            if citas_count > 0 or odontogramas_count > 0 or radiografias_count > 0:
                print(f"Cliente {cliente_id} tiene: {citas_count} citas, {odontogramas_count} odontogramas, {radiografias_count} radiografias")
        except Exception as e:
            print(f"Error al verificar relaciones: {str(e)}")
        
        # Buscar y eliminar el usuario web asociado si existe
        usuario_web_eliminado = False
        try:
            # Usar filter().first() en lugar de get() para evitar errores si hay múltiples usuarios
            users = User.objects.filter(email=email_cliente)
            if users.exists():
                for user in users:
                    # Eliminar también el perfil de cliente si existe
                    try:
                        from cuentas.models import PerfilCliente
                        try:
                            perfil_cliente = PerfilCliente.objects.get(user=user)
                            perfil_cliente.delete()
                        except PerfilCliente.DoesNotExist:
                            pass
                        except PerfilCliente.MultipleObjectsReturned:
                            # Si hay múltiples perfiles, eliminar todos
                            PerfilCliente.objects.filter(user=user).delete()
                    except ImportError:
                        pass
                    
                    # Eliminar el usuario de Django
                    user.delete()
                    usuario_web_eliminado = True
        except Exception as e:
            # Si hay un error al eliminar el usuario, continuar con la eliminación del cliente
            print(f"Advertencia: Error al eliminar usuario web: {str(e)}")
            pass
        
        # Eliminar el cliente
        cliente.delete()
        
        # Mensaje de confirmación
        mensaje = f'Cliente "{nombre_cliente}" eliminado exitosamente.'
        if citas_actualizadas > 0:
            mensaje += f' {citas_actualizadas} cita(s) reservada(s) fueron marcadas como disponibles.'
        if usuario_web_eliminado:
            mensaje += ' Su cuenta de usuario web también fue eliminada.'
        
        return JsonResponse({
            'success': True,
            'message': mensaje,
            'citas_actualizadas': citas_actualizadas
        })
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente no encontrado'
        }, status=404)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error al eliminar cliente {cliente_id}: {error_details}")  # Para debugging
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar el cliente: {str(e)}',
            'details': str(e)  # Incluir detalles del error
        }, status=500)


# ========== GESTIÓN DE RADIOGRAFÍAS ==========

@login_required
def radiografias_listar(request):
    """Vista principal para listar pacientes con sus radiografías"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden gestionar radiografías.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Filtros de búsqueda
    search = request.GET.get('search', '')
    
    # Obtener todas las radiografías del dentista
    radiografias = Radiografia.objects.filter(dentista=perfil).select_related('cliente')

    # Obtener todos los emails únicos de pacientes que tienen radiografías
    emails_unicos = radiografias.values_list('paciente_email', flat=True).distinct()
    
    # También obtener clientes únicos que tienen radiografías asociadas
    clientes_con_radiografias = Cliente.objects.filter(
        radiografias__dentista=perfil,
        activo=True
    ).distinct()
    
    # Crear diccionario de pacientes con radiografías
    pacientes_dict = {}
    
    # Primero procesar clientes del sistema que tienen radiografías
    for cliente in clientes_con_radiografias:
        # Obtener todas las radiografías de este cliente (por relación cliente o por email)
        radiografias_cliente = radiografias.filter(
            Q(cliente=cliente) | Q(paciente_email=cliente.email)
        )
        
        if not radiografias_cliente.exists():
            continue
        
        # Usar la información actualizada del cliente
        nombre_completo = cliente.nombre_completo
        telefono = cliente.telefono or ''
        email_actual = cliente.email
        paciente_id = cliente.id
        
        # Aplicar filtro de búsqueda
        if search:
            if not (search.lower() in nombre_completo.lower() or
                    search.lower() in email_actual.lower() or
                    search.lower() in (telefono or '').lower()):
                continue
        
        # Usar el email actual del cliente como clave
        pacientes_dict[email_actual] = {
            'id': paciente_id,
            'nombre_completo': nombre_completo,
            'email': email_actual,
            'telefono': telefono,
            'total_radiografias': radiografias_cliente.count(),
            'ultima_radiografia': radiografias_cliente.order_by('-fecha_carga').first(),
        }
    
    # Luego procesar emails que no tienen cliente asociado en el sistema
    for email in emails_unicos:
        # Si ya procesamos este email (tiene cliente), saltar
        if email in pacientes_dict:
            continue
        
        # Buscar si existe un cliente en el sistema con este email (por si acaso)
        try:
            cliente = Cliente.objects.get(email=email, activo=True)
            nombre_completo = cliente.nombre_completo
            telefono = cliente.telefono or ''
            paciente_id = cliente.id
            email_actual = cliente.email
        except Cliente.DoesNotExist:
            # Si no existe cliente, obtener información de las radiografías
            primera_radiografia = radiografias.filter(paciente_email=email).first()
            if primera_radiografia:
                nombre_completo = primera_radiografia.paciente_nombre
                telefono = ''
                # Usar hash del email como ID temporal
                paciente_id = hash(email) % 1000000
                email_actual = email
            else:
                continue
        
        # Aplicar filtro de búsqueda
        if search:
            if not (search.lower() in nombre_completo.lower() or
                    search.lower() in email_actual.lower()):
                continue
        
        # Contar radiografías de este paciente
        radiografias_paciente = radiografias.filter(paciente_email=email)
        
        pacientes_dict[email_actual] = {
            'id': paciente_id,
            'nombre_completo': nombre_completo,
            'email': email_actual,
            'telefono': telefono,
            'total_radiografias': radiografias_paciente.count(),
            'ultima_radiografia': radiografias_paciente.order_by('-fecha_carga').first(),
        }
    
    # Convertir a lista y ordenar por nombre
    pacientes_con_radiografias = list(pacientes_dict.values())
    pacientes_con_radiografias.sort(key=lambda x: x['nombre_completo'])
    
    context = {
        'perfil': perfil,
        'pacientes': pacientes_con_radiografias,
        'search': search,
        'es_dentista': True
    }
    
    return render(request, 'citas/radiografias_listar.html', context)


@login_required
def radiografias_paciente(request, paciente_id):
    """Vista para ver y gestionar radiografías de un paciente específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden gestionar radiografías.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Obtener todas las radiografías del dentista
    radiografias_todas = Radiografia.objects.filter(dentista=perfil)
    
    # Intentar encontrar el paciente por ID (puede ser cliente del sistema o hash)
    paciente = None
    paciente_email = None
    
    # Primero intentar buscar como cliente del sistema
    try:
        cliente = Cliente.objects.get(id=paciente_id, activo=True)
        paciente_email = cliente.email
        paciente = {
            'id': cliente.id,
            'nombre_completo': cliente.nombre_completo,
            'email': cliente.email,
            'telefono': cliente.telefono or '',
        }
    except Cliente.DoesNotExist:
        # Si no es cliente del sistema, buscar por email en las radiografías
        # usando el hash del email
        for radiografia in radiografias_todas:
            email_hash = hash(radiografia.paciente_email) % 1000000
            if email_hash == int(paciente_id):
                paciente_email = radiografia.paciente_email
                # Buscar si hay un cliente con este email
                try:
                    cliente = Cliente.objects.get(email=paciente_email, activo=True)
                    paciente = {
                        'id': cliente.id,
                        'nombre_completo': cliente.nombre_completo,
                        'email': cliente.email,
                        'telefono': cliente.telefono or '',
                    }
                except Cliente.DoesNotExist:
                    # Si no existe cliente, usar datos de la radiografía
                    primera_radiografia = radiografias_todas.filter(paciente_email=paciente_email).first()
                    if primera_radiografia:
                        paciente = {
                            'id': int(paciente_id),
                            'nombre_completo': primera_radiografia.paciente_nombre,
                            'email': paciente_email,
                            'telefono': '',
                        }
                break
    
    if not paciente or not paciente_email:
        messages.error(request, 'No tienes permisos para ver este paciente.')
        return redirect('radiografias_listar')
    
    # Obtener todas las radiografías del paciente
    radiografias = Radiografia.objects.filter(
        dentista=perfil,
        paciente_email=paciente_email
    ).order_by('-fecha_carga')
    
    context = {
        'perfil': perfil,
        'paciente': paciente,
        'radiografias': radiografias,
        'es_dentista': True
    }
    
    return render(request, 'citas/radiografias_paciente.html', context)


@login_required
def agregar_radiografia(request, paciente_id):
    """Vista para agregar una nueva radiografía"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden agregar radiografías.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')

    # Obtener el paciente - puede ser cliente del sistema o paciente externo con radiografías
    paciente = None
    paciente_email = None
    
    # Primero intentar buscar como cliente del sistema
    try:
        cliente = Cliente.objects.get(id=paciente_id, activo=True)
        paciente_email = cliente.email
        paciente = {
            'id': cliente.id,
            'nombre_completo': cliente.nombre_completo,
            'email': cliente.email,
            'telefono': cliente.telefono or '',
        }
    except Cliente.DoesNotExist:
        # Si no es cliente del sistema, buscar por email en las radiografías del dentista
        # usando el hash del email
        radiografias_todas = Radiografia.objects.filter(dentista=perfil)
        for radiografia in radiografias_todas:
            email_hash = hash(radiografia.paciente_email) % 1000000
            if email_hash == int(paciente_id):
                paciente_email = radiografia.paciente_email
                # Buscar si hay un cliente con este email
                try:
                    cliente = Cliente.objects.get(email=paciente_email, activo=True)
                    paciente = {
                        'id': cliente.id,
                        'nombre_completo': cliente.nombre_completo,
                        'email': cliente.email,
                        'telefono': cliente.telefono or '',
                    }
                except Cliente.DoesNotExist:
                    # Si no existe cliente, usar datos de la radiografía
                    primera_radiografia = radiografias_todas.filter(paciente_email=paciente_email).first()
                    if primera_radiografia:
                        paciente = {
                            'id': int(paciente_id),
                            'nombre_completo': primera_radiografia.paciente_nombre,
                            'email': paciente_email,
                            'telefono': '',
                        }
                break
    
    if not paciente or not paciente_email:
        messages.error(request, 'No tienes permisos para agregar radiografías a este paciente.')
        return redirect('radiografias_listar')
    
    if request.method == 'POST':
        try:
            tipo = request.POST.get('tipo', 'periapical')
            descripcion = request.POST.get('descripcion', '')
            fecha_tomada = request.POST.get('fecha_tomada', '')
            imagen = request.FILES.get('imagen')
            
            if not imagen:
                messages.error(request, 'Debes seleccionar una imagen.')
                return redirect('radiografias_paciente', paciente_id=paciente_id)
            
            # Buscar si existe un cliente con ese email
            cliente_obj = None
            try:
                cliente_obj = Cliente.objects.get(email=paciente['email'], activo=True)
            except Cliente.DoesNotExist:
                pass
            
            # Crear la radiografía
            radiografia = Radiografia.objects.create(
                cliente=cliente_obj,  # Cliente del sistema (opcional)
                paciente_email=paciente['email'],
                paciente_nombre=paciente['nombre_completo'],
                dentista=perfil,
                tipo=tipo,
                descripcion=descripcion,
                imagen=imagen,
                fecha_tomada=fecha_tomada if fecha_tomada else None
            )
            
            messages.success(request, 'Radiografía agregada correctamente.')
            return redirect('radiografias_paciente', paciente_id=paciente_id)
            
        except Exception as e:
            messages.error(request, f'Error al agregar la radiografía: {str(e)}')
    
    context = {
        'perfil': perfil,
        'paciente': paciente,
        'tipos_radiografia': Radiografia.TIPO_RADIOGRAFIA_CHOICES,
        'es_dentista': True
    }
    
    return render(request, 'citas/agregar_radiografia.html', context)


@login_required
def editar_radiografia(request, radiografia_id):
    """Vista para editar una radiografía existente"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden editar radiografías.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    try:
        radiografia = Radiografia.objects.get(id=radiografia_id, dentista=perfil)
    except Radiografia.DoesNotExist:
        messages.error(request, 'Radiografía no encontrada.')
        return redirect('radiografias_listar')
    
    # Obtener paciente_id para redirección
    paciente_id = None
    if radiografia.cliente:
        paciente_id = radiografia.cliente.id
    else:
        paciente_id = hash(radiografia.paciente_email) % 1000000
    
    # Obtener citas del paciente para el selector
    citas_paciente = []
    if radiografia.cliente:
        citas_paciente = Cita.objects.filter(
            cliente=radiografia.cliente,
            estado__in=['reservada', 'completada']
        ).order_by('-fecha_hora')[:20]
    elif radiografia.paciente_email:
        # Buscar citas por email
        citas_paciente = Cita.objects.filter(
            paciente_email=radiografia.paciente_email,
            estado__in=['reservada', 'completada']
        ).order_by('-fecha_hora')[:20]
    
    if request.method == 'POST':
        try:
            tipo = request.POST.get('tipo', radiografia.tipo)
            descripcion = request.POST.get('descripcion', '')
            fecha_tomada = request.POST.get('fecha_tomada', '')
            cita_id = request.POST.get('cita', '')
            imagen = request.FILES.get('imagen')
            
            # Actualizar campos
            radiografia.tipo = tipo
            radiografia.descripcion = descripcion if descripcion else None
            radiografia.fecha_tomada = fecha_tomada if fecha_tomada else None
            
            # Actualizar cita asociada
            if cita_id:
                try:
                    cita = Cita.objects.get(id=cita_id)
                    radiografia.cita = cita
                except Cita.DoesNotExist:
                    radiografia.cita = None
            else:
                radiografia.cita = None
            
            # Actualizar imagen si se proporciona una nueva
            if imagen:
                radiografia.imagen = imagen
                # Si hay nueva imagen, eliminar anotaciones anteriores
                if radiografia.imagen_anotada:
                    radiografia.imagen_anotada.delete()
                    radiografia.imagen_anotada = None
            
            radiografia.save()
            
            messages.success(request, 'Radiografía actualizada correctamente.')
            return redirect('radiografias_paciente', paciente_id=paciente_id)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la radiografía: {str(e)}')
    
    context = {
        'perfil': perfil,
        'radiografia': radiografia,
        'paciente_id': paciente_id,
        'tipos_radiografia': Radiografia.TIPO_RADIOGRAFIA_CHOICES,
        'citas_paciente': citas_paciente,
    }
    
    return render(request, 'citas/editar_radiografia.html', context)


@login_required
def guardar_anotaciones_radiografia(request, radiografia_id):
    """Vista AJAX para guardar anotaciones de una radiografía"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            return JsonResponse({'success': False, 'error': 'No tienes permisos para guardar anotaciones.'}, status=403)
    except Perfil.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No tienes permisos.'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido.'}, status=405)
    
    try:
        radiografia = Radiografia.objects.get(id=radiografia_id, dentista=perfil)
    except Radiografia.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Radiografía no encontrada.'}, status=404)
    
    try:
        from django.core.files.base import ContentFile
        import base64
        
        # Obtener imagen base64 del canvas
        imagen_data = request.POST.get('imagen_data', '')
        if not imagen_data:
            return JsonResponse({'success': False, 'error': 'No se proporcionó imagen.'}, status=400)
        
        # Decodificar imagen base64
        if ',' in imagen_data:
            imagen_data = imagen_data.split(',')[1]
        
        image_data = base64.b64decode(imagen_data)
        image_file = ContentFile(image_data, name=f'radiografia_{radiografia_id}_anotada.png')
        
        # Eliminar imagen anterior si existe
        if radiografia.imagen_anotada:
            radiografia.imagen_anotada.delete()
        
        # Guardar nueva imagen con anotaciones
        radiografia.imagen_anotada = image_file
        radiografia.save()
        
        return JsonResponse({'success': True, 'message': 'Anotaciones guardadas correctamente.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error al guardar anotaciones: {str(e)}'}, status=500)


@login_required
def obtener_anotaciones_radiografia(request, radiografia_id):
    """Vista AJAX para obtener la imagen con anotaciones de una radiografía"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            return JsonResponse({'success': False, 'error': 'No tienes permisos.'}, status=403)
    except Perfil.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No tienes permisos.'}, status=403)
    
    try:
        radiografia = Radiografia.objects.get(id=radiografia_id, dentista=perfil)
        
        if radiografia.imagen_anotada:
            return JsonResponse({
                'success': True,
                'imagen_anotada': radiografia.imagen_anotada.url
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No hay anotaciones guardadas'
            })
            
    except Radiografia.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Radiografía no encontrada.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'}, status=500)


@login_required
def eliminar_radiografia(request, radiografia_id):
    """Vista para eliminar una radiografía"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden eliminar radiografías.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    try:
        radiografia = Radiografia.objects.get(id=radiografia_id, dentista=perfil)
        paciente_email = radiografia.paciente_email
        
        # Obtener el paciente para redirigir
        pacientes = perfil.get_pacientes_asignados()
        paciente_id = None
        for p in pacientes:
            if p['email'] == paciente_email:
                paciente_id = p['id']
                break
        
        radiografia.delete()
        messages.success(request, 'Radiografía eliminada correctamente.')
        
        if paciente_id:
            return redirect('radiografias_paciente', paciente_id=paciente_id)
        else:
            return redirect('radiografias_listar')
            
    except Radiografia.DoesNotExist:
        messages.error(request, 'Radiografía no encontrada.')
        return redirect('radiografias_listar')
    except Exception as e:
        messages.error(request, f'Error al eliminar la radiografía: {str(e)}')
        return redirect('radiografias_listar')


@login_required
def perfil_cliente(request, cliente_id):
    """Vista de perfil completo del cliente para administrativos con todos sus historiales"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden ver perfiles de clientes.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    try:
        cliente = Cliente.objects.get(id=cliente_id)
    except Cliente.DoesNotExist:
        messages.error(request, 'Cliente no encontrado.')
        return redirect('gestor_clientes')
    
    # Obtener historiales del cliente
    # Para odontogramas y radiografías, buscar tanto por cliente directo como por email
    # para incluir registros que no tienen cliente asociado pero tienen el mismo email
    from django.db.models import Q
    odontogramas = Odontograma.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=cliente.email)
    ).order_by('-fecha_creacion')
    
    radiografias = Radiografia.objects.filter(
        Q(cliente=cliente) | Q(paciente_email=cliente.email)
    ).order_by('-fecha_carga')
    
    citas = Cita.objects.filter(cliente=cliente).order_by('-fecha_hora')
    
    # Estadísticas
    estadisticas = {
        'total_citas': citas.count(),
        'citas_completadas': citas.filter(estado='completada').count(),
        'citas_pendientes': citas.filter(estado='reservada').count(),
        'total_odontogramas': odontogramas.count(),
        'total_radiografias': radiografias.count(),
        'ultima_cita': citas.first(),
        'ultimo_odontograma': odontogramas.first(),
        'ultima_radiografia': radiografias.first(),
    }
    
    context = {
        'perfil': perfil,
        'cliente': cliente,
        'odontogramas': odontogramas,
        'radiografias': radiografias,
        'citas': citas[:10],  # Últimas 10 citas
        'estadisticas': estadisticas,
        'es_admin': True
    }
    
    return render(request, 'citas/perfil_cliente.html', context)


@login_required
def enviar_radiografia_por_correo(request, radiografia_id):
    """Vista para enviar una radiografía al correo del cliente"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden enviar radiografías por correo.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    try:
        radiografia = Radiografia.objects.get(id=radiografia_id)
        cliente = radiografia.cliente
        
        # Si no hay cliente asociado, intentar buscar por email
        if not cliente:
            try:
                cliente = Cliente.objects.get(email=radiografia.paciente_email, activo=True)
            except Cliente.DoesNotExist:
                messages.error(request, 'No se encontró el cliente asociado a esta radiografía.')
                return redirect('gestor_clientes')
        
        # Verificar que el cliente tenga email
        if not cliente.email:
            messages.error(request, 'El cliente no tiene un email registrado.')
            return redirect('perfil_cliente', cliente_id=cliente.id)
        
        # Importar EmailMessage
        from django.core.mail import EmailMessage
        from django.conf import settings
        from django.utils import timezone
        
        # Preparar el mensaje profesional
        asunto = f'Radiografía Dental - {radiografia.get_tipo_display()}'
        
        mensaje = f"""
Estimado/a {cliente.nombre_completo},

Le enviamos su radiografía dental según solicitó. Esta imagen corresponde a su archivo médico y está disponible para su uso cuando la necesite.

Información de la radiografía:
- Tipo: {radiografia.get_tipo_display()}
- Fecha: {radiografia.fecha_carga.strftime('%d/%m/%Y')}
- Dentista: {radiografia.dentista.nombre_completo}
"""
        
        if radiografia.descripcion:
            mensaje += f"- Descripción: {radiografia.descripcion}\n"
        
        mensaje += f"""
Esta radiografía forma parte de su historial médico en nuestra clínica. Le recomendamos guardarla en un lugar seguro.

Si tiene alguna pregunta o necesita más información, no dude en contactarnos.

Atentamente,
Clínica Dental
"""
        
        # Crear el correo con la imagen adjunta
        email = EmailMessage(
            subject=asunto,
            body=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[cliente.email],
        )
        
        # Adjuntar la imagen de la radiografía
        try:
            if radiografia.imagen:
                email.attach_file(radiografia.imagen.path)
        except Exception as e:
            messages.warning(request, f'Error al adjuntar la imagen: {str(e)}')
        
        # Enviar el correo
        try:
            email.send(fail_silently=False)
            messages.success(request, f'Radiografía enviada correctamente al correo {cliente.email}.')
        except Exception as e:
            messages.error(request, f'Error al enviar el correo: {str(e)}. Verifique la configuración de email.')
            return redirect('perfil_cliente', cliente_id=cliente.id)
        
        return redirect('perfil_cliente', cliente_id=cliente.id)
        
    except Radiografia.DoesNotExist:
        messages.error(request, 'Radiografía no encontrada.')
        return redirect('gestor_clientes')
    except Exception as e:
        messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        return redirect('gestor_clientes')

# ==========================================
# GESTIÓN DE SERVICIOS DENTALES
# ==========================================

@login_required
def gestor_servicios(request):
    """Vista para gestionar tipos de servicios dentales"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden gestionar servicios.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    # Filtros de búsqueda
    search = request.GET.get('search', '')
    categoria = request.GET.get('categoria', '')
    estado = request.GET.get('estado', '')
    
    # Obtener servicios
    servicios = TipoServicio.objects.all()
    
    # Aplicar filtros
    if search:
        servicios = servicios.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if categoria:
        servicios = servicios.filter(categoria=categoria)
    
    if estado == 'activo':
        servicios = servicios.filter(activo=True)
    elif estado == 'inactivo':
        servicios = servicios.filter(activo=False)
    
    servicios = servicios.order_by('categoria', 'nombre')
    
    # Estadísticas
    total_servicios = TipoServicio.objects.count()
    servicios_activos = TipoServicio.objects.filter(activo=True).count()
    servicios_inactivos = TipoServicio.objects.filter(activo=False).count()
    servicios_por_categoria = TipoServicio.objects.values('categoria').annotate(
        total=Count('id')
    )
    
    estadisticas = {
        'total_servicios': total_servicios,
        'servicios_activos': servicios_activos,
        'servicios_inactivos': servicios_inactivos,
        'servicios_por_categoria': servicios_por_categoria,
    }
    
    context = {
        'perfil': perfil,
        'servicios': servicios,
        'estadisticas': estadisticas,
        'search': search,
        'categoria': categoria,
        'estado': estado,
        'categorias': TipoServicio.CATEGORIA_CHOICES,
    }
    
    return render(request, 'citas/gestor_servicios.html', context)

@login_required
def crear_servicio(request):
    """Vista para crear un nuevo servicio"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden crear servicios.')
            return redirect('gestor_servicios')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            categoria = request.POST.get('categoria', 'otros')
            precio_base = request.POST.get('precio_base', '0')
            requiere_dentista = request.POST.get('requiere_dentista') == 'on'
            duracion_estimada = request.POST.get('duracion_estimada', '')
            activo = request.POST.get('activo') == 'on'
            
            # Validaciones
            if not nombre:
                messages.error(request, 'El nombre del servicio es obligatorio.')
                return redirect('crear_servicio')
            
            try:
                precio_base = float(precio_base)
                if precio_base < 0:
                    raise ValueError('El precio debe ser positivo')
            except ValueError:
                messages.error(request, 'El precio debe ser un número válido.')
                return redirect('crear_servicio')
            
            duracion_estimada_int = None
            if duracion_estimada:
                try:
                    duracion_estimada_int = int(duracion_estimada)
                    if duracion_estimada_int < 0:
                        raise ValueError
                except ValueError:
                    messages.error(request, 'La duración estimada debe ser un número válido.')
                    return redirect('crear_servicio')
            
            # Verificar que no exista un servicio con el mismo nombre
            if TipoServicio.objects.filter(nombre=nombre).exists():
                messages.error(request, 'Ya existe un servicio con ese nombre.')
                return redirect('crear_servicio')
            
            # Crear el servicio
            servicio = TipoServicio.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                categoria=categoria,
                precio_base=precio_base,
                requiere_dentista=requiere_dentista,
                duracion_estimada=duracion_estimada_int,
                activo=activo,
                creado_por=perfil
            )
            
            messages.success(request, f'Servicio "{nombre}" creado correctamente.')
            return redirect('gestor_servicios')
            
        except Exception as e:
            messages.error(request, f'Error al crear el servicio: {str(e)}')
            return redirect('crear_servicio')
    
    context = {
        'perfil': perfil,
        'categorias': TipoServicio.CATEGORIA_CHOICES,
    }
    
    return render(request, 'citas/crear_servicio.html', context)

@login_required
def editar_servicio(request, servicio_id):
    """Vista para editar un servicio existente"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden editar servicios.')
            return redirect('gestor_servicios')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    servicio = get_object_or_404(TipoServicio, id=servicio_id)
    
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            categoria = request.POST.get('categoria', 'otros')
            precio_base = request.POST.get('precio_base', '0')
            requiere_dentista = request.POST.get('requiere_dentista') == 'on'
            duracion_estimada = request.POST.get('duracion_estimada', '')
            activo = request.POST.get('activo') == 'on'
            
            # Validaciones
            if not nombre:
                messages.error(request, 'El nombre del servicio es obligatorio.')
                return redirect('editar_servicio', servicio_id=servicio_id)
            
            try:
                precio_base = float(precio_base)
                if precio_base < 0:
                    raise ValueError('El precio debe ser positivo')
            except ValueError:
                messages.error(request, 'El precio debe ser un número válido.')
                return redirect('editar_servicio', servicio_id=servicio_id)
            
            duracion_estimada_int = None
            if duracion_estimada:
                try:
                    duracion_estimada_int = int(duracion_estimada)
                    if duracion_estimada_int < 0:
                        raise ValueError
                except ValueError:
                    messages.error(request, 'La duración estimada debe ser un número válido.')
                    return redirect('editar_servicio', servicio_id=servicio_id)
            
            # Verificar que no exista otro servicio con el mismo nombre (excepto el actual)
            if TipoServicio.objects.filter(nombre=nombre).exclude(id=servicio_id).exists():
                messages.error(request, 'Ya existe otro servicio con ese nombre.')
                return redirect('editar_servicio', servicio_id=servicio_id)
            
            # Actualizar el servicio
            servicio.nombre = nombre
            servicio.descripcion = descripcion
            servicio.categoria = categoria
            servicio.precio_base = precio_base
            servicio.requiere_dentista = requiere_dentista
            servicio.duracion_estimada = duracion_estimada_int
            servicio.activo = activo
            servicio.save()
            
            messages.success(request, f'Servicio "{nombre}" actualizado correctamente.')
            return redirect('gestor_servicios')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el servicio: {str(e)}')
            return redirect('editar_servicio', servicio_id=servicio_id)
    
    context = {
        'perfil': perfil,
        'servicio': servicio,
        'categorias': TipoServicio.CATEGORIA_CHOICES,
    }
    
    return render(request, 'citas/editar_servicio.html', context)

@login_required
def eliminar_servicio(request, servicio_id):
    """Vista para eliminar un servicio"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden eliminar servicios.')
            return redirect('gestor_servicios')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    servicio = get_object_or_404(TipoServicio, id=servicio_id)
    
    if request.method == 'POST':
        nombre_servicio = servicio.nombre
        
        # Verificar si hay citas asociadas a este servicio
        citas_asociadas = Cita.objects.filter(tipo_servicio=servicio).count()
        if citas_asociadas > 0:
            messages.warning(
                request, 
                f'No se puede eliminar el servicio "{nombre_servicio}" porque tiene {citas_asociadas} cita(s) asociada(s). '
                'Desactive el servicio en lugar de eliminarlo.'
            )
            return redirect('gestor_servicios')
        
        try:
            servicio.delete()
            messages.success(request, f'Servicio "{nombre_servicio}" eliminado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar el servicio: {str(e)}')
        
        return redirect('gestor_servicios')
    
    context = {
        'perfil': perfil,
        'servicio': servicio,
    }
    
    return render(request, 'citas/eliminar_servicio.html', context)

# ==========================================
# GESTIÓN DE HORARIOS DE DENTISTAS
# ==========================================

@login_required
def gestor_horarios(request):
    """Vista para que el administrador gestione horarios de dentistas"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden gestionar horarios.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    # Obtener todos los dentistas
    dentistas = Perfil.objects.filter(rol='dentista', activo=True).order_by('nombre_completo')
    
    # Obtener horarios agrupados por dentista
    horarios_por_dentista = {}
    for dentista in dentistas:
        horarios = HorarioDentista.objects.filter(dentista=dentista, activo=True).order_by('dia_semana', 'hora_inicio')
        horarios_por_dentista[dentista.id] = horarios
    
    context = {
        'perfil': perfil,
        'dentistas': dentistas,
        'horarios_por_dentista': horarios_por_dentista,
        'dias_semana': HorarioDentista.DIA_SEMANA_CHOICES,
    }
    return render(request, 'citas/gestor_horarios.html', context)

@login_required
def gestionar_horario_dentista(request, dentista_id):
    """Vista para que el administrador gestione el horario de un dentista específico"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_administrativo():
            messages.error(request, 'Solo los administrativos pueden gestionar horarios.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    dentista = get_object_or_404(Perfil, id=dentista_id, rol='dentista')
    
    if request.method == 'POST':
        # Eliminar horarios existentes si se envía el formulario
        if 'eliminar_horarios' in request.POST:
            horarios_ids = request.POST.getlist('horarios_a_eliminar')
            HorarioDentista.objects.filter(id__in=horarios_ids, dentista=dentista).delete()
            messages.success(request, 'Horarios eliminados correctamente.')
            return redirect('gestionar_horario_dentista', dentista_id=dentista_id)
        
        # Agregar nuevo horario
        dia_semana = request.POST.get('dia_semana')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        
        if dia_semana and hora_inicio and hora_fin:
            try:
                horario = HorarioDentista.objects.create(
                    dentista=dentista,
                    dia_semana=int(dia_semana),
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    activo=True
                )
                messages.success(request, f'Horario agregado: {horario.get_dia_semana_display()} {hora_inicio}-{hora_fin}')
            except Exception as e:
                messages.error(request, f'Error al crear horario: {str(e)}')
        
        return redirect('gestionar_horario_dentista', dentista_id=dentista_id)
    
    # Obtener horarios del dentista agrupados por día
    horarios = HorarioDentista.objects.filter(dentista=dentista).order_by('dia_semana', 'hora_inicio')
    horarios_por_dia = {}
    for dia_num, dia_nombre in HorarioDentista.DIA_SEMANA_CHOICES:
        horarios_por_dia[dia_num] = horarios.filter(dia_semana=dia_num)
    
    context = {
        'perfil': perfil,
        'dentista': dentista,
        'horarios_por_dia': horarios_por_dia,
        'dias_semana': HorarioDentista.DIA_SEMANA_CHOICES,
    }
    return render(request, 'citas/gestionar_horario_dentista.html', context)

@login_required
def ver_mi_horario(request):
    """Vista para que el dentista vea su horario (solo lectura)"""
    try:
        perfil = Perfil.objects.get(user=request.user)
        if not perfil.es_dentista():
            messages.error(request, 'Solo los dentistas pueden ver su horario.')
            return redirect('panel_trabajador')
    except Perfil.DoesNotExist:
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('login')
    
    # Obtener horarios del dentista agrupados por día
    horarios = HorarioDentista.objects.filter(dentista=perfil, activo=True).order_by('dia_semana', 'hora_inicio')
    horarios_por_dia = {}
    for dia_num, dia_nombre in HorarioDentista.DIA_SEMANA_CHOICES:
        horarios_por_dia[dia_num] = horarios.filter(dia_semana=dia_num)
    
    context = {
        'perfil': perfil,
        'horarios_por_dia': horarios_por_dia,
        'dias_semana': HorarioDentista.DIA_SEMANA_CHOICES,
    }
    return render(request, 'citas/ver_mi_horario.html', context)
