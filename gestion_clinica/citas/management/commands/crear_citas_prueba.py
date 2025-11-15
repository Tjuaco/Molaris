from django.core.management.base import BaseCommand
from citas.models import Cita
from personal.models import Perfil
from django.utils import timezone
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Crea citas de prueba con clientes para el sistema'

    def handle(self, *args, **options):
        # Obtener un dentista para asignar
        dentista = Perfil.objects.filter(rol='dentista', activo=True).first()
        
        if not dentista:
            self.stdout.write(
                self.style.ERROR('No hay dentistas disponibles. Crea un dentista primero.')
            )
            return
        
        # Crear citas de prueba con clientes
        citas_prueba = [
            {
                'paciente_nombre': 'Ana García López',
                'paciente_email': 'ana.garcia@email.com',
                'paciente_telefono': '+56912345678',
                'tipo_consulta': 'Limpieza dental',
                'notas': 'Primera consulta de limpieza'
            },
            {
                'paciente_nombre': 'Carlos Mendoza Ruiz',
                'paciente_email': 'carlos.mendoza@email.com',
                'paciente_telefono': '+56987654321',
                'tipo_consulta': 'Ortodoncia',
                'notas': 'Control de brackets'
            },
            {
                'paciente_nombre': 'María Fernández Silva',
                'paciente_email': 'maria.fernandez@email.com',
                'paciente_telefono': '+56911223344',
                'tipo_consulta': 'Endodoncia',
                'notas': 'Tratamiento de conducto'
            },
            {
                'paciente_nombre': 'Luis Rodríguez Pérez',
                'paciente_email': 'luis.rodriguez@email.com',
                'paciente_telefono': '+56955667788',
                'tipo_consulta': 'Implante dental',
                'notas': 'Consulta pre-operatoria'
            },
            {
                'paciente_nombre': 'Sofia Martínez González',
                'paciente_email': 'sofia.martinez@email.com',
                'paciente_telefono': '+56999887766',
                'tipo_consulta': 'Periodoncia',
                'notas': 'Tratamiento de encías'
            }
        ]
        
        citas_creadas = 0
        base_fecha = timezone.now() + timedelta(days=1)
        
        for i, datos_cita in enumerate(citas_prueba):
            fecha_hora = base_fecha + timedelta(hours=i*2)  # Citas cada 2 horas
            
            # Verificar que no exista ya una cita en esa fecha/hora
            if not Cita.objects.filter(fecha_hora=fecha_hora).exists():
                cita = Cita.objects.create(
                    fecha_hora=fecha_hora,
                    paciente_nombre=datos_cita['paciente_nombre'],
                    paciente_email=datos_cita['paciente_email'],
                    paciente_telefono=datos_cita['paciente_telefono'],
                    tipo_consulta=datos_cita['tipo_consulta'],
                    notas=datos_cita['notas'],
                    estado='reservada',
                    dentista=dentista
                )
                citas_creadas += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Cita creada: {cita.paciente_nombre} - {cita.fecha_hora.strftime("%d/%m/%Y %H:%M")}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Ya existe una cita en {fecha_hora.strftime("%d/%m/%Y %H:%M")}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Se crearon {citas_creadas} citas de prueba con clientes.')
        )


