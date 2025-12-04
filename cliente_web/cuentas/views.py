from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import RegistroClienteForm
from .models import CodigoVerificacion, PerfilCliente
from reservas.sms_service import enviar_codigo_verificacion
from reservas.sms_service import _normalizar_telefono_chile
from reservas.documentos_models import ClienteDocumento

def registro_cliente(request):
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            # Guardar datos en sesión para verificación
            telefono_normalizado = _normalizar_telefono_chile(form.cleaned_data['telefono'])
            metodo_verificacion = form.cleaned_data.get('metodo_verificacion', 'email')
            email = form.cleaned_data['email']
            
            # Generar código de verificación
            try:
                codigo_obj = CodigoVerificacion.generar_codigo(telefono_normalizado)
                
                # Enviar código según el método seleccionado
                try:
                    from reservas.twilio_service import enviar_codigo_por_whatsapp, enviar_codigo_por_email
                    
                    if metodo_verificacion == 'whatsapp':
                        enviar_codigo_por_whatsapp(telefono_normalizado, codigo_obj.codigo)
                        mensaje_exito = f'Código de verificación enviado por WhatsApp al {telefono_normalizado}. Por favor, revisa tu WhatsApp e ingresa el código recibido.'
                    else:  # email
                        enviar_codigo_por_email(email, codigo_obj.codigo)
                        mensaje_exito = f'Código de verificación enviado por email a {email}. Por favor, revisa tu correo e ingresa el código recibido.'
                    
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al enviar código de verificación: {str(e)}")
                    messages.error(request, f'Error al enviar código de verificación: {str(e)}. Por favor, verifica tus datos e intenta nuevamente.')
                    return render(request, 'cuentas/registro_cliente.html', {'form': form})
                
                # Guardar datos del formulario en sesión
                request.session['registro_data'] = {
                    'username': form.cleaned_data['username'],
                    'email': form.cleaned_data['email'],
                    'password': form.cleaned_data['password1'],
                    'nombre_completo': form.cleaned_data['nombre_completo'],
                    'telefono': form.cleaned_data['telefono'],
                    'rut': form.cleaned_data.get('rut'),
                    'fecha_nacimiento': form.cleaned_data.get('fecha_nacimiento').isoformat() if form.cleaned_data.get('fecha_nacimiento') else None,
                    'alergias': form.cleaned_data.get('alergias'),
                    'metodo_verificacion': metodo_verificacion,
                }
                
                messages.success(request, mensaje_exito)
                return redirect('verificar_telefono')
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error al generar código de verificación: {str(e)}")
                messages.error(request, f'Error al generar código de verificación: {str(e)}')
                return render(request, 'cuentas/registro_cliente.html', {'form': form})
    else:
        form = RegistroClienteForm()
    return render(request, 'cuentas/registro_cliente.html', {'form': form})

# ========================================
# FUNCIONES DE VERIFICACIÓN ACTIVADAS
# ========================================

