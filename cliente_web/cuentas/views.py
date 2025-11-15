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
            # Crear usuario directamente sin verificación
            from django.contrib.auth.models import User
            
            try:
                # Normalizar teléfono
                telefono_normalizado = _normalizar_telefono_chile(form.cleaned_data['telefono'])
                
                # Crear usuario
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password1']
                )
                
                # Crear perfil (sin verificación de teléfono)
                perfil_cliente = PerfilCliente.objects.create(
                    user=user,
                    nombre_completo=form.cleaned_data['nombre_completo'] or '',
                    telefono=telefono_normalizado,
                    email=form.cleaned_data['email'] or '',
                    telefono_verificado=False,  # No verificado para pruebas rápidas
                    rut=form.cleaned_data.get('rut'),
                    fecha_nacimiento=form.cleaned_data.get('fecha_nacimiento'),
                    alergias=form.cleaned_data.get('alergias')
                )
                
                # IMPORTANTE: Crear automáticamente el Cliente en el sistema de gestión
                # Esto asegura que ambos sistemas estén sincronizados
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
                    # Si no se puede importar el modelo Cliente, continuar sin error
                    # (puede ser que estén en diferentes bases de datos en producción)
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"No se pudo crear Cliente automáticamente para {perfil_cliente.email}")
                except Exception as e:
                    # Si hay error al crear Cliente, registrar pero no fallar el registro
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al crear Cliente automáticamente: {str(e)}")
                    # Continuar con el registro del usuario aunque falle la creación del Cliente
                
                # Iniciar sesión automáticamente (especificar backend)
                from django.contrib.auth import login
                from django.contrib.auth.backends import ModelBackend
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.success(request, '¡Cuenta creada correctamente! Bienvenido.')
                return redirect('panel_cliente')
                
            except Exception as e:
                print(f"Error en registro: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al crear la cuenta: {str(e)}')
                return render(request, 'cuentas/registro_cliente.html', {'form': form})
    else:
        form = RegistroClienteForm()
    return render(request, 'cuentas/registro_cliente.html', {'form': form})

# ========================================
# FUNCIONES DE VERIFICACIÓN DESACTIVADAS
# Descomentarlas si se quiere reactivar la verificación por teléfono
# ========================================

# def verificar_telefono(request):
#     """Vista para verificar el código de teléfono durante el registro."""
#     if 'registro_data' not in request.session:
#         messages.error(request, 'Sesión de registro expirada. Por favor, regístrate nuevamente.')
#         return redirect('registro_cliente')
#     
#     registro_data = request.session['registro_data']
#     telefono_normalizado = _normalizar_telefono_chile(registro_data['telefono'])
#     
#     if request.method == 'POST':
#         codigo_ingresado = request.POST.get('codigo', '').strip()
#         
#         if not codigo_ingresado:
#             messages.error(request, 'Por favor ingresa el código de verificación.')
#             return render(request, 'cuentas/verificar_telefono.html', {
#                 'telefono': telefono_normalizado,
#                 'registro_data': registro_data
#             })
#         
#         # Buscar código de verificación
#         try:
#             codigo_obj = CodigoVerificacion.objects.filter(
#                 telefono=telefono_normalizado,
#                 verificado=False
#             ).first()
#             
#             if not codigo_obj:
#                 messages.error(request, 'Código no encontrado. Solicita uno nuevo.')
#                 return render(request, 'cuentas/verificar_telefono.html', {
#                     'telefono': telefono_normalizado,
#                     'registro_data': registro_data
#                 })
#             
#             if codigo_obj.verificar(codigo_ingresado):
#                 # Código correcto, crear usuario
#                 from django.contrib.auth.models import User
#                 
#                 user = User.objects.create_user(
#                     username=registro_data['username'],
#                     email=registro_data['email'],
#                     password=registro_data['password']
#                 )
#                 
#                 # Crear perfil con teléfono verificado
#                 PerfilCliente.objects.create(
#                     user=user,
#                     nombre_completo=registro_data['nombre_completo'] or '',
#                     telefono=telefono_normalizado,
#                     email=registro_data['email'] or '',
#                     telefono_verificado=True
#                 )
#                 
#                 # Limpiar sesión
#                 del request.session['registro_data']
#                 
#                 # Iniciar sesión automáticamente
#                 login(request, user)
#                 
#                 messages.success(request, '¡Cuenta creada y verificada correctamente!')
#                 return redirect('panel_cliente')
#             else:
#                 if codigo_obj.intentos >= 3:
#                     messages.error(request, 'Demasiados intentos fallidos. Solicita un nuevo código.')
#                     codigo_obj.delete()
#                 else:
#                     messages.error(request, f'Código incorrecto. Intentos restantes: {3 - codigo_obj.intentos}')
#                 
#         except Exception as e:
#             messages.error(request, f'Error al verificar código: {str(e)}')
#     
#     return render(request, 'cuentas/verificar_telefono.html', {
#         'telefono': telefono_normalizado,
#         'registro_data': registro_data
#     })


# @csrf_exempt
# def reenviar_codigo(request):
#     """Vista AJAX para reenviar código de verificación."""
#     if request.method == 'POST' and 'registro_data' in request.session:
#         registro_data = request.session['registro_data']
#         telefono_normalizado = _normalizar_telefono_chile(registro_data['telefono'])
#         
#         try:
#             # Generar nuevo código
#             codigo_obj = CodigoVerificacion.generar_codigo(telefono_normalizado)
#             enviar_codigo_verificacion(telefono_normalizado, codigo_obj.codigo)
#             
#             return JsonResponse({
#                 'success': True,
#                 'message': f'Código reenviado al {telefono_normalizado}'
#             })
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'message': f'Error al reenviar código: {str(e)}'
#             })
#     
#     return JsonResponse({
#         'success': False,
#         'message': 'Sesión de registro no encontrada'
#     })


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
                
                # Verificar el estado del cliente en citas_cliente del sistema de gestión
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
                    logger.error(f"Error al verificar cliente en citas_cliente: {e}")
                
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




