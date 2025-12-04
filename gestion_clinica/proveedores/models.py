from django.db import models
from personal.models import Perfil


class Proveedor(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Proveedor")
    rut = models.CharField(max_length=20, unique=True, verbose_name="RUT/NIT")
    email = models.EmailField(verbose_name="Email de Contacto")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    contacto_nombre = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nombre del Contacto")
    sitio_web = models.URLField(blank=True, null=True, verbose_name="Sitio Web")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    # Campos de auditoría
    creado_el = models.DateTimeField(auto_now_add=True)
    actualizado_el = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='proveedores_creados')
    
    def __str__(self):
        return f"{self.nombre} - {self.rut}"
    
    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']


# Pedidos a proveedores (agrupa múltiples solicitudes)
class Pedido(models.Model):
    ESTADO_CHOICES = (
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('confirmado', 'Confirmado'),
        ('en_transito', 'En Tránsito'),
        ('recibido', 'Recibido'),
        ('cancelado', 'Cancelado'),
    )
    
    numero_pedido = models.CharField(max_length=50, unique=True, verbose_name="Número de Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='pedidos')
    fecha_pedido = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Pedido")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones Generales")
    
    # Envío de correo
    correo_enviado = models.BooleanField(default=False, verbose_name="Correo Enviado")
    fecha_envio_correo = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío del Correo")
    
    # Finanzas
    registrar_como_egreso = models.BooleanField(default=False, verbose_name="Registrar como Egreso en Finanzas")
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Monto Total del Pedido")
    
    # Campos de auditoría
    creado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_creados')
    recibido_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_recibidos')
    fecha_recepcion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Recepción")
    
    def calcular_monto_total(self):
        """Calcula el monto total del pedido basado en las solicitudes"""
        total = 0
        for solicitud in self.solicitudes.all():
            if solicitud.monto_egreso:
                total += solicitud.monto_egreso
        return total
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f'PED-{timestamp}'
        
        # Calcular monto total si hay solicitudes
        if self.pk:
            self.monto_total = self.calcular_monto_total()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']


# Solicitudes de insumos a proveedores (ahora vinculadas a pedidos)
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='solicitudes', null=True, blank=True, verbose_name="Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Precio y monto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unitario")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def calcular_monto(self):
        """Calcula el monto basado en precio unitario y cantidad"""
        if self.precio_unitario:
            return self.precio_unitario * self.cantidad_solicitada
        elif self.insumo.precio_unitario:
            return self.insumo.precio_unitario * self.cantidad_solicitada
        return None
    
    def save(self, *args, **kwargs):
        # Calcular monto si no está establecido
        if not self.monto_egreso:
            monto_calculado = self.calcular_monto()
            if monto_calculado:
                self.monto_egreso = monto_calculado
        
        # Si no tiene precio unitario, usar el del insumo
        if not self.precio_unitario and self.insumo.precio_unitario:
            self.precio_unitario = self.insumo.precio_unitario
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']

    def calcular_monto_total(self):
        """Calcula el monto total del pedido basado en las solicitudes"""
        total = 0
        for solicitud in self.solicitudes.all():
            if solicitud.monto_egreso:
                total += solicitud.monto_egreso
        return total
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f'PED-{timestamp}'
        
        # Calcular monto total si hay solicitudes
        if self.pk:
            self.monto_total = self.calcular_monto_total()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']


# Solicitudes de insumos a proveedores (ahora vinculadas a pedidos)
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='solicitudes', null=True, blank=True, verbose_name="Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Precio y monto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unitario")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def calcular_monto(self):
        """Calcula el monto basado en precio unitario y cantidad"""
        if self.precio_unitario:
            return self.precio_unitario * self.cantidad_solicitada
        elif self.insumo.precio_unitario:
            return self.insumo.precio_unitario * self.cantidad_solicitada
        return None
    
    def save(self, *args, **kwargs):
        # Calcular monto si no está establecido
        if not self.monto_egreso:
            monto_calculado = self.calcular_monto()
            if monto_calculado:
                self.monto_egreso = monto_calculado
        
        # Si no tiene precio unitario, usar el del insumo
        if not self.precio_unitario and self.insumo.precio_unitario:
            self.precio_unitario = self.insumo.precio_unitario
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']

    def calcular_monto_total(self):
        """Calcula el monto total del pedido basado en las solicitudes"""
        total = 0
        for solicitud in self.solicitudes.all():
            if solicitud.monto_egreso:
                total += solicitud.monto_egreso
        return total
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f'PED-{timestamp}'
        
        # Calcular monto total si hay solicitudes
        if self.pk:
            self.monto_total = self.calcular_monto_total()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']


# Solicitudes de insumos a proveedores (ahora vinculadas a pedidos)
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='solicitudes', null=True, blank=True, verbose_name="Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Precio y monto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unitario")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def calcular_monto(self):
        """Calcula el monto basado en precio unitario y cantidad"""
        if self.precio_unitario:
            return self.precio_unitario * self.cantidad_solicitada
        elif self.insumo.precio_unitario:
            return self.insumo.precio_unitario * self.cantidad_solicitada
        return None
    
    def save(self, *args, **kwargs):
        # Calcular monto si no está establecido
        if not self.monto_egreso:
            monto_calculado = self.calcular_monto()
            if monto_calculado:
                self.monto_egreso = monto_calculado
        
        # Si no tiene precio unitario, usar el del insumo
        if not self.precio_unitario and self.insumo.precio_unitario:
            self.precio_unitario = self.insumo.precio_unitario
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']

    def calcular_monto_total(self):
        """Calcula el monto total del pedido basado en las solicitudes"""
        total = 0
        for solicitud in self.solicitudes.all():
            if solicitud.monto_egreso:
                total += solicitud.monto_egreso
        return total
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f'PED-{timestamp}'
        
        # Calcular monto total si hay solicitudes
        if self.pk:
            self.monto_total = self.calcular_monto_total()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']