def verificar_telefono(request):
    """Vista para verificar el código de teléfono durante el registro."""
    if 'registro_data' not in request.session:
        messages.error(request, 'Sesión de registro expirada. Por favor, regístrate nuevamente.')
        return redirect('registro_cliente')
    
    registro_data = request.session['registro_data']
    telefono_normalizado = _normalizar_telefono_chile(registro_data['telefono'])
    
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo', '').strip()
        
        if not codigo_ingresado:
            messages.error(request, 'Por favor ingresa el código de verificación.')
            return render(request, 'cuentas/verificar_telefono.html', {
                'telefono': telefono_normalizado,
                'registro_data': registro_data
            })
        
        # Buscar código de verificación
        try:
            codigo_obj = CodigoVerificacion.objects.filter(
                telefono=telefono_normalizado,
                verificado=False
            ).order_by('-creado_el').first()
            
            if not codigo_obj:
                messages.error(request, 'Código no encontrado. Solicita uno nuevo.')
                return render(request, 'cuentas/verificar_telefono.html', {
                    'telefono': telefono_normalizado,
                    'registro_data': registro_data
                })
            
            if codigo_obj.verificar(codigo_ingresado):
                # Código correcto, crear usuario
                from django.contrib.auth.models import User
                from datetime import datetime
                
                user = User.objects.create_user(
                    username=registro_data['username'],
                    email=registro_data['email'],
                    password=registro_data['password']
                )
                
                # Convertir fecha_nacimiento de string a date si existe
                fecha_nacimiento = None
                if registro_data.get('fecha_nacimiento'):
                    try:
                        fecha_nacimiento = datetime.fromisoformat(registro_data['fecha_nacimiento']).date()
                    except:
                        pass
                
                # Crear perfil con teléfono verificado
                perfil_cliente = PerfilCliente.objects.create(
                    user=user,
                    nombre_completo=registro_data['nombre_completo'] or '',
                    telefono=telefono_normalizado,
                    email=registro_data['email'] or '',
                    telefono_verificado=True,
                    rut=registro_data.get('rut'),
                    fecha_nacimiento=fecha_nacimiento,
                    alergias=registro_data.get('alergias')
                )
                
                # IMPORTANTE: Crear automáticamente el Cliente en el sistema de gestión
                try:
                    from pacientes.models import Cliente
                    
                    # Verificar si ya existe un Cliente con este email
                    if not Cliente.objects.filter(email=perfil_cliente.email).exists():
                        Cliente.objects.create(
                            nombre_completo=perfil_cliente.nombre_completo,
                            email=perfil_cliente.email,
                            telefono=perfil_cliente.telefono,
                            rut=perfil_cliente.rut,
                            fecha_nacimiento=perfil_cliente.fecha_nacimiento,
                            alergias=perfil_cliente.alergias,
                            activo=True,
                            notas=f'Cliente registrado desde la página web. Usuario: {user.username}'
                        )
                except ImportError:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"No se pudo crear Cliente automáticamente para {perfil_cliente.email}")
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al crear Cliente automáticamente: {str(e)}")
                
                # Limpiar sesión
                del request.session['registro_data']
                
                # Iniciar sesión automáticamente
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.success(request, '¡Cuenta creada y verificada correctamente! Bienvenido.')
                return redirect('panel_cliente')
            else:
                if codigo_obj.intentos >= 3:
                    messages.error(request, 'Demasiados intentos fallidos. Solicita un nuevo código.')
                    codigo_obj.delete()
                else:
                    messages.error(request, f'Código incorrecto. Intentos restantes: {3 - codigo_obj.intentos}')
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al verificar código: {str(e)}")
            messages.error(request, f'Error al verificar código: {str(e)}')
    
    return render(request, 'cuentas/verificar_telefono.html', {
        'telefono': telefono_normalizado,
        'registro_data': registro_data
    })


@csrf_exempt
def reenviar_codigo(request):
    """Vista AJAX para reenviar código de verificación."""
    if request.method == 'POST' and 'registro_data' in request.session:
        registro_data = request.session['registro_data']
        telefono_normalizado = _normalizar_telefono_chile(registro_data['telefono'])
        
        try:
            # Generar nuevo código
            codigo_obj = CodigoVerificacion.generar_codigo(telefono_normalizado)
            enviar_codigo_verificacion(telefono_normalizado, codigo_obj.codigo)
            
            return JsonResponse({
                'success': True,
                'message': f'Código reenviado al {telefono_normalizado}'
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al reenviar código: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error al reenviar código: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Sesión de registro no encontrada'
    })


