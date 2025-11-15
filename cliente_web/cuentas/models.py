from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta

class PerfilCliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre_completo = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    telefono_verificado = models.BooleanField(default=False)
    
    # Campos nuevos sincronizados desde el sistema de gestión
    rut = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        verbose_name="RUT",
        help_text="RUT en formato: 12345678-9 (opcional pero recomendado)"
    )
    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Nacimiento",
        help_text="Fecha de nacimiento del paciente"
    )
    alergias = models.TextField(
        blank=True,
        null=True,
        verbose_name="Alergias",
        help_text="Lista de alergias conocidas (medicamentos, materiales dentales, anestesia, etc.). MUY IMPORTANTE para la seguridad del paciente."
    )
    
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

    def __str__(self):
        return f"{self.nombre_completo} ({self.user.username})"

class CodigoVerificacion(models.Model):
    telefono = models.CharField(max_length=20)
    codigo = models.CharField(max_length=6)
    creado_el = models.DateTimeField(auto_now_add=True)
    intentos = models.IntegerField(default=0)
    verificado = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-creado_el']
    
    def __str__(self):
        return f"Código para {self.telefono}: {self.codigo}"
    
    @classmethod
    def generar_codigo(cls, telefono):
        """Genera un nuevo código de verificación para un teléfono"""
        # Eliminar códigos antiguos para este teléfono
        cls.objects.filter(telefono=telefono).delete()
        
        # Generar código de 6 dígitos
        codigo = ''.join(random.choices(string.digits, k=6))
        
        return cls.objects.create(
            telefono=telefono,
            codigo=codigo
        )
    
    def es_valido(self):
        """Verifica si el código sigue siendo válido (15 minutos)"""
        tiempo_expiracion = self.creado_el + timedelta(minutes=15)
        return timezone.now() < tiempo_expiracion and not self.verificado
    
    def verificar(self, codigo_ingresado):
        """Verifica si el código ingresado es correcto"""
        if not self.es_valido():
            return False
            
        if self.codigo == codigo_ingresado:
            self.verificado = True
            self.save()
            return True
        
        self.intentos += 1
        self.save()
        return False