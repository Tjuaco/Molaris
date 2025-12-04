from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone


class Perfil(models.Model):
    ROLE_CHOICES = (
        ('administrativo', 'Administrativo'),
        ('dentista', 'Dentista'),
        ('general', 'General (Acceso Completo)'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre_completo = models.CharField(max_length=150)
    telefono = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{8,15}$',
                message='El número de teléfono debe tener entre 8 y 15 dígitos.'
            )
        ]
    )
    email = models.EmailField()
    rol = models.CharField(max_length=20, choices=ROLE_CHOICES)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    # Foto del personal (opcional)
    foto = models.ImageField(upload_to='personal/', blank=True, null=True, verbose_name="Foto del Personal")
    
    # Indica si el personal requiere acceso al sistema
    requiere_acceso_sistema = models.BooleanField(default=True, verbose_name="Requiere Acceso al Sistema")
    
    # Campos específicos para dentistas
    especialidad = models.CharField(max_length=100, blank=True, null=True)
    numero_colegio = models.CharField(max_length=50, blank=True, null=True)
    
    # Permisos específicos
    puede_gestionar_citas = models.BooleanField(default=True, verbose_name="Puede gestionar citas")
    puede_gestionar_clientes = models.BooleanField(default=False, verbose_name="Puede gestionar clientes")
    puede_gestionar_insumos = models.BooleanField(default=False, verbose_name="Puede gestionar insumos")
    puede_gestionar_personal = models.BooleanField(default=False, verbose_name="Puede gestionar personal")
    puede_ver_reportes = models.BooleanField(default=False, verbose_name="Puede ver reportes")
    puede_crear_odontogramas = models.BooleanField(default=True, verbose_name="Puede crear odontogramas")
    
    def __str__(self):
        return f"{self.nombre_completo} ({self.rol})"
    
    def es_administrativo(self):
        return self.rol == 'administrativo' or self.rol == 'general'
    
    def es_dentista(self):
        return self.rol == 'dentista'
    
    def es_general(self):
        return self.rol == 'general'
    
    def tiene_permiso(self, permiso):
        """
        Verifica si el perfil tiene un permiso específico.
        Los administradores (rol 'general') tienen TODOS los permisos automáticamente.
        """
        if self.es_general():
            return True
        return getattr(self, permiso, False)
    
    def puede_gestionar_citas_check(self):
        """Verifica si puede gestionar citas. Administradores siempre pueden."""
        return self.es_general() or self.puede_gestionar_citas
    
    def puede_gestionar_clientes_check(self):
        """Verifica si puede gestionar clientes. Administradores siempre pueden."""
        return self.es_general() or self.puede_gestionar_clientes
    
    def puede_gestionar_insumos_check(self):
        """Verifica si puede gestionar insumos. Administradores siempre pueden."""
        return self.es_general() or self.puede_gestionar_insumos
    
    def puede_gestionar_personal_check(self):
        """Verifica si puede gestionar personal. Administradores siempre pueden."""
        return self.es_general() or self.puede_gestionar_personal
    
    def puede_ver_reportes_check(self):
        """Verifica si puede ver reportes. Administradores siempre pueden."""
        return self.es_general() or self.puede_ver_reportes
    
    def puede_crear_odontogramas_check(self):
        """Verifica si puede crear odontogramas. Administradores siempre pueden."""
        return self.es_general() or self.puede_crear_odontogramas
    
    def save(self, *args, **kwargs):
        """
        Override del método save para asegurar que los administradores (rol 'general')
        tengan todos los permisos habilitados automáticamente.
        """
        if self.rol == 'general':
            # El rol 'general' (administrador completo) tiene todos los permisos
            self.puede_gestionar_citas = True
            self.puede_gestionar_clientes = True
            self.puede_gestionar_insumos = True
            self.puede_gestionar_personal = True
            self.puede_ver_reportes = True
            self.puede_crear_odontogramas = True
        super().save(*args, **kwargs)
    
    def get_pacientes_asignados(self):
        """
        Retorna todos los pacientes que han tenido citas con este dentista (historial completo).
        
        IMPORTANTE: Incluye pacientes con citas en cualquier estado:
        - Citas completadas
        - Citas reservadas (activas)
        - Citas canceladas
        - Citas disponibles
        
        Esto permite ver el historial completo de pacientes, no solo los que tienen citas activas.
        
        Prioriza los datos actualizados del modelo Cliente cuando existe.
        """
        if self.es_dentista():
            from citas.models import Cita
            # Obtener citas asignadas a este dentista
            citas_asignadas = Cita.objects.filter(
                dentista=self,
                paciente_nombre__isnull=False,
                paciente_email__isnull=False
            ).exclude(
                paciente_nombre='',
                paciente_email=''
            )
            
            # Estrategia mejorada: buscar clientes de múltiples formas
            from pacientes.models import Cliente
            # 1. Clientes con relación directa en citas (campo cliente)
            clientes_con_relacion = Cliente.objects.filter(
                citas__dentista=self,
                activo=True
            ).distinct()
            
            # 2. Clientes que tengan emails que aparecen en las citas
            emails_citas = citas_asignadas.values_list('paciente_email', flat=True).distinct()
            clientes_por_email = Cliente.objects.filter(
                email__in=emails_citas,
                activo=True
            ).distinct()
            
            # 3. Combinar ambos conjuntos
            todos_clientes = (clientes_con_relacion | clientes_por_email).distinct()
            
            # Crear diccionario de clientes actualizados por email actual
            clientes_dict = {}
            for cliente in todos_clientes:
                email_cliente = cliente.email
                clientes_dict[email_cliente] = {
                    'id': cliente.id,
                    'nombre_completo': cliente.nombre_completo,
                    'email': cliente.email,
                    'telefono': cliente.telefono or '',
                    'fecha_registro': cliente.fecha_registro,
                    'activo': cliente.activo,
                    'notas': cliente.notas or '',
                    'total_citas': 0,
                    'citas': []
                }
            
            # Crear mapeo de emails antiguos a emails actuales
            # Mapear por relación directa: si una cita tiene cliente, usar el email del cliente
            emails_antiguos_a_actuales = {}
            for cita in citas_asignadas:
                if cita.cliente:
                    # Si la cita tiene cliente, mapear el email de la cita al email actual del cliente
                    email_cita = cita.paciente_email
                    email_actual_cliente = cita.cliente.email
                    if email_cita and email_actual_cliente and email_cita != email_actual_cliente:
                        emails_antiguos_a_actuales[email_cita] = email_actual_cliente
            
            # También mapear por nombre: si el nombre coincide y hay un cliente, usar el email del cliente
            for cliente in todos_clientes:
                email_actual = cliente.email
                # Buscar citas de este cliente por relación directa o por nombre que coincida
                citas_cliente = citas_asignadas.filter(
                    Q(cliente=cliente) | 
                    (Q(paciente_nombre__iexact=cliente.nombre_completo) & Q(paciente_email__isnull=False))
                )
                for cita in citas_cliente:
                    email_cita = cita.paciente_email
                    if email_cita and email_cita != email_actual:
                        emails_antiguos_a_actuales[email_cita] = email_actual
            
            # Crear lista de pacientes únicos basada en email
            pacientes_dict = {}
            for cita in citas_asignadas:
                email_cita = cita.paciente_email
                
                # PRIORIDAD 1: Si la cita tiene cliente directamente, usar ese cliente (más confiable)
                # Usar ID del cliente como clave para evitar duplicados por email
                if cita.cliente:
                    cliente = cita.cliente
                    email_key = f"cliente_{cliente.id}"  # Clave única por cliente
                    
                    if email_key not in pacientes_dict:
                        pacientes_dict[email_key] = {
                            'id': cliente.id,
                            'nombre_completo': cliente.nombre_completo,  # Nombre completo actualizado
                            'email': cliente.email,  # Email actualizado
                            'telefono': cliente.telefono or '',
                            'fecha_registro': cliente.fecha_registro,
                            'activo': cliente.activo,
                            'notas': cliente.notas or '',
                            'total_citas': 0,
                            'citas': []
                        }
                else:
                    # PRIORIDAD 2: Buscar por mapeo de emails antiguos a actuales
                    email_principal = emails_antiguos_a_actuales.get(email_cita, email_cita)
                    
                    # Si hay un email actual mapeado, buscar el cliente
                    cliente_encontrado = None
                    if email_principal in clientes_dict:
                        try:
                            cliente_encontrado = Cliente.objects.get(email=email_principal, activo=True)
                        except Cliente.DoesNotExist:
                            pass
                    elif email_cita in clientes_dict:
                        try:
                            cliente_encontrado = Cliente.objects.get(email=email_cita, activo=True)
                        except Cliente.DoesNotExist:
                            pass
                    
                    if cliente_encontrado:
                        # Usar ID del cliente como clave (evita duplicados por email)
                        email_key = f"cliente_{cliente_encontrado.id}"
                        if email_key not in pacientes_dict:
                            pacientes_dict[email_key] = {
                                'id': cliente_encontrado.id,
                                'nombre_completo': cliente_encontrado.nombre_completo,
                                'email': cliente_encontrado.email,
                                'telefono': cliente_encontrado.telefono or '',
                                'fecha_registro': cliente_encontrado.fecha_registro,
                                'activo': cliente_encontrado.activo,
                                'notas': cliente_encontrado.notas or '',
                                'total_citas': 0,
                                'citas': []
                            }
                    else:
                        # PRIORIDAD 3 y 4: Si no existe cliente, buscar por nombre completo para evitar duplicados
                        nombre_cita = (cita.paciente_nombre or '').strip()
                        nombre_normalizado = nombre_cita.lower().strip() if nombre_cita else ''
                        
                        # Buscar si ya existe un paciente con este nombre exacto
                        paciente_existente = None
                        if nombre_normalizado:
                            for key, paciente in pacientes_dict.items():
                                if paciente.get('nombre_completo', '').lower().strip() == nombre_normalizado:
                                    paciente_existente = key
                                    break
                        
                        if paciente_existente:
                            # Usar el paciente existente (evita duplicado por nombre)
                            email_key = paciente_existente
                        else:
                            # Nuevo paciente sin cliente en el sistema
                            email_key = email_cita
                            if email_key not in pacientes_dict:
                                notas_paciente = cita.notas_paciente or ''
                                pacientes_dict[email_key] = {
                                    'id': hash(email_cita) % 1000000,
                                    'nombre_completo': cita.paciente_nombre,
                                    'email': email_cita,
                                    'telefono': cita.paciente_telefono or '',
                                    'fecha_registro': cita.creada_el,
                                    'activo': True,
                                    'notas': notas_paciente,
                                    'total_citas': 0,
                                    'citas': []
                                }
                
                pacientes_dict[email_key]['citas'].append(cita)
                pacientes_dict[email_key]['total_citas'] += 1
                
                # Actualizar notas si la cita actual tiene notas más recientes (solo si no hay cliente)
                if email_key not in clientes_dict and cita.notas_paciente:
                    pacientes_dict[email_key]['notas'] = cita.notas_paciente
                
                # Asegurar que siempre se usen los datos actualizados del cliente si existe
                if email_key in clientes_dict:
                    # Actualizar con datos actuales del cliente
                    pacientes_dict[email_key]['email'] = clientes_dict[email_key]['email']
                    pacientes_dict[email_key]['nombre_completo'] = clientes_dict[email_key]['nombre_completo']
                    pacientes_dict[email_key]['telefono'] = clientes_dict[email_key]['telefono']
                elif cita.cliente:
                    # Si la cita tiene cliente, usar sus datos actualizados (por si acaso)
                    pacientes_dict[email_key]['email'] = cita.cliente.email
                    pacientes_dict[email_key]['nombre_completo'] = cita.cliente.nombre_completo
                    pacientes_dict[email_key]['telefono'] = cita.cliente.telefono or ''
            
            return list(pacientes_dict.values())
        return []
    
    def get_citas_pacientes(self):
        """Retorna todas las citas de los pacientes asignados a este dentista"""
        if self.es_dentista():
            from citas.models import Cita
            return Cita.objects.filter(
                dentista=self,
                paciente_nombre__isnull=False,
                paciente_email__isnull=False
            ).exclude(
                paciente_nombre='',
                paciente_email=''
            )
        return Cita.objects.none()
    
    def get_estadisticas_pacientes(self):
        """Retorna estadísticas de los pacientes del dentista"""
        if not self.es_dentista():
            return {}
        
        pacientes = self.get_pacientes_asignados()
        citas_pacientes = self.get_citas_pacientes()
        
        return {
            'total_pacientes': len(pacientes),
            'citas_totales': citas_pacientes.count(),
            'citas_completadas': citas_pacientes.filter(estado='completada').count(),
            'citas_pendientes': citas_pacientes.filter(estado='reservada').count(),
            'citas_hoy': citas_pacientes.filter(
                fecha_hora__date=timezone.now().date()
            ).count(),
        }
    
    class Meta:
        verbose_name = "Perfil de Trabajador"
        verbose_name_plural = "Perfiles de Trabajadores"