@csrf_exempt
def validar_username(request):
    """Vista AJAX para validar si un username está disponible."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        
        if not username:
            return JsonResponse({'disponible': False, 'mensaje': 'El nombre de usuario es obligatorio'})
        
        from django.contrib.auth.models import User
        disponible = not User.objects.filter(username=username).exists()
        
        return JsonResponse({'disponible': disponible})
    
    return JsonResponse({'disponible': False})


@csrf_exempt
def validar_email(request):
    """Vista AJAX para validar si un email está disponible."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({'disponible': False, 'mensaje': 'El email es obligatorio'})
        
        from django.contrib.auth.models import User
        disponible = not User.objects.filter(email=email).exists()
        
        # También verificar en PerfilCliente
        if disponible:
            disponible = not PerfilCliente.objects.filter(email=email).exists()
        
        return JsonResponse({'disponible': disponible})
    
    return JsonResponse({'disponible': False})


@csrf_exempt
def validar_rut(request):
    """Vista AJAX para validar si un RUT está disponible."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        rut = data.get('rut', '').strip()
        
        if not rut:
            return JsonResponse({'disponible': False, 'mensaje': 'El RUT es obligatorio'})
        
        disponible = not PerfilCliente.objects.filter(rut=rut).exists()
        
        return JsonResponse({'disponible': disponible})
    
    return JsonResponse({'disponible': False})


@csrf_exempt
def validar_telefono(request):
    """Vista AJAX para validar si un teléfono está disponible."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        telefono = data.get('telefono', '').strip()
        
        if not telefono:
            return JsonResponse({'disponible': False, 'mensaje': 'El teléfono es obligatorio'})
        
        # Normalizar teléfono para comparar
        telefono_normalizado = _normalizar_telefono_chile(telefono)
        
        if not telefono_normalizado:
            return JsonResponse({'disponible': False, 'mensaje': 'Teléfono inválido'})
        
        disponible = not PerfilCliente.objects.filter(telefono=telefono_normalizado).exists()
        
        return JsonResponse({'disponible': disponible})
    
    return JsonResponse({'disponible': False})


def login_cliente(request):
    """
    Vista de login personalizada que verifica que el cliente exista en el sistema de gestión.
    """
    if request.user.is_authenticated:
        return redirect('panel_cliente')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Autenticar usuario
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Verificar que tenga PerfilCliente
                try:
                    perfil = PerfilCliente.objects.get(user=user)
                except PerfilCliente.DoesNotExist:
                    messages.error(request, 'Tu cuenta no está configurada correctamente. Por favor, contacta al administrador.')
                    return render(request, 'cuentas/login.html', {'form': form})
                
                # Verificar el estado del cliente en pacientes_cliente del sistema de gestión
                # IMPORTANTE: Solo bloquear si el cliente existe pero está INACTIVO (fue borrado)
                # Si no existe, permitir login (puede ser un registro nuevo que aún no se sincronizó)
                try:
                    # Buscar por email
                    cliente_doc = ClienteDocumento.objects.filter(email=perfil.email).first()
                    if not cliente_doc:
                        # Si no se encuentra por email, intentar por nombre completo
                        cliente_doc = ClienteDocumento.objects.filter(nombre_completo=perfil.nombre_completo).first()
                    
                    if cliente_doc:
                        # Cliente existe en el sistema de gestión
                        if not cliente_doc.activo:
                            # Cliente fue borrado/desactivado en el sistema de gestión
                            messages.error(request, 'Tu cuenta ha sido desactivada en el sistema de gestión. Por favor, contacta a la clínica.')
                            return render(request, 'cuentas/login.html', {'form': form})
                        # Si está activo, continuar con el login
                    # Si no existe, permitir login (puede ser registro nuevo)
                except Exception as e:
                    # En caso de error, permitir login pero registrar el error
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al verificar cliente en pacientes_cliente: {e}")
                
                # Especificar backend al hacer login
                login(request, user, backend='cuentas.backends.ClienteBackend')
                messages.success(request, f'¡Bienvenido de nuevo, {perfil.nombre_completo or username}!')
                return redirect('panel_cliente')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'cuentas/login.html', {'form': form})


@login_required
def logout_cliente(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('login_cliente')




