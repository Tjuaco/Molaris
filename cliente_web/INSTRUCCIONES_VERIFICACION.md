# Sistema de Verificación con Twilio - Email y WhatsApp

## ✅ Cambios Implementados

### 1. Nuevo Servicio de Twilio
- **Archivo creado**: `cliente_web/reservas/twilio_service.py`
- **Funciones**:
  - `enviar_codigo_por_whatsapp()`: Envía código por WhatsApp usando Twilio
  - `enviar_codigo_por_email()`: Envía código por email usando Django

### 2. Formulario Actualizado
- **Archivo modificado**: `cliente_web/cuentas/forms.py`
- **Nuevo campo**: `metodo_verificacion` (ChoiceField con opciones Email/WhatsApp)
- El usuario puede elegir cómo recibir el código

### 3. Vista Actualizada
- **Archivo modificado**: `cliente_web/cuentas/views.py`
- La vista `registro_cliente` ahora:
  - Lee el método de verificación seleccionado
  - Envía el código según la opción elegida
  - Muestra mensajes apropiados según el método

### 4. Template Actualizado
- **Archivo modificado**: `cliente_web/templates/cuentas/registro_cliente.html`
- Se agregó un campo visual para seleccionar el método de verificación
- Estilos CSS agregados para los radio buttons

## 📋 Pasos para Completar la Configuración

### 1. Instalar Twilio (si no está instalado)
```bash
pip install twilio
```

### 2. Configurar Variables de Entorno
En `cliente_web/cliente_web/settings.py` o en un archivo `.env`:

```python
# Credenciales de Twilio (obtenerlas de https://www.twilio.com/console)
TWILIO_ACCOUNT_SID = 'tu_account_sid_aqui'
TWILIO_AUTH_TOKEN = 'tu_auth_token_aqui'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'  # Número de Twilio para WhatsApp
TWILIO_PHONE_NUMBER = '+1234567890'  # Tu número de Twilio para SMS (opcional)
```

### 3. Configurar Email (para verificación por email)
En `cliente_web/cliente_web/settings.py`:

```python
EMAIL_HOST = 'smtp.gmail.com'  # o tu proveedor de email
EMAIL_PORT = 587
EMAIL_HOST_USER = 'tu-email@gmail.com'
EMAIL_HOST_PASSWORD = 'tu-contraseña-de-aplicacion'  # No la contraseña normal
EMAIL_USE_TLS = True
EMAIL_FROM = 'tu-email@gmail.com'
```

## 🎯 Cómo Funciona

1. **Usuario completa el formulario de registro**
2. **Selecciona método de verificación**:
   - 📧 Email: Recibe código por correo electrónico
   - 💬 WhatsApp: Recibe código por WhatsApp
3. **Sistema envía el código** según la opción elegida
4. **Usuario ingresa el código** en la página de verificación
5. **Cuenta creada** exitosamente

## 🔧 Modo Desarrollo

Si Twilio o Email no están configurados:
- El código se mostrará en la **consola del servidor Django**
- El flujo continuará normalmente para pruebas
- Mensaje claro: `[MODO DESARROLLO] Código de verificación...`

## 📝 Notas Importantes

- **Twilio Sandbox**: Para pruebas, puedes usar el sandbox de Twilio (gratis)
- **WhatsApp**: Necesitas un número de WhatsApp Business verificado en Twilio
- **Email**: Funciona con cualquier proveedor de email (Gmail, Outlook, etc.)
- **Seguridad**: Los códigos expiran en 15 minutos

## 🚀 Próximos Pasos

1. Instalar Twilio: `pip install twilio`
2. Obtener credenciales de Twilio (cuenta gratuita disponible)
3. Configurar variables de entorno
4. Probar el registro con ambos métodos

