from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
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
        widget=forms.TextInput(attrs={'class': 'form-control'})
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
        self.fields['username'].help_text = 'Requerido. 150 caracteres o menos. Solo letras, dígitos y @/./+/-/_'
        self.fields['password1'].help_text = 'Tu contraseña debe contener al menos 8 caracteres'
        self.fields['password2'].help_text = 'Ingresa la misma contraseña para verificación'
        
        # Agregar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Este nombre de usuario ya está en uso. Por favor, elige otro.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este email ya está registrado.')
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        # Validación básica de teléfono
        if not telefono.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise forms.ValidationError('El teléfono debe contener solo números, +, - y espacios.')
        return telefono

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
