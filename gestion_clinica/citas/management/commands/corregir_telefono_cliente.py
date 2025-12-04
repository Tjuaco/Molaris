from django.core.management.base import BaseCommand
from pacientes.models import Cliente

class Command(BaseCommand):
    help = 'Corrige el teléfono de un cliente'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del cliente')
        parser.add_argument('telefono', type=str, nargs='?', help='Nuevo teléfono (opcional)')

    def handle(self, *args, **options):
        email = options['email']
        telefono_nuevo = options.get('telefono')
        
        try:
            cliente = Cliente.objects.get(email=email)
            self.stdout.write(f'Cliente encontrado: {cliente.nombre_completo}')
            self.stdout.write(f'Teléfono actual: {cliente.telefono}')
            
            if telefono_nuevo:
                cliente.telefono = telefono_nuevo
                cliente.save()
                self.stdout.write(self.style.SUCCESS(f'Teléfono actualizado a: {telefono_nuevo}'))
            else:
                self.stdout.write(self.style.WARNING('No se proporcionó nuevo teléfono. El teléfono actual es inválido.'))
                self.stdout.write(self.style.WARNING('Puedes editarlo desde la interfaz web o ejecutar:'))
                self.stdout.write(f'  python manage.py corregir_telefono_cliente {email} +56912345678')
                
        except Cliente.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No se encontró cliente con email: {email}'))















