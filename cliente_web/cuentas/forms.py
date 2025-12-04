from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import PerfilCliente
import re

def _normalizar_telefono_chile_form(telefono: str | None) -> str | None:
    if not telefono:
        return None
    t = telefono.strip()
    if t.startswith('+'):
        limpio = '+' + re.sub(r"\D", "", t[1:])
    else:
        limpio = re.sub(r"\D", "", t)
    if limpio.startswith('+56'):
        return limpio
    if limpio.startswith('56'):
        return '+' + limpio
    limpio = limpio.lstrip('0')
    if limpio.startswith('9') and len(limpio) == 9:
        return '+56' + limpio
    if len(limpio) in (8, 9):
        return '+56' + limpio
    return None

class RegistroClienteForm(UserCreationForm):
    nombre_completo = forms.CharField(max_length=150, required=True, label="Nombre Completo")
    telefono = forms.CharField(max_length=20, required=True)
    email = forms.EmailField(required=True)
    rut = forms.CharField(
        max_length=12,
        required=True,
        label="RUT",
        help_text="Formato: 12345678-9 (obligatorio)"
    )
    fecha_nacimiento = forms.DateField(
        required=True,
        label="Fecha de Nacimiento",
        help_text="Formato: DD/MM/YYYY (obligatorio)",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    alergias = forms.CharField(
        required=True,
        label="Alergias",
        help_text="Lista de alergias conocidas (medicamentos, materiales dentales, anestesia, etc.). MUY IMPORTANTE para su seguridad. Si no tiene alergias, escriba 'Ninguna'.",
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ejemplo: Penicilina, látex, anestesia local... (si no tiene alergias, escriba "Ninguna")'})
    )
    metodo_verificacion = forms.ChoiceField(
        choices=[
            ('email', '📧 Recibir código por Email'),
            ('whatsapp', '💬 Recibir código por WhatsApp'),
        ],
        required=True,
        label="Método de Verificación",
        help_text="Elige cómo quieres recibir tu código de verificación",
        widget=forms.RadioSelect(attrs={'class': 'metodo-verificacion'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'nombre_completo', 'telefono', 'rut', 'fecha_nacimiento', 'alergias', 'metodo_verificacion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Todos los campos son obligatorios
        self.fields['email'].required = True
        # Simplificar las validaciones de contraseña
        self.fields['password1'].help_text = "Cualquier contraseña (mínimo 1 carácter)"
        self.fields['password2'].help_text = "Repite la misma contraseña"
        # Configurar campo de teléfono
        self.fields['telefono'].widget.attrs.update({
            'maxlength': '8',
            'pattern': '[0-9]{8}',
            'placeholder': '12345678'
        })
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("El nombre de usuario es obligatorio")
        
        # Verificar que el username no esté ya registrado
        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso. Por favor, elige otro.")
        
        return username

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono')
        if not tel:
            raise forms.ValidationError("El teléfono es obligatorio para la verificación")
        
        # Solo permitir 8 dígitos
        tel_limpio = re.sub(r'\D', '', tel)
        if len(tel_limpio) != 8:
            raise forms.ValidationError("El teléfono debe tener exactamente 8 dígitos (número celular chileno)")
        
        # Verificar que solo sean números
        if not tel_limpio.isdigit():
            raise forms.ValidationError("El teléfono solo debe contener números")
        
        normalizado = _normalizar_telefono_chile_form(tel_limpio)
        if not normalizado:
            raise forms.ValidationError("Ingresa un teléfono válido de Chile (8 dígitos)")
        return tel_limpio
    
    def clean_rut(self):
        rut = self.cleaned_data.get('rut', '').strip()
        if not rut:
            raise forms.ValidationError("El RUT es obligatorio")
        # Validar formato básico de RUT chileno (12345678-9)
        import re
        if not re.match(r'^\d{7,8}-[\dkK]$', rut):
            raise forms.ValidationError("El RUT debe tener el formato: 12345678-9 (con guión y dígito verificador)")
        
        # Verificar que el RUT no esté ya registrado
        from .models import PerfilCliente
        if PerfilCliente.objects.filter(rut=rut).exists():
            raise forms.ValidationError("Este RUT ya está registrado en el sistema. Si ya tienes cuenta, inicia sesión.")
        
        return rut
    
    def clean_nombre_completo(self):
        nombre_completo = self.cleaned_data.get('nombre_completo', '').strip()
        if not nombre_completo:
            raise forms.ValidationError("El nombre completo es obligatorio")
        return nombre_completo
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("El email es obligatorio")
        return email
    
    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
        if not fecha_nacimiento:
            raise forms.ValidationError("La fecha de nacimiento es obligatoria")
        return fecha_nacimiento
    
    def clean_alergias(self):
        alergias = self.cleaned_data.get('alergias', '').strip()
        if not alergias:
            raise forms.ValidationError("Las alergias son obligatorias. Si no tiene alergias, escriba 'Ninguna'")
        return alergias

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1 and len(password1) < 1:
            raise forms.ValidationError("La contraseña debe tener al menos 1 carácter")
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Normalizar el teléfono si se proporcionó
            telefono = self.cleaned_data.get('telefono')
            if telefono:
                telefono_normalizado = _normalizar_telefono_chile_form(telefono)
            else:
                telefono_normalizado = '+56912345678'  # Valor por defecto
            
            # Crear el perfil del cliente con los datos proporcionados o valores por defecto
            PerfilCliente.objects.create(
                user=user,
                nombre_completo=self.cleaned_data.get('nombre_completo', f'Cliente {user.username}'),
                telefono=telefono_normalizado,
                email=self.cleaned_data.get('email', f'{user.username}@test.com'),
                rut=self.cleaned_data.get('rut'),
                fecha_nacimiento=self.cleaned_data.get('fecha_nacimiento'),
                alergias=self.cleaned_data.get('alergias')
            )
        return user
