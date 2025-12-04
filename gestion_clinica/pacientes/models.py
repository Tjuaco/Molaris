from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
import re


def normalizar_telefono_chileno_modelo(telefono):
    """
    Normaliza un número de teléfono chileno al formato +56912345678
    Acepta números de 8 dígitos (ej: 20589344) y los convierte a +56920589344
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
    
    # Caso 1: 8 dígitos (formato preferido: solo los últimos 8 del celular)
    # Ejemplo: 20589344 -> +56920589344
    if len(telefono_limpio) == 8:
        return f"+569{telefono_limpio}"
    
    # Caso 2: 9 dígitos que empiezan con 9
    # Ejemplo: 920589344 -> +56920589344
    if len(telefono_limpio) == 9 and telefono_limpio.startswith('9'):
        return f"+56{telefono_limpio}"
    
    # Caso 3: 11 dígitos (ya incluye código de país)
    # Ejemplo: 56920589344 -> +56920589344
    if len(telefono_limpio) == 11 and telefono_limpio.startswith('56'):
        return f"+{telefono_limpio}"
    
    # Caso 4: Ya está en formato correcto (+569...)
    if len(telefono_limpio) == 11 and telefono_limpio.startswith('569'):
        return f"+{telefono_limpio}"
    
    return None


class Cliente(models.Model):
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    
    # RUT/DNI - Identificación única
    rut = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        null=True,
        verbose_name="RUT",
        help_text="RUT en formato: 12345678-9 (opcional pero recomendado)"
    )
    
    telefono = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+569\d{8}$',
                message='El número de teléfono debe ser un celular chileno. Ingrese solo los 8 dígitos (ejemplo: 20589344). El sistema agregará automáticamente el 9 y el código de país (+56).'
            )
        ],
        help_text="Ingrese solo los 8 dígitos del celular (ejemplo: 20589344). El sistema agregará automáticamente el 9 y el código de país (+56)."
    )
    
    # Fecha de nacimiento - Para calcular edad automáticamente
    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Nacimiento",
        help_text="Fecha de nacimiento del paciente"
    )
    
    # Alergias - CRÍTICO para seguridad del paciente
    alergias = models.TextField(
        blank=True,
        null=True,
        verbose_name="Alergias",
        help_text="Lista de alergias conocidas (medicamentos, materiales dentales, anestesia, etc.). MUY IMPORTANTE para la seguridad del paciente."
    )
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    
    # Relación explícita con User (para facilitar eliminación en cascada y sincronización)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cliente_asociado',
        verbose_name="Usuario Web Asociado",
        help_text="Usuario del sistema web asociado a este cliente (opcional)"
    )
    
    # Relación con dentista asignado
    dentista_asignado = models.ForeignKey(
        'personal.Perfil', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pacientes_asignados',
        limit_choices_to={'rol': 'dentista', 'activo': True},
        verbose_name="Dentista Asignado"
    )
    
    def save(self, *args, **kwargs):
        """Normaliza el teléfono automáticamente antes de guardar"""
        if self.telefono:
            telefono_normalizado = normalizar_telefono_chileno_modelo(self.telefono)
            if telefono_normalizado:
                self.telefono = telefono_normalizado
            # Si no se puede normalizar, mantener el valor original (el validador lo rechazará)
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.rut:
            return f"{self.nombre_completo} (RUT: {self.rut})"
        return f"{self.nombre_completo} ({self.email})"
    
    @property
    def tiene_dentista_asignado(self):
        """Verifica si el cliente tiene un dentista asignado"""
        return self.dentista_asignado is not None
    
    @property
    def nombre_dentista(self):
        """Retorna el nombre del dentista asignado o 'Sin asignar'"""
        return self.dentista_asignado.nombre_completo if self.dentista_asignado else 'Sin asignar'
    
    @property
    def edad(self):
        """Calcula la edad automáticamente basándose en la fecha de nacimiento"""
        if self.fecha_nacimiento:
            from datetime import date
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None
    
    @property
    def tiene_alergias(self):
        """Verifica si el paciente tiene alergias registradas"""
        return bool(self.alergias and self.alergias.strip())
    
    @property
    def tiene_usuario_web(self):
        """Verifica si el cliente tiene un usuario web asociado"""
        return self.user is not None
    
    @property
    def username_web(self):
        """Retorna el username del usuario web asociado o None"""
        return self.user.username if self.user else None
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre_completo']
