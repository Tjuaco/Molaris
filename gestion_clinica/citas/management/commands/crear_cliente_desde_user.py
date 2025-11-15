from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pacientes.models import Cliente

class Command(BaseCommand):
    help = 'Crea un Cliente desde un User que no tiene PerfilCliente'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username del usuario')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f'Usuario encontrado: {user.username} ({user.email})')
            
            # Verificar si ya existe un Cliente con este email
            if Cliente.objects.filter(email=user.email).exists():
                self.stdout.write(self.style.ERROR(f'Ya existe un Cliente con el email: {user.email}'))
                cliente_existente = Cliente.objects.get(email=user.email)
                self.stdout.write(f'Cliente existente: {cliente_existente.nombre_completo} (ID: {cliente_existente.id})')
                return
            
            # Crear el Cliente
            # Intentar obtener nombre completo de first_name y last_name
            if user.first_name or user.last_name:
                nombre_completo = f"{user.first_name} {user.last_name}".strip()
            else:
                nombre_completo = user.username
            
            # El teléfono es obligatorio, pero no lo tenemos del User
            # Usaremos un placeholder que el usuario deberá actualizar
            telefono = "+56900000000"  # Placeholder que debe ser actualizado
            
            self.stdout.write(self.style.WARNING(f'Creando cliente con datos:'))
            self.stdout.write(f'  - Nombre: {nombre_completo}')
            self.stdout.write(f'  - Email: {user.email}')
            self.stdout.write(f'  - Teléfono: {telefono} (PLACEHOLDER - debe actualizarse)')
            
            cliente = Cliente.objects.create(
                nombre_completo=nombre_completo,
                email=user.email,
                telefono=telefono,
                activo=True,
                notas=f'Cliente creado desde User: {user.username}'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Cliente creado exitosamente:'))
            self.stdout.write(f'  - ID: {cliente.id}')
            self.stdout.write(f'  - Nombre: {cliente.nombre_completo}')
            self.stdout.write(f'  - Email: {cliente.email}')
            self.stdout.write(f'  - Teléfono: {cliente.telefono}')
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No se encontró el usuario: {username}'))

