from django import template

register = template.Library()

@register.filter(name='pesos_chilenos')
def pesos_chilenos(value):
    """
    Formatea un número como pesos chilenos con separador de miles.
    Ejemplo: 1000 -> $1.000
    Los pesos chilenos siempre se muestran sin decimales (redondeados).
    Uso: {{ precio|pesos_chilenos }}
    """
    if value is None:
        return '$0'
    try:
        # Convertir a entero o float
        if isinstance(value, str):
            # Intentar convertir string a número
            try:
                num = float(value)
            except ValueError:
                return value
        else:
            num = float(value)
        
        # Para pesos chilenos, siempre redondear a entero (sin decimales)
        num_entero = round(num)
        formatted = f"{num_entero:,}".replace(",", ".")
        return f"${formatted}"
    except (ValueError, TypeError):
        return str(value)


@register.filter(name='split')
def split(value, arg):
    """
    Divide una cadena en una lista usando el separador especificado.
    Uso: {{ "1,2,3"|split:"," }}
    """
    return value.split(arg)


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Obtiene un item de un diccionario usando una clave.
    Uso: {{ mi_diccionario|get_item:clave }}
    """
    if dictionary is None:
        return None
    # Convertir la clave a entero si el diccionario tiene claves enteras
    try:
        key = int(key)
    except (ValueError, TypeError):
        pass
    return dictionary.get(key, 0)


@register.filter(name='getattr')
def getattr_filter(field, obj):
    """
    Obtiene un atributo de un objeto usando el nombre de un campo.
    Uso: {{ permiso|getattr:rol }}
    """
    try:
        if hasattr(field, 'name'):
            # Si field es un campo del modelo, obtener su nombre
            attr_name = field.name
            return getattr(obj, attr_name, False)
        return False
    except (AttributeError, TypeError):
        return False


def get_item(dictionary, key):
    """
    Obtiene un item de un diccionario usando una clave.
    Uso: {{ mi_diccionario|get_item:clave }}
    """
    if dictionary is None:
        return None
    # Convertir la clave a entero si el diccionario tiene claves enteras
    try:
        key = int(key)
    except (ValueError, TypeError):
        pass
    return dictionary.get(key, 0)


@register.filter(name='getattr')
def getattr_filter(field, obj):
    """
    Obtiene un atributo de un objeto usando el nombre de un campo.
    Uso: {{ permiso|getattr:rol }}
    """
    try:
        if hasattr(field, 'name'):
            # Si field es un campo del modelo, obtener su nombre
            attr_name = field.name
            return getattr(obj, attr_name, False)
        return False
    except (AttributeError, TypeError):
        return False


def get_item(dictionary, key):
    """
    Obtiene un item de un diccionario usando una clave.
    Uso: {{ mi_diccionario|get_item:clave }}
    """
    if dictionary is None:
        return None
    # Convertir la clave a entero si el diccionario tiene claves enteras
    try:
        key = int(key)
    except (ValueError, TypeError):
        pass
    return dictionary.get(key, 0)


@register.filter(name='getattr')
def getattr_filter(field, obj):
    """
    Obtiene un atributo de un objeto usando el nombre de un campo.
    Uso: {{ permiso|getattr:rol }}
    """
    try:
        if hasattr(field, 'name'):
            # Si field es un campo del modelo, obtener su nombre
            attr_name = field.name
            return getattr(obj, attr_name, False)
        return False
    except (AttributeError, TypeError):
        return False


def get_item(dictionary, key):
    """
    Obtiene un item de un diccionario usando una clave.
    Uso: {{ mi_diccionario|get_item:clave }}
    """
    if dictionary is None:
        return None
    # Convertir la clave a entero si el diccionario tiene claves enteras
    try:
        key = int(key)
    except (ValueError, TypeError):
        pass
    return dictionary.get(key, 0)


@register.filter(name='getattr')
def getattr_filter(field, obj):
    """
    Obtiene un atributo de un objeto usando el nombre de un campo.
    Uso: {{ permiso|getattr:rol }}
    """
    try:
        if hasattr(field, 'name'):
            # Si field es un campo del modelo, obtener su nombre
            attr_name = field.name
            return getattr(obj, attr_name, False)
        return False
    except (AttributeError, TypeError):
        return False

