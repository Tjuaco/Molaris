from django.core.management.base import BaseCommand
from django.db import connection, transaction
from pacientes.models import Cliente

class Command(BaseCommand):
    help = 'Importa PerfilCliente desde la web pública hacia el modelo Cliente del sistema de gestión'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando importación de perfiles de cliente...'))
        
        clientes_creados = 0
        clientes_actualizados = 0
        errores = 0
        
        try:
            with connection.cursor() as cursor:
                # Verificar si existe la tabla cuentas_perfilcliente
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_name = 'cuentas_perfilcliente';
                """)
                
                if cursor.fetchone()[0] == 0:
                    self.stdout.write(
                        self.style.ERROR('✗ Tabla cuentas_perfilcliente no encontrada')
                    )
                    return
                
                # Obtener todos los perfiles de cliente con TODOS los campos
                cursor.execute("""
                    SELECT 
                        nombre_completo, 
                        email, 
                        telefono, 
                        telefono_verificado,
                        rut,
                        fecha_nacimiento,
                        alergias
                    FROM cuentas_perfilcliente;
                """)
                
                perfiles = cursor.fetchall()
                total_perfiles = len(perfiles)
                
                self.stdout.write(f'Encontrados {total_perfiles} perfiles de cliente')
                
                with transaction.atomic():
                    for perfil in perfiles:
                        nombre_completo = perfil[0]
                        email = perfil[1]
                        telefono = perfil[2]
                        telefono_verificado = perfil[3]
                        rut = perfil[4] if len(perfil) > 4 else None
                        fecha_nacimiento = perfil[5] if len(perfil) > 5 else None
                        alergias = perfil[6] if len(perfil) > 6 else None
                        
                        try:
                            # Buscar o crear el cliente
                            cliente, created = Cliente.objects.get_or_create(
                                email=email,
                                defaults={
                                    'nombre_completo': nombre_completo,
                                    'telefono': telefono,
                                    'rut': rut,
                                    'fecha_nacimiento': fecha_nacimiento,
                                    'alergias': alergias,
                                    'activo': True,
                                    'notas': f'Importado desde PerfilCliente. Teléfono verificado: {telefono_verificado}'
                                }
                            )
                            
                            if created:
                                clientes_creados += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'[OK] Cliente creado: {cliente.nombre_completo} ({cliente.email})'
                                    )
                                )
                            else:
                                # Actualizar información si el cliente ya existe
                                # Sincronizar TODOS los campos desde PerfilCliente
                                cliente.nombre_completo = nombre_completo
                                cliente.telefono = telefono
                                if rut and not cliente.rut:
                                    cliente.rut = rut
                                if fecha_nacimiento and not cliente.fecha_nacimiento:
                                    cliente.fecha_nacimiento = fecha_nacimiento
                                if alergias and not cliente.alergias:
                                    cliente.alergias = alergias
                                if not cliente.notas:
                                    cliente.notas = f'Importado desde PerfilCliente. Teléfono verificado: {telefono_verificado}'
                                cliente.save()
                                clientes_actualizados += 1
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'[ACTUALIZADO] Cliente actualizado: {cliente.nombre_completo} ({cliente.email})'
                                    )
                                )
                        
                        except Exception as e:
                            errores += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'[ERROR] Error al procesar {email}: {str(e)}'
                                )
                            )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error general: {str(e)}')
            )
            return
        
        # Resumen
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('[OK] Importacion completada'))
        self.stdout.write('='*60)
        self.stdout.write(f'Clientes creados:      {clientes_creados}')
        self.stdout.write(f'Clientes actualizados: {clientes_actualizados}')
        self.stdout.write(f'Errores:               {errores}')
        self.stdout.write(f'Total procesados:      {clientes_creados + clientes_actualizados + errores}')
        self.stdout.write('='*60)
        
        # Verificar resultado
        total_clientes = Cliente.objects.count()
        self.stdout.write(f'\n[INFO] Total de clientes en el sistema: {total_clientes}')






























