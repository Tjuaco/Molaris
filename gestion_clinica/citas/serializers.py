from rest_framework import serializers
from .models import Cita, TipoServicio
from pacientes.models import Cliente
from personal.models import Perfil
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre_completo', 'email', 'telefono', 'rut', 'fecha_nacimiento', 'alergias', 'activo']


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['id', 'nombre_completo', 'rol', 'especialidad']


class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = ['id', 'nombre', 'descripcion', 'precio_base']


class CitaSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    dentista = PerfilSerializer(read_only=True)
    tipo_servicio = TipoServicioSerializer(read_only=True)
    
    class Meta:
        model = Cita
        fields = '__all__'


class OdontogramaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Odontograma
        fields = '__all__'


class RadiografiaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Radiografia
        fields = '__all__'


class EvaluacionSerializer(serializers.ModelSerializer):
    """
    Serializer para crear evaluaciones desde el proyecto del cliente.
    Valida que el cliente exista y que no haya enviado una evaluación previamente.
    """
    
    # Campos solo de lectura para la respuesta
    estrellas_display = serializers.CharField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Evaluacion
        fields = ['id', 'email_cliente', 'estrellas', 'comentario', 'fecha_creacion', 'estrellas_display']
        read_only_fields = ['id', 'fecha_creacion', 'estrellas_display']
    
    def validate_estrellas(self, value):
        """Valida que las estrellas estén entre 1 y 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("La calificación debe estar entre 1 y 5 estrellas.")
        return value
    
    def validate_comentario(self, value):
        """Valida que el comentario no esté vacío y tenga un máximo de 500 caracteres"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        if len(value) > 500:
            raise serializers.ValidationError("El comentario no puede exceder los 500 caracteres.")
        return value.strip()
    
    def validate_email_cliente(self, value):
        """Valida que el email corresponda a un cliente existente"""
        try:
            cliente = Cliente.objects.get(email=value)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError("No existe un cliente registrado con este email.")
        return value
    
    def validate(self, data):
        """Valida que el cliente no haya enviado una evaluación previamente"""
        email = data.get('email_cliente')
        
        # Obtener el cliente
        try:
            cliente = Cliente.objects.get(email=email)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError({"email_cliente": "No existe un cliente registrado con este email."})
        
        # Verificar si ya existe una evaluación para este cliente
        if Evaluacion.objects.filter(cliente=cliente).exists():
            raise serializers.ValidationError({
                "email_cliente": "Ya has enviado una evaluación. Solo se permite una evaluación por cliente."
            })
        
        # Guardar el cliente en el contexto para usarlo en create()
        self.context['cliente'] = cliente
        
        return data
    
    def create(self, validated_data):
        """Crea la evaluación asociando el cliente correcto"""
        cliente = self.context['cliente']
        
        # Obtener la IP del request si está disponible
        request = self.context.get('request')
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        evaluacion = Evaluacion.objects.create(
            cliente=cliente,
            email_cliente=validated_data['email_cliente'],
            estrellas=validated_data['estrellas'],
            comentario=validated_data['comentario'],
            ip_address=ip_address
        )
        
        return evaluacion

from pacientes.models import Cliente
from personal.models import Perfil
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre_completo', 'email', 'telefono', 'rut', 'fecha_nacimiento', 'alergias', 'activo']


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['id', 'nombre_completo', 'rol', 'especialidad']


class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = ['id', 'nombre', 'descripcion', 'precio_base']


class CitaSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    dentista = PerfilSerializer(read_only=True)
    tipo_servicio = TipoServicioSerializer(read_only=True)
    
    class Meta:
        model = Cita
        fields = '__all__'


class OdontogramaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Odontograma
        fields = '__all__'


class RadiografiaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Radiografia
        fields = '__all__'


class EvaluacionSerializer(serializers.ModelSerializer):
    """
    Serializer para crear evaluaciones desde el proyecto del cliente.
    Valida que el cliente exista y que no haya enviado una evaluación previamente.
    """
    
    # Campos solo de lectura para la respuesta
    estrellas_display = serializers.CharField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Evaluacion
        fields = ['id', 'email_cliente', 'estrellas', 'comentario', 'fecha_creacion', 'estrellas_display']
        read_only_fields = ['id', 'fecha_creacion', 'estrellas_display']
    
    def validate_estrellas(self, value):
        """Valida que las estrellas estén entre 1 y 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("La calificación debe estar entre 1 y 5 estrellas.")
        return value
    
    def validate_comentario(self, value):
        """Valida que el comentario no esté vacío y tenga un máximo de 500 caracteres"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        if len(value) > 500:
            raise serializers.ValidationError("El comentario no puede exceder los 500 caracteres.")
        return value.strip()
    
    def validate_email_cliente(self, value):
        """Valida que el email corresponda a un cliente existente"""
        try:
            cliente = Cliente.objects.get(email=value)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError("No existe un cliente registrado con este email.")
        return value
    
    def validate(self, data):
        """Valida que el cliente no haya enviado una evaluación previamente"""
        email = data.get('email_cliente')
        
        # Obtener el cliente
        try:
            cliente = Cliente.objects.get(email=email)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError({"email_cliente": "No existe un cliente registrado con este email."})
        
        # Verificar si ya existe una evaluación para este cliente
        if Evaluacion.objects.filter(cliente=cliente).exists():
            raise serializers.ValidationError({
                "email_cliente": "Ya has enviado una evaluación. Solo se permite una evaluación por cliente."
            })
        
        # Guardar el cliente en el contexto para usarlo en create()
        self.context['cliente'] = cliente
        
        return data
    
    def create(self, validated_data):
        """Crea la evaluación asociando el cliente correcto"""
        cliente = self.context['cliente']
        
        # Obtener la IP del request si está disponible
        request = self.context.get('request')
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        evaluacion = Evaluacion.objects.create(
            cliente=cliente,
            email_cliente=validated_data['email_cliente'],
            estrellas=validated_data['estrellas'],
            comentario=validated_data['comentario'],
            ip_address=ip_address
        )
        
        return evaluacion

