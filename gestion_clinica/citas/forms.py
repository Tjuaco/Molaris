from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.html import escape
from django.utils.safestring import mark_safe
import re
from personal.models import Perfil

class RegistroTrabajadorForm(UserCreationForm):
    # Campos del usuario
    first_name = forms.CharField(
        label="Nombre",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Apellido",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    # Campos del perfil
    nombre_completo = forms.CharField(
        label="Nombre Completo",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Ingresa tu nombre completo (máximo 150 caracteres)'
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'})
    )
    rol = forms.ChoiceField(
        choices=Perfil.ROLE_CHOICES,
        label="Rol",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Campos específicos para dentistas
    especialidad = forms.CharField(
        label="Especialidad",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    numero_colegio = forms.CharField(
        label="Número de Colegio",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar mensajes de ayuda
        self.fields['username'].help_text = 'Requerido. 3-150 caracteres. Solo letras, dígitos y @/./+/-/_'
        self.fields['password1'].help_text = 'Mínimo 8 caracteres. Debe incluir letras y números.'
        self.fields['password2'].help_text = 'Ingresa la misma contraseña para verificación'
        
        # Agregar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError('El nombre de usuario es requerido.')
        
        # Sanitizar username (prevenir XSS) - strip primero, luego escape
        username = username.strip()
        
        # Validar formato de username (solo letras, números y caracteres permitidos)
        if not re.match(r'^[a-zA-Z0-9@.+\-_]+$', username):
            raise forms.ValidationError('El nombre de usuario solo puede contener letras, números y los caracteres: @ . + - _')
        
        # Validar longitud
        if len(username) < 3:
            raise forms.ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
        if len(username) > 150:
            raise forms.ValidationError('El nombre de usuario no puede tener más de 150 caracteres.')
        
        # Verificar si existe (usando get para evitar timing attacks parcialmente)
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Este nombre de usuario ya está en uso. Por favor, elige otro.')
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('El email es requerido.')
        
        # Sanitizar email - strip y lower primero
        email = email.strip().lower()
        
        # Validar formato de email más estricto
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise forms.ValidationError('Por favor, ingresa un email válido.')
        
        # Verificar longitud máxima
        if len(email) > 254:  # RFC 5321
            raise forms.ValidationError('El email es demasiado largo.')
        
        # Verificar si existe
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este email ya está registrado.')
        
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono:
            raise forms.ValidationError('El teléfono es requerido.')
        
        # Sanitizar teléfono - solo strip, no escape (es un campo de texto)
        telefono = telefono.strip()
        
        # Validación más estricta de teléfono (solo números, +, -, espacios)
        cleaned_phone = telefono.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        if not cleaned_phone.isdigit():
            raise forms.ValidationError('El teléfono debe contener solo números y los caracteres: + - ( ) espacios.')
        
        # Validar longitud mínima
        if len(cleaned_phone) < 8:
            raise forms.ValidationError('El teléfono debe tener al menos 8 dígitos.')
        if len(cleaned_phone) > 15:
            raise forms.ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('La contraseña es requerida.')
        
        # Validación de fuerza de contraseña mejorada
        if len(password1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        if len(password1) > 128:
            raise forms.ValidationError('La contraseña no puede tener más de 128 caracteres.')
        
        # Verificar que tenga al menos una letra y un número
        has_letter = re.search(r'[a-zA-Z]', password1)
        has_digit = re.search(r'\d', password1)
        
        if not has_letter:
            raise forms.ValidationError('La contraseña debe contener al menos una letra.')
        
        if not has_digit:
            raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
        # Verificar que no sea demasiado común (lista básica)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password1.lower() in common_passwords:
            raise forms.ValidationError('Esta contraseña es demasiado común. Por favor, elige una más segura.')
        
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Crear el perfil con todos los campos
            perfil_data = {
                'user': user,
                'nombre_completo': self.cleaned_data['nombre_completo'],
                'telefono': self.cleaned_data['telefono'],
                'email': user.email,
                'rol': self.cleaned_data['rol'],
            }
            
            # Agregar campos específicos para dentistas
            if self.cleaned_data['rol'] == 'dentista':
                perfil_data['especialidad'] = self.cleaned_data.get('especialidad', '')
                perfil_data['numero_colegio'] = self.cleaned_data.get('numero_colegio', '')
            
            Perfil.objects.create(**perfil_data)
        
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre_completo', 'telefono', 'email', 'rol', 'especialidad', 'numero_colegio', 'activo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos específicos de dentista opcionales para administrativos
        if self.instance.pk and self.instance.rol == 'administrativo':
            self.fields['especialidad'].required = False
            self.fields['numero_colegio'].required = False

        # Validar longitud mínima
        if len(cleaned_phone) < 8:
            raise forms.ValidationError('El teléfono debe tener al menos 8 dígitos.')
        if len(cleaned_phone) > 15:
            raise forms.ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('La contraseña es requerida.')
        
        # Validación de fuerza de contraseña mejorada
        if len(password1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        if len(password1) > 128:
            raise forms.ValidationError('La contraseña no puede tener más de 128 caracteres.')
        
        # Verificar que tenga al menos una letra y un número
        has_letter = re.search(r'[a-zA-Z]', password1)
        has_digit = re.search(r'\d', password1)
        
        if not has_letter:
            raise forms.ValidationError('La contraseña debe contener al menos una letra.')
        
        if not has_digit:
            raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
        # Verificar que no sea demasiado común (lista básica)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password1.lower() in common_passwords:
            raise forms.ValidationError('Esta contraseña es demasiado común. Por favor, elige una más segura.')
        
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Crear el perfil con todos los campos
            perfil_data = {
                'user': user,
                'nombre_completo': self.cleaned_data['nombre_completo'],
                'telefono': self.cleaned_data['telefono'],
                'email': user.email,
                'rol': self.cleaned_data['rol'],
            }
            
            # Agregar campos específicos para dentistas
            if self.cleaned_data['rol'] == 'dentista':
                perfil_data['especialidad'] = self.cleaned_data.get('especialidad', '')
                perfil_data['numero_colegio'] = self.cleaned_data.get('numero_colegio', '')
            
            Perfil.objects.create(**perfil_data)
        
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre_completo', 'telefono', 'email', 'rol', 'especialidad', 'numero_colegio', 'activo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos específicos de dentista opcionales para administrativos
        if self.instance.pk and self.instance.rol == 'administrativo':
            self.fields['especialidad'].required = False
            self.fields['numero_colegio'].required = False

        # Validar longitud mínima
        if len(cleaned_phone) < 8:
            raise forms.ValidationError('El teléfono debe tener al menos 8 dígitos.')
        if len(cleaned_phone) > 15:
            raise forms.ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('La contraseña es requerida.')
        
        # Validación de fuerza de contraseña mejorada
        if len(password1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        if len(password1) > 128:
            raise forms.ValidationError('La contraseña no puede tener más de 128 caracteres.')
        
        # Verificar que tenga al menos una letra y un número
        has_letter = re.search(r'[a-zA-Z]', password1)
        has_digit = re.search(r'\d', password1)
        
        if not has_letter:
            raise forms.ValidationError('La contraseña debe contener al menos una letra.')
        
        if not has_digit:
            raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
        # Verificar que no sea demasiado común (lista básica)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password1.lower() in common_passwords:
            raise forms.ValidationError('Esta contraseña es demasiado común. Por favor, elige una más segura.')
        
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Crear el perfil con todos los campos
            perfil_data = {
                'user': user,
                'nombre_completo': self.cleaned_data['nombre_completo'],
                'telefono': self.cleaned_data['telefono'],
                'email': user.email,
                'rol': self.cleaned_data['rol'],
            }
            
            # Agregar campos específicos para dentistas
            if self.cleaned_data['rol'] == 'dentista':
                perfil_data['especialidad'] = self.cleaned_data.get('especialidad', '')
                perfil_data['numero_colegio'] = self.cleaned_data.get('numero_colegio', '')
            
            Perfil.objects.create(**perfil_data)
        
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre_completo', 'telefono', 'email', 'rol', 'especialidad', 'numero_colegio', 'activo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos específicos de dentista opcionales para administrativos
        if self.instance.pk and self.instance.rol == 'administrativo':
            self.fields['especialidad'].required = False
            self.fields['numero_colegio'].required = False

        # Validar longitud mínima
        if len(cleaned_phone) < 8:
            raise forms.ValidationError('El teléfono debe tener al menos 8 dígitos.')
        if len(cleaned_phone) > 15:
            raise forms.ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('La contraseña es requerida.')
        
        # Validación de fuerza de contraseña mejorada
        if len(password1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        if len(password1) > 128:
            raise forms.ValidationError('La contraseña no puede tener más de 128 caracteres.')
        
        # Verificar que tenga al menos una letra y un número
        has_letter = re.search(r'[a-zA-Z]', password1)
        has_digit = re.search(r'\d', password1)
        
        if not has_letter:
            raise forms.ValidationError('La contraseña debe contener al menos una letra.')
        
        if not has_digit:
            raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
        # Verificar que no sea demasiado común (lista básica)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password1.lower() in common_passwords:
            raise forms.ValidationError('Esta contraseña es demasiado común. Por favor, elige una más segura.')
        
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Crear el perfil con todos los campos
            perfil_data = {
                'user': user,
                'nombre_completo': self.cleaned_data['nombre_completo'],
                'telefono': self.cleaned_data['telefono'],
                'email': user.email,
                'rol': self.cleaned_data['rol'],
            }
            
            # Agregar campos específicos para dentistas
            if self.cleaned_data['rol'] == 'dentista':
                perfil_data['especialidad'] = self.cleaned_data.get('especialidad', '')
                perfil_data['numero_colegio'] = self.cleaned_data.get('numero_colegio', '')
            
            Perfil.objects.create(**perfil_data)
        
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre_completo', 'telefono', 'email', 'rol', 'especialidad', 'numero_colegio', 'activo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos específicos de dentista opcionales para administrativos
        if self.instance.pk and self.instance.rol == 'administrativo':
            self.fields['especialidad'].required = False
            self.fields['numero_colegio'].required = False

        # Validar longitud mínima
        if len(cleaned_phone) < 8:
            raise forms.ValidationError('El teléfono debe tener al menos 8 dígitos.')
        if len(cleaned_phone) > 15:
            raise forms.ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('La contraseña es requerida.')
        
        # Validación de fuerza de contraseña mejorada
        if len(password1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        if len(password1) > 128:
            raise forms.ValidationError('La contraseña no puede tener más de 128 caracteres.')
        
        # Verificar que tenga al menos una letra y un número
        has_letter = re.search(r'[a-zA-Z]', password1)
        has_digit = re.search(r'\d', password1)
        
        if not has_letter:
            raise forms.ValidationError('La contraseña debe contener al menos una letra.')
        
        if not has_digit:
            raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
        # Verificar que no sea demasiado común (lista básica)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password1.lower() in common_passwords:
            raise forms.ValidationError('Esta contraseña es demasiado común. Por favor, elige una más segura.')
        
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Crear el perfil con todos los campos
            perfil_data = {
                'user': user,
                'nombre_completo': self.cleaned_data['nombre_completo'],
                'telefono': self.cleaned_data['telefono'],
                'email': user.email,
                'rol': self.cleaned_data['rol'],
            }
            
            # Agregar campos específicos para dentistas
            if self.cleaned_data['rol'] == 'dentista':
                perfil_data['especialidad'] = self.cleaned_data.get('especialidad', '')
                perfil_data['numero_colegio'] = self.cleaned_data.get('numero_colegio', '')
            
            Perfil.objects.create(**perfil_data)
        
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre_completo', 'telefono', 'email', 'rol', 'especialidad', 'numero_colegio', 'activo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos específicos de dentista opcionales para administrativos
        if self.instance.pk and self.instance.rol == 'administrativo':
            self.fields['especialidad'].required = False
            self.fields['numero_colegio'].required = False

        # Validar longitud mínima
        if len(cleaned_phone) < 8:
            raise forms.ValidationError('El teléfono debe tener al menos 8 dígitos.')
        if len(cleaned_phone) > 15:
            raise forms.ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('La contraseña es requerida.')
        
        # Validación de fuerza de contraseña mejorada
        if len(password1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        if len(password1) > 128:
            raise forms.ValidationError('La contraseña no puede tener más de 128 caracteres.')
        
        # Verificar que tenga al menos una letra y un número
        has_letter = re.search(r'[a-zA-Z]', password1)
        has_digit = re.search(r'\d', password1)
        
        if not has_letter:
            raise forms.ValidationError('La contraseña debe contener al menos una letra.')
        
        if not has_digit:
            raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
        # Verificar que no sea demasiado común (lista básica)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password1.lower() in common_passwords:
            raise forms.ValidationError('Esta contraseña es demasiado común. Por favor, elige una más segura.')
        
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Crear el perfil con todos los campos
            perfil_data = {
                'user': user,
                'nombre_completo': self.cleaned_data['nombre_completo'],
                'telefono': self.cleaned_data['telefono'],
                'email': user.email,
                'rol': self.cleaned_data['rol'],
            }
            
            # Agregar campos específicos para dentistas
            if self.cleaned_data['rol'] == 'dentista':
                perfil_data['especialidad'] = self.cleaned_data.get('especialidad', '')
                perfil_data['numero_colegio'] = self.cleaned_data.get('numero_colegio', '')
            
            Perfil.objects.create(**perfil_data)
        
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre_completo', 'telefono', 'email', 'rol', 'especialidad', 'numero_colegio', 'activo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos específicos de dentista opcionales para administrativos
        if self.instance.pk and self.instance.rol == 'administrativo':
            self.fields['especialidad'].required = False
            self.fields['numero_colegio'].required = False

        # Validar longitud mínima
        if len(cleaned_phone) < 8:
            raise forms.ValidationError('El teléfono debe tener al menos 8 dígitos.')
        if len(cleaned_phone) > 15:
            raise forms.ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('La contraseña es requerida.')
        
        # Validación de fuerza de contraseña mejorada
        if len(password1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        if len(password1) > 128:
            raise forms.ValidationError('La contraseña no puede tener más de 128 caracteres.')
        
        # Verificar que tenga al menos una letra y un número
        has_letter = re.search(r'[a-zA-Z]', password1)
        has_digit = re.search(r'\d', password1)
        
        if not has_letter:
            raise forms.ValidationError('La contraseña debe contener al menos una letra.')
        
        if not has_digit:
            raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
        # Verificar que no sea demasiado común (lista básica)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password1.lower() in common_passwords:
            raise forms.ValidationError('Esta contraseña es demasiado común. Por favor, elige una más segura.')
        
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Crear el perfil con todos los campos
            perfil_data = {
                'user': user,
                'nombre_completo': self.cleaned_data['nombre_completo'],
                'telefono': self.cleaned_data['telefono'],
                'email': user.email,
                'rol': self.cleaned_data['rol'],
            }
            
            # Agregar campos específicos para dentistas
            if self.cleaned_data['rol'] == 'dentista':
                perfil_data['especialidad'] = self.cleaned_data.get('especialidad', '')
                perfil_data['numero_colegio'] = self.cleaned_data.get('numero_colegio', '')
            
            Perfil.objects.create(**perfil_data)
        
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre_completo', 'telefono', 'email', 'rol', 'especialidad', 'numero_colegio', 'activo']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos específicos de dentista opcionales para administrativos
        if self.instance.pk and self.instance.rol == 'administrativo':
            self.fields['especialidad'].required = False
            self.fields['numero_colegio'].required = False
