from django.core.management.base import BaseCommand
from pacientes.models import Cliente
from django.contrib.auth.models import User

try:
    from cuentas.models import PerfilCliente
    PERFIL_CLIENTE_AVAILABLE = True
except ImportError:
    PERFIL_CLIENTE_AVAILABLE = False
    PerfilCliente = None

class Command(BaseCommand):
    help = 'Diagnostica los clientes en la base de datos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== DIAGNÓSTICO DE CLIENTES ===\n'))
        
        # 1. Verificar Cliente (modelo principal)
        self.stdout.write(self.style.WARNING('1. CLIENTES (pacientes.models.Cliente):'))
        total_clientes = Cliente.objects.count()
        self.stdout.write(f'   Total: {total_clientes}')
        
        if total_clientes > 0:
            clientes_activos = Cliente.objects.filter(activo=True).count()
            clientes_inactivos = Cliente.objects.filter(activo=False).count()
            self.stdout.write(f'   - Activos: {clientes_activos}')
            self.stdout.write(f'   - Inactivos: {clientes_inactivos}')
            
            # Mostrar primeros 5
            self.stdout.write('\n   Primeros 5 clientes:')
            for cliente in Cliente.objects.all()[:5]:
                estado = '✓' if cliente.activo else '✗'
                estado_texto = 'ACTIVO' if cliente.activo else 'INACTIVO'
                self.stdout.write(f'   [{estado_texto}] {cliente.nombre_completo} ({cliente.email})')
        else:
            self.stdout.write(self.style.ERROR('   [ADVERTENCIA] No hay clientes en la tabla Cliente'))
        
        # 2. Verificar PerfilCliente (si existe)
        if PERFIL_CLIENTE_AVAILABLE:
            self.stdout.write('\n' + self.style.WARNING('2. PERFIL CLIENTE (cuentas.models.PerfilCliente):'))
            total_perfiles = PerfilCliente.objects.count()
            self.stdout.write(f'   Total: {total_perfiles}')
            
            if total_perfiles > 0:
                # Mostrar primeros 5
                self.stdout.write('\n   Primeros 5 perfiles:')
                for perfil in PerfilCliente.objects.all()[:5]:
                    self.stdout.write(f'   - {perfil.nombre_completo} ({perfil.email}) - User: {perfil.user.username}')
            else:
                self.stdout.write(self.style.ERROR('   [ADVERTENCIA] No hay perfiles de cliente'))
        else:
            self.stdout.write('\n' + self.style.WARNING('2. PERFIL CLIENTE: No disponible'))
        
        # 3. Verificar Users
        self.stdout.write('\n' + self.style.WARNING('3. USUARIOS (django.contrib.auth.models.User):'))
        total_users = User.objects.count()
        self.stdout.write(f'   Total: {total_users}')
        
        # 4. Verificar si hay citas con clientes
        from citas.models import Cita
        citas_con_cliente = Cita.objects.filter(cliente__isnull=False).count()
        citas_sin_cliente = Cita.objects.filter(cliente__isnull=False, paciente_email__isnull=False).count()
        self.stdout.write('\n' + self.style.WARNING('4. CITAS:'))
        self.stdout.write(f'   Citas con cliente vinculado: {citas_con_cliente}')
        self.stdout.write(f'   Citas con email pero sin cliente: {citas_sin_cliente}')
        
        # 5. Resumen
        self.stdout.write('\n' + self.style.SUCCESS('=== RESUMEN ==='))
        if total_clientes == 0:
            self.stdout.write(self.style.ERROR('[PROBLEMA] No hay clientes en la tabla Cliente'))
            if PERFIL_CLIENTE_AVAILABLE and total_perfiles > 0:
                self.stdout.write(self.style.WARNING('   -> Hay perfiles de cliente pero no estan sincronizados'))
                self.stdout.write(self.style.WARNING('   -> Considera sincronizar PerfilCliente -> Cliente'))
        else:
            self.stdout.write(self.style.SUCCESS(f'[OK] Hay {total_clientes} clientes en la base de datos'))
        
        self.stdout.write('')

