from django.core.management.base import BaseCommand
from pacientes.models import Cliente
from personal.models import Perfil
from django.utils import timezone

class Command(BaseCommand):
    help = 'Crea clientes de prueba para el sistema'

    def handle(self, *args, **options):
        # Crear clientes de prueba
        clientes_prueba = [
            {
                'nombre_completo': 'Juan Pérez García',
                'email': 'juan.perez@email.com',
                'telefono': '+56912345678',
                'notas': 'Paciente con historial de caries. Requiere limpieza cada 6 meses.'
            },
            {
                'nombre_completo': 'María González López',
                'email': 'maria.gonzalez@email.com',
                'telefono': '+56987654321',
                'notas': 'Paciente con ortodoncia. Citas de control mensual.'
            },
            {
                'nombre_completo': 'Carlos Rodríguez Martínez',
                'email': 'carlos.rodriguez@email.com',
                'telefono': '+56911223344',
                'notas': 'Paciente nuevo. Primera consulta programada.'
            },
            {
                'nombre_completo': 'Ana Fernández Silva',
                'email': 'ana.fernandez@email.com',
                'telefono': '+56955667788',
                'notas': 'Paciente con implantes. Seguimiento post-operatorio.'
            },
            {
                'nombre_completo': 'Luis Morales Herrera',
                'email': 'luis.morales@email.com',
                'telefono': '+56999887766',
                'notas': 'Paciente con periodontitis. Tratamiento en curso.'
            }
        ]

        # Obtener el primer dentista disponible para asignar
        dentista = Perfil.objects.filter(rol='dentista', activo=True).first()
        
        clientes_creados = 0
        for datos_cliente in clientes_prueba:
            # Verificar si el cliente ya existe
            if not Cliente.objects.filter(email=datos_cliente['email']).exists():
                cliente = Cliente.objects.create(
                    nombre_completo=datos_cliente['nombre_completo'],
                    email=datos_cliente['email'],
                    telefono=datos_cliente['telefono'],
                    notas=datos_cliente['notas'],
                    dentista_asignado=dentista if dentista else None
                )
                clientes_creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Cliente creado: {cliente.nombre_completo}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Cliente ya existe: {datos_cliente["nombre_completo"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Se crearon {clientes_creados} clientes de prueba.')
        )