# Solicitudes de insumos a proveedores (ahora vinculadas a pedidos)
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='solicitudes', null=True, blank=True, verbose_name="Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Precio y monto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unitario")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def calcular_monto(self):
        """Calcula el monto basado en precio unitario y cantidad"""
        if self.precio_unitario:
            return self.precio_unitario * self.cantidad_solicitada
        elif self.insumo.precio_unitario:
            return self.insumo.precio_unitario * self.cantidad_solicitada
        return None
    
    def save(self, *args, **kwargs):
        # Calcular monto si no está establecido
        if not self.monto_egreso:
            monto_calculado = self.calcular_monto()
            if monto_calculado:
                self.monto_egreso = monto_calculado
        
        # Si no tiene precio unitario, usar el del insumo
        if not self.precio_unitario and self.insumo.precio_unitario:
            self.precio_unitario = self.insumo.precio_unitario
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']

    def calcular_monto_total(self):
        """Calcula el monto total del pedido basado en las solicitudes"""
        total = 0
        for solicitud in self.solicitudes.all():
            if solicitud.monto_egreso:
                total += solicitud.monto_egreso
        return total
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f'PED-{timestamp}'
        
        # Calcular monto total si hay solicitudes
        if self.pk:
            self.monto_total = self.calcular_monto_total()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']


# Solicitudes de insumos a proveedores (ahora vinculadas a pedidos)
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='solicitudes', null=True, blank=True, verbose_name="Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Precio y monto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unitario")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def calcular_monto(self):
        """Calcula el monto basado en precio unitario y cantidad"""
        if self.precio_unitario:
            return self.precio_unitario * self.cantidad_solicitada
        elif self.insumo.precio_unitario:
            return self.insumo.precio_unitario * self.cantidad_solicitada
        return None
    
    def save(self, *args, **kwargs):
        # Calcular monto si no está establecido
        if not self.monto_egreso:
            monto_calculado = self.calcular_monto()
            if monto_calculado:
                self.monto_egreso = monto_calculado
        
        # Si no tiene precio unitario, usar el del insumo
        if not self.precio_unitario and self.insumo.precio_unitario:
            self.precio_unitario = self.insumo.precio_unitario
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']

    def calcular_monto_total(self):
        """Calcula el monto total del pedido basado en las solicitudes"""
        total = 0
        for solicitud in self.solicitudes.all():
            if solicitud.monto_egreso:
                total += solicitud.monto_egreso
        return total
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f'PED-{timestamp}'
        
        # Calcular monto total si hay solicitudes
        if self.pk:
            self.monto_total = self.calcular_monto_total()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']


# Solicitudes de insumos a proveedores (ahora vinculadas a pedidos)
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='solicitudes', null=True, blank=True, verbose_name="Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Precio y monto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unitario")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def calcular_monto(self):
        """Calcula el monto basado en precio unitario y cantidad"""
        if self.precio_unitario:
            return self.precio_unitario * self.cantidad_solicitada
        elif self.insumo.precio_unitario:
            return self.insumo.precio_unitario * self.cantidad_solicitada
        return None
    
    def save(self, *args, **kwargs):
        # Calcular monto si no está establecido
        if not self.monto_egreso:
            monto_calculado = self.calcular_monto()
            if monto_calculado:
                self.monto_egreso = monto_calculado
        
        # Si no tiene precio unitario, usar el del insumo
        if not self.precio_unitario and self.insumo.precio_unitario:
            self.precio_unitario = self.insumo.precio_unitario
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']

    def calcular_monto_total(self):
        """Calcula el monto total del pedido basado en las solicitudes"""
        total = 0
        for solicitud in self.solicitudes.all():
            if solicitud.monto_egreso:
                total += solicitud.monto_egreso
        return total
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_pedido = f'PED-{timestamp}'
        
        # Calcular monto total si hay solicitudes
        if self.pk:
            self.monto_total = self.calcular_monto_total()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']


# Solicitudes de insumos a proveedores (ahora vinculadas a pedidos)
class SolicitudInsumo(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    )
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='solicitudes', null=True, blank=True, verbose_name="Pedido")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='solicitudes')
    insumo = models.ForeignKey('inventario.Insumo', on_delete=models.CASCADE, related_name='solicitudes')
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega_esperada = models.DateField(verbose_name="Fecha de Entrega Esperada")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Precio y monto
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unitario")
    monto_egreso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto del Egreso")
    
    # Campos de auditoría
    solicitado_por = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_realizadas')
    
    def calcular_monto(self):
        """Calcula el monto basado en precio unitario y cantidad"""
        if self.precio_unitario:
            return self.precio_unitario * self.cantidad_solicitada
        elif self.insumo.precio_unitario:
            return self.insumo.precio_unitario * self.cantidad_solicitada
        return None
    
    def save(self, *args, **kwargs):
        # Calcular monto si no está establecido
        if not self.monto_egreso:
            monto_calculado = self.calcular_monto()
            if monto_calculado:
                self.monto_egreso = monto_calculado
        
        # Si no tiene precio unitario, usar el del insumo
        if not self.precio_unitario and self.insumo.precio_unitario:
            self.precio_unitario = self.insumo.precio_unitario
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.insumo.nombre} a {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = "Solicitud de Insumo"
        verbose_name_plural = "Solicitudes de Insumos"
        ordering = ['-fecha_solicitud']
