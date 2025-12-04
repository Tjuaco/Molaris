from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pacientes.models import Cliente

try:
    from cuentas.models import PerfilCliente
    PERFIL_CLIENTE_AVAILABLE = True
except ImportError:
    PERFIL_CLIENTE_AVAILABLE = False
    PerfilCliente = None

class Command(BaseCommand):
    help = 'Busca un cliente específico por username o email'

    def add_arguments(self, parser):
        parser.add_argument('busqueda', type=str, help='Username o email a buscar')

    def handle(self, *args, **options):
        busqueda = options['busqueda']
        
        self.stdout.write(self.style.SUCCESS(f'\n=== BUSCANDO: {busqueda} ===\n'))
        
        # 1. Buscar en User
        self.stdout.write(self.style.WARNING('1. BUSCANDO EN USUARIOS (User):'))
        try:
            user = User.objects.get(username=busqueda)
            self.stdout.write(f'   [ENCONTRADO] Usuario: {user.username}')
            self.stdout.write(f'   - Email: {user.email}')
            self.stdout.write(f'   - ID: {user.id}')
            self.stdout.write(f'   - Activo: {user.is_active}')
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=busqueda)
                self.stdout.write(f'   [ENCONTRADO] Usuario por email: {user.username}')
                self.stdout.write(f'   - Email: {user.email}')
                self.stdout.write(f'   - ID: {user.id}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR('   [NO ENCONTRADO] No existe usuario con ese username o email'))
                user = None
        
        # 2. Buscar en PerfilCliente
        if PERFIL_CLIENTE_AVAILABLE and user:
            self.stdout.write('\n' + self.style.WARNING('2. BUSCANDO EN PERFIL CLIENTE:'))
            try:
                perfil = PerfilCliente.objects.get(user=user)
                self.stdout.write(f'   [ENCONTRADO] PerfilCliente:')
                self.stdout.write(f'   - Nombre: {perfil.nombre_completo}')
                self.stdout.write(f'   - Email: {perfil.email}')
                self.stdout.write(f'   - Teléfono: {perfil.telefono}')
                self.stdout.write(f'   - RUT: {perfil.rut or "No tiene"}')
            except PerfilCliente.DoesNotExist:
                self.stdout.write(self.style.ERROR('   [NO ENCONTRADO] No tiene PerfilCliente asociado'))
                perfil = None
        else:
            perfil = None
        
        # 3. Buscar en Cliente
        self.stdout.write('\n' + self.style.WARNING('3. BUSCANDO EN CLIENTE:'))
        if user:
            # Buscar por email del usuario
            try:
                cliente = Cliente.objects.get(email=user.email)
                self.stdout.write(f'   [ENCONTRADO] Cliente por email:')
                self.stdout.write(f'   - Nombre: {cliente.nombre_completo}')
                self.stdout.write(f'   - Email: {cliente.email}')
                self.stdout.write(f'   - Teléfono: {cliente.telefono}')
                self.stdout.write(f'   - Activo: {cliente.activo}')
                self.stdout.write(f'   - ID: {cliente.id}')
            except Cliente.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'   [NO ENCONTRADO] No existe Cliente con email: {user.email}'))
                cliente = None
        else:
            # Buscar directamente por email
            try:
                cliente = Cliente.objects.get(email=busqueda)
                self.stdout.write(f'   [ENCONTRADO] Cliente por email:')
                self.stdout.write(f'   - Nombre: {cliente.nombre_completo}')
                self.stdout.write(f'   - Email: {cliente.email}')
            except Cliente.DoesNotExist:
                self.stdout.write(self.style.ERROR('   [NO ENCONTRADO] No existe Cliente con ese email'))
                cliente = None
        
        # 4. Resumen
        self.stdout.write('\n' + self.style.SUCCESS('=== RESUMEN ==='))
        if user and perfil and not cliente:
            self.stdout.write(self.style.WARNING('[PROBLEMA] El usuario tiene PerfilCliente pero NO tiene Cliente'))
            self.stdout.write(self.style.WARNING('   -> Necesita ejecutar: python manage.py importar_perfiles_cliente'))
        elif user and not perfil:
            self.stdout.write(self.style.WARNING('[PROBLEMA] El usuario NO tiene PerfilCliente'))
        elif user and perfil and cliente:
            self.stdout.write(self.style.SUCCESS('[OK] El usuario tiene User, PerfilCliente y Cliente'))
        
        self.stdout.write('')















