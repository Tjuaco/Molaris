"""
Comando de gestión para limpiar registros de auditoría antiguos.

Política de retención actualizada:
- Mantener los últimos 12 meses (365 días) completos
- Si hay más de 100,000 registros, mantener solo los 100,000 más recientes
- Eliminar registros más antiguos automáticamente
- Este comando debe ejecutarse periódicamente (recomendado: semanalmente o mensualmente)
- También se ejecuta automáticamente cada ~100 registros nuevos (1% de probabilidad)

Uso:
    python manage.py limpiar_auditoria_antigua
    python manage.py limpiar_auditoria_antigua --dry-run  # Solo mostrar qué se eliminaría
    python manage.py limpiar_auditoria_antigua --dias 365  # Especificar días de retención
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from citas.models_auditoria import AuditoriaLog
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Elimina registros de auditoría antiguos según política: 12 meses + máximo 100,000 registros'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se eliminaría sin eliminar realmente',
        )
        parser.add_argument(
            '--dias',
            type=int,
            default=365,
            help='Número de días de retención (por defecto: 365 días = 12 meses)',
        )
        parser.add_argument(
            '--max-registros',
            type=int,
            default=100000,
            help='Número máximo de registros a mantener (por defecto: 100,000)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        dias_retencion = options['dias']
        max_registros = options['max_registros']
        
        # Contar total de registros
        total_registros = AuditoriaLog.objects.count()
        self.stdout.write(f'Total de registros en auditoría: {total_registros:,}')
        
        cantidad_eliminada_total = 0
        
        # Política 1: Si hay más de max_registros, mantener solo los max_registros más recientes
        if total_registros > max_registros:
            # Obtener el ID del registro número max_registros (ordenado por fecha descendente)
            registros_ordenados = AuditoriaLog.objects.order_by('-fecha_hora')[:max_registros]
            if registros_ordenados:
                # Obtener la fecha del último registro que queremos mantener
                fecha_limite_cantidad = registros_ordenados[max_registros - 1].fecha_hora
                # Eliminar registros más antiguos que este
                registros_a_eliminar = AuditoriaLog.objects.filter(fecha_hora__lt=fecha_limite_cantidad)
                cantidad = registros_a_eliminar.count()
                
                if cantidad > 0:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'[DRY RUN] Se eliminarían {cantidad:,} registros de auditoría '
                                f'(manteniendo solo los {max_registros:,} más recientes)'
                            )
                        )
                    else:
                        try:
                            registros_a_eliminar.delete()
                            cantidad_eliminada_total += cantidad
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✓ Se eliminaron {cantidad:,} registros antiguos '
                                    f'(manteniendo los {max_registros:,} más recientes)'
                                )
                            )
                            logger.info(f'Se eliminaron {cantidad} registros de auditoría (más de {max_registros} registros)')
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'✗ Error al eliminar registros: {str(e)}')
                            )
                            logger.error(f'Error al eliminar registros de auditoría: {str(e)}')
        
        # Política 2: Eliminar registros más antiguos de X días (si no se aplicó la política 1)
        if total_registros <= max_registros:
            fecha_limite = timezone.now() - timedelta(days=dias_retencion)
            registros_antiguos = AuditoriaLog.objects.filter(fecha_hora__lt=fecha_limite)
            cantidad = registros_antiguos.count()
            
            if cantidad == 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ No hay registros de auditoría más antiguos de {dias_retencion} días.')
                )
            else:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY RUN] Se eliminarían {cantidad:,} registros de auditoría anteriores a {fecha_limite.strftime("%d/%m/%Y %H:%M")}'
                        )
                    )
                    
                    # Mostrar algunos ejemplos
                    ejemplos = registros_antiguos[:5]
                    self.stdout.write('\nEjemplos de registros que se eliminarían:')
                    for registro in ejemplos:
                        self.stdout.write(
                            f'  - [{registro.fecha_hora.strftime("%d/%m/%Y %H:%M")}] '
                            f'{registro.usuario.nombre_completo if registro.usuario else "Sistema"} - '
                            f'{registro.get_accion_display()} en {registro.get_modulo_display()}: {registro.descripcion[:50]}'
                        )
                    if cantidad > 5:
                        self.stdout.write(f'  ... y {cantidad - 5:,} más')
                else:
                    # Eliminar registros antiguos
                    try:
                        registros_antiguos.delete()
                        cantidad_eliminada_total += cantidad
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Se eliminaron {cantidad:,} registros de auditoría anteriores a {fecha_limite.strftime("%d/%m/%Y %H:%M")}'
                            )
                        )
                        logger.info(f'Se eliminaron {cantidad} registros de auditoría antiguos (anteriores a {fecha_limite})')
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'✗ Error al eliminar registros: {str(e)}')
                        )
                        logger.error(f'Error al eliminar registros de auditoría antiguos: {str(e)}')
        
        # Resumen final
        if not dry_run and cantidad_eliminada_total > 0:
            total_restante = AuditoriaLog.objects.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Resumen: Se eliminaron {cantidad_eliminada_total:,} registros. '
                    f'Quedan {total_restante:,} registros en auditoría.'
                )
            )