from pacientes.models import Cliente
from personal.models import Perfil
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre_completo', 'email', 'telefono', 'rut', 'fecha_nacimiento', 'alergias', 'activo']


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['id', 'nombre_completo', 'rol', 'especialidad']


class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = ['id', 'nombre', 'descripcion', 'precio_base']


class CitaSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    dentista = PerfilSerializer(read_only=True)
    tipo_servicio = TipoServicioSerializer(read_only=True)
    
    class Meta:
        model = Cita
        fields = '__all__'


class OdontogramaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Odontograma
        fields = '__all__'


class RadiografiaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Radiografia
        fields = '__all__'


class EvaluacionSerializer(serializers.ModelSerializer):
    """
    Serializer para crear evaluaciones desde el proyecto del cliente.
    Valida que el cliente exista y que no haya enviado una evaluación previamente.
    """
    
    # Campos solo de lectura para la respuesta
    estrellas_display = serializers.CharField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Evaluacion
        fields = ['id', 'email_cliente', 'estrellas', 'comentario', 'fecha_creacion', 'estrellas_display']
        read_only_fields = ['id', 'fecha_creacion', 'estrellas_display']
    
    def validate_estrellas(self, value):
        """Valida que las estrellas estén entre 1 y 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("La calificación debe estar entre 1 y 5 estrellas.")
        return value
    
    def validate_comentario(self, value):
        """Valida que el comentario no esté vacío y tenga un máximo de 500 caracteres"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        if len(value) > 500:
            raise serializers.ValidationError("El comentario no puede exceder los 500 caracteres.")
        return value.strip()
    
    def validate_email_cliente(self, value):
        """Valida que el email corresponda a un cliente existente"""
        try:
            cliente = Cliente.objects.get(email=value)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError("No existe un cliente registrado con este email.")
        return value
    
    def validate(self, data):
        """Valida que el cliente no haya enviado una evaluación previamente"""
        email = data.get('email_cliente')
        
        # Obtener el cliente
        try:
            cliente = Cliente.objects.get(email=email)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError({"email_cliente": "No existe un cliente registrado con este email."})
        
        # Verificar si ya existe una evaluación para este cliente
        if Evaluacion.objects.filter(cliente=cliente).exists():
            raise serializers.ValidationError({
                "email_cliente": "Ya has enviado una evaluación. Solo se permite una evaluación por cliente."
            })
        
        # Guardar el cliente en el contexto para usarlo en create()
        self.context['cliente'] = cliente
        
        return data
    
    def create(self, validated_data):
        """Crea la evaluación asociando el cliente correcto"""
        cliente = self.context['cliente']
        
        # Obtener la IP del request si está disponible
        request = self.context.get('request')
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        evaluacion = Evaluacion.objects.create(
            cliente=cliente,
            email_cliente=validated_data['email_cliente'],
            estrellas=validated_data['estrellas'],
            comentario=validated_data['comentario'],
            ip_address=ip_address
        )
        
        return evaluacion

from pacientes.models import Cliente
from personal.models import Perfil
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre_completo', 'email', 'telefono', 'rut', 'fecha_nacimiento', 'alergias', 'activo']


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['id', 'nombre_completo', 'rol', 'especialidad']


class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = ['id', 'nombre', 'descripcion', 'precio_base']


class CitaSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    dentista = PerfilSerializer(read_only=True)
    tipo_servicio = TipoServicioSerializer(read_only=True)
    
    class Meta:
        model = Cita
        fields = '__all__'


class OdontogramaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Odontograma
        fields = '__all__'


class RadiografiaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Radiografia
        fields = '__all__'


