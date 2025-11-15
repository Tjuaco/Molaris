from django.core.management.base import BaseCommand
from pacientes.models import Cliente
from citas.models import Cita
from django.db import transaction

class Command(BaseCommand):
    help = 'Sincroniza clientes desde las citas existentes hacia el modelo Cliente'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando sincronización de clientes...'))
        
        # Obtener todas las citas que tienen información de paciente
        citas_con_paciente = Cita.objects.filter(
            paciente_email__isnull=False
        ).exclude(
            paciente_email=''
        ).order_by('creada_el')
        
        clientes_creados = 0
        clientes_actualizados = 0
        clientes_vinculados = 0
        
        # Diccionario para rastrear emails procesados en esta ejecución
        emails_procesados = {}
        
        with transaction.atomic():
            for cita in citas_con_paciente:
                email = cita.paciente_email
                
                # Si ya procesamos este email en esta ejecución, solo vincular la cita
                if email in emails_procesados:
                    cliente = emails_procesados[email]
                    if not cita.cliente:
                        cita.cliente = cliente
                        cita.save(update_fields=['cliente'])
                        clientes_vinculados += 1
                    continue
                
                # Buscar o crear el cliente
                cliente, created = Cliente.objects.get_or_create(
                    email=email,
                    defaults={
                        'nombre_completo': cita.paciente_nombre or 'Sin nombre',
                        'telefono': cita.paciente_telefono or '',
                        'activo': True,
                        'notas': f'Cliente sincronizado automáticamente desde cita {cita.id}'
                    }
                )
                
                # Guardar en el diccionario
                emails_procesados[email] = cliente
                
                if created:
                    clientes_creados += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Cliente creado: {cliente.nombre_completo} ({cliente.email})')
                    )
                else:
                    # Actualizar información si el cliente ya existe
                    actualizado = False
                    if not cliente.nombre_completo or cliente.nombre_completo == 'Sin nombre':
                        cliente.nombre_completo = cita.paciente_nombre or 'Sin nombre'
                        actualizado = True
                    if not cliente.telefono and cita.paciente_telefono:
                        cliente.telefono = cita.paciente_telefono
                        actualizado = True
                    
                    if actualizado:
                        cliente.save()
                        clientes_actualizados += 1
                        self.stdout.write(
                            self.style.WARNING(f'↻ Cliente actualizado: {cliente.nombre_completo}')
                        )
                
                # Vincular la cita con el cliente si no está vinculada
                if not cita.cliente:
                    cita.cliente = cliente
                    cita.save(update_fields=['cliente'])
                    clientes_vinculados += 1
        
        # Resumen
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ Sincronización completada'))
        self.stdout.write('='*60)
        self.stdout.write(f'Clientes creados:     {clientes_creados}')
        self.stdout.write(f'Clientes actualizados: {clientes_actualizados}')
        self.stdout.write(f'Citas vinculadas:      {clientes_vinculados}')
        self.stdout.write(f'Total citas procesadas: {citas_con_paciente.count()}')
        self.stdout.write('='*60)


