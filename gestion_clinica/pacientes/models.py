from django.db import models
from django.core.validators import RegexValidator


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
                message='El número de teléfono debe ser un celular chileno en formato: +56912345678 (solo números celulares)'
            )
        ],
        help_text="Solo números celulares chilenos. Formato: +56912345678"
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
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre_completo']