class EvaluacionSerializer(serializers.ModelSerializer):
    """
    Serializer para crear evaluaciones desde el proyecto del cliente.
    Valida que el cliente exista y que no haya enviado una evaluación previamente.
    """
    
    # Campos solo de lectura para la respuesta
    estrellas_display = serializers.CharField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Evaluacion
        fields = ['id', 'email_cliente', 'estrellas', 'comentario', 'fecha_creacion', 'estrellas_display']
        read_only_fields = ['id', 'fecha_creacion', 'estrellas_display']
    
    def validate_estrellas(self, value):
        """Valida que las estrellas estén entre 1 y 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("La calificación debe estar entre 1 y 5 estrellas.")
        return value
    
    def validate_comentario(self, value):
        """Valida que el comentario no esté vacío y tenga un máximo de 500 caracteres"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        if len(value) > 500:
            raise serializers.ValidationError("El comentario no puede exceder los 500 caracteres.")
        return value.strip()
    
    def validate_email_cliente(self, value):
        """Valida que el email corresponda a un cliente existente"""
        try:
            cliente = Cliente.objects.get(email=value)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError("No existe un cliente registrado con este email.")
        return value
    
    def validate(self, data):
        """Valida que el cliente no haya enviado una evaluación previamente"""
        email = data.get('email_cliente')
        
        # Obtener el cliente
        try:
            cliente = Cliente.objects.get(email=email)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError({"email_cliente": "No existe un cliente registrado con este email."})
        
        # Verificar si ya existe una evaluación para este cliente
        if Evaluacion.objects.filter(cliente=cliente).exists():
            raise serializers.ValidationError({
                "email_cliente": "Ya has enviado una evaluación. Solo se permite una evaluación por cliente."
            })
        
        # Guardar el cliente en el contexto para usarlo en create()
        self.context['cliente'] = cliente
        
        return data
    
    def create(self, validated_data):
        """Crea la evaluación asociando el cliente correcto"""
        cliente = self.context['cliente']
        
        # Obtener la IP del request si está disponible
        request = self.context.get('request')
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        evaluacion = Evaluacion.objects.create(
            cliente=cliente,
            email_cliente=validated_data['email_cliente'],
            estrellas=validated_data['estrellas'],
            comentario=validated_data['comentario'],
            ip_address=ip_address
        )
        
        return evaluacion

from pacientes.models import Cliente
from personal.models import Perfil
from evaluaciones.models import Evaluacion
from historial_clinico.models import Odontograma, Radiografia


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre_completo', 'email', 'telefono', 'rut', 'fecha_nacimiento', 'alergias', 'activo']


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['id', 'nombre_completo', 'rol', 'especialidad']


class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = ['id', 'nombre', 'descripcion', 'precio_base']


class CitaSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    dentista = PerfilSerializer(read_only=True)
    tipo_servicio = TipoServicioSerializer(read_only=True)
    
    class Meta:
        model = Cita
        fields = '__all__'


class OdontogramaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Odontograma
        fields = '__all__'


class RadiografiaSerializer(serializers.ModelSerializer):
    dentista = PerfilSerializer(read_only=True)
    cliente = ClienteSerializer(read_only=True)
    cita = CitaSerializer(read_only=True)
    
    class Meta:
        model = Radiografia
        fields = '__all__'


class EvaluacionSerializer(serializers.ModelSerializer):
    """
    Serializer para crear evaluaciones desde el proyecto del cliente.
    Valida que el cliente exista y que no haya enviado una evaluación previamente.
    """
    
    # Campos solo de lectura para la respuesta
    estrellas_display = serializers.CharField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Evaluacion
        fields = ['id', 'email_cliente', 'estrellas', 'comentario', 'fecha_creacion', 'estrellas_display']
        read_only_fields = ['id', 'fecha_creacion', 'estrellas_display']
    
    def validate_estrellas(self, value):
        """Valida que las estrellas estén entre 1 y 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("La calificación debe estar entre 1 y 5 estrellas.")
        return value
    
    def validate_comentario(self, value):
        """Valida que el comentario no esté vacío y tenga un máximo de 500 caracteres"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        if len(value) > 500:
            raise serializers.ValidationError("El comentario no puede exceder los 500 caracteres.")
        return value.strip()
    
    def validate_email_cliente(self, value):
        """Valida que el email corresponda a un cliente existente"""
        try:
            cliente = Cliente.objects.get(email=value)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError("No existe un cliente registrado con este email.")
        return value
    
    def validate(self, data):
        """Valida que el cliente no haya enviado una evaluación previamente"""
        email = data.get('email_cliente')
        
        # Obtener el cliente
        try:
            cliente = Cliente.objects.get(email=email)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError({"email_cliente": "No existe un cliente registrado con este email."})
        
        # Verificar si ya existe una evaluación para este cliente
        if Evaluacion.objects.filter(cliente=cliente).exists():
            raise serializers.ValidationError({
                "email_cliente": "Ya has enviado una evaluación. Solo se permite una evaluación por cliente."
            })
        
        # Guardar el cliente en el contexto para usarlo en create()
        self.context['cliente'] = cliente
        
        return data
    
    def create(self, validated_data):
        """Crea la evaluación asociando el cliente correcto"""
        cliente = self.context['cliente']
        
        # Obtener la IP del request si está disponible
        request = self.context.get('request')
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        evaluacion = Evaluacion.objects.create(
            cliente=cliente,
            email_cliente=validated_data['email_cliente'],
            estrellas=validated_data['estrellas'],
            comentario=validated_data['comentario'],
            ip_address=ip_address
        )
        
        return evaluacion
