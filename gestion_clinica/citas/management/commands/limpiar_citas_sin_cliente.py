"""
Comando de gestión para limpiar citas que tienen clientes eliminados.

Este comando:
1. Encuentra citas reservadas que no tienen cliente asignado (cliente=None)
2. Si tienen campos de respaldo (paciente_nombre, etc.), las mantiene
3. Si están reservadas sin cliente, las cambia a "disponible"
4. Muestra un resumen de las citas actualizadas

Uso:
    python manage.py limpiar_citas_sin_cliente
    python manage.py limpiar_citas_sin_cliente --dry-run  # Solo muestra qué haría sin hacer cambios
"""

from django.core.management.base import BaseCommand
from citas.models import Cita


class Command(BaseCommand):
    help = 'Limpia citas que tienen clientes eliminados, marcándolas como disponibles si están reservadas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué haría sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios reales\n'))
        
        # Encontrar citas reservadas sin cliente
        citas_reservadas_sin_cliente = Cita.objects.filter(
            estado='reservada',
            cliente__isnull=True
        )
        
        total_encontradas = citas_reservadas_sin_cliente.count()
        
        if total_encontradas == 0:
            self.stdout.write(self.style.SUCCESS('✓ No se encontraron citas reservadas sin cliente.'))
            return
        
        self.stdout.write(f'Se encontraron {total_encontradas} cita(s) reservada(s) sin cliente asignado.\n')
        
        citas_actualizadas = 0
        citas_con_datos = 0
        citas_sin_datos = 0
        
        for cita in citas_reservadas_sin_cliente:
            tiene_datos = bool(cita.paciente_nombre or cita.paciente_email or cita.paciente_telefono)
            
            if tiene_datos:
                citas_con_datos += 1
                self.stdout.write(
                    f'  - Cita ID {cita.id} ({cita.fecha_hora.strftime("%d/%m/%Y %H:%M")}): '
                    f'Tiene datos de respaldo (Paciente: {cita.paciente_nombre or "N/A"})'
                )
            else:
                citas_sin_datos += 1
                self.stdout.write(
                    f'  - Cita ID {cita.id} ({cita.fecha_hora.strftime("%d/%m/%Y %H:%M")}): '
                    f'Sin datos de respaldo'
                )
            
            if not dry_run:
                # Cambiar estado a disponible
                cita.estado = 'disponible'
                cita.save()
                citas_actualizadas += 1
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('RESUMEN:')
        self.stdout.write(f'  - Total encontradas: {total_encontradas}')
        self.stdout.write(f'  - Con datos de respaldo: {citas_con_datos}')
        self.stdout.write(f'  - Sin datos de respaldo: {citas_sin_datos}')
        
        if not dry_run:
            self.stdout.write(f'  - Actualizadas: {citas_actualizadas}')
            self.stdout.write(self.style.SUCCESS(f'\n✓ Se actualizaron {citas_actualizadas} cita(s) a estado "disponible".'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠ En modo dry-run, se actualizarían {total_encontradas} cita(s).'))
            self.stdout.write(self.style.WARNING('Ejecuta sin --dry-run para aplicar los cambios.'))


