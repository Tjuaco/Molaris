"""
Django settings for gestion_clinica project.
"""

from pathlib import Path
import os
from decouple import config, Csv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production-28vh&5z1ku08x3e@gwocph(vtcc=k3shq(!6=4@-v1iuw+c)5t')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'citas',
    'personal',
    'pacientes',
    'historial_clinico',
    'inventario',
    'proveedores',
    'finanzas',
    'configuracion',
    'comunicacion',
    'evaluaciones',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gestion_clinica.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'citas.context_processors.info_clinica',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestion_clinica.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Railway proporciona DATABASE_URL automáticamente
import dj_database_url

# Intentar usar DATABASE_URL de Railway primero
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Fallback a configuración manual
    DB_ENGINE = config('DB_ENGINE', default='sqlite')
    
    if DB_ENGINE == 'postgresql':
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config('DB_NAME', default='clinica_db'),
                'USER': config('DB_USER', default='postgres'),
                'PASSWORD': config('DB_PASSWORD', default=''),
                'HOST': config('DB_HOST', default='localhost'),
                'PORT': config('DB_PORT', default='5432'),
            }
        }
    else:
        # SQLite por defecto
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for serving static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = '/trabajadores/login/'
LOGIN_REDIRECT_URL = '/trabajadores/dashboard/'
LOGOUT_REDIRECT_URL = '/trabajadores/login/'

# Configuración de Twilio para SMS y WhatsApp
# ⚠️ IMPORTANTE: Configura estos valores en el archivo .env
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='AC7319b0ea75ab89067722861358686b39')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='cfa7d326a809fd880175c86e59f6a228')

# Número de teléfono de Twilio para SMS (formato E.164: +1234567890)
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='+15005550006')
TWILIO_FROM_SMS = config('TWILIO_FROM_SMS', default=TWILIO_PHONE_NUMBER)

# Número de WhatsApp de Twilio (puede ser sandbox o número de WhatsApp Business)
# Formato: whatsapp:+14155238886 (sandbox) o whatsapp:+1234567890 (número real)
TWILIO_WHATSAPP_NUMBER = config('TWILIO_WHATSAPP_NUMBER', default='whatsapp:+14155238886')
TWILIO_FROM_WHATSAPP = config('TWILIO_FROM_WHATSAPP', default=TWILIO_WHATSAPP_NUMBER)
TWILIO_WHATSAPP_BUSINESS_NUMBER = config('TWILIO_WHATSAPP_BUSINESS_NUMBER', default=TWILIO_FROM_WHATSAPP)

# URL de callback para recibir actualizaciones de estado de mensajes (opcional)
TWILIO_STATUS_CALLBACK = config('TWILIO_STATUS_CALLBACK', default=None)

# Información de la clínica para personalizar mensajes (opcional, se obtiene del modelo si no se define)
CLINIC_NAME = config('CLINIC_NAME', default='Clínica Dental San Felipe')
CLINIC_ADDRESS = config('CLINIC_ADDRESS', default='')
CLINIC_PHONE = config('CLINIC_PHONE', default='')
CLINIC_EMAIL = config('CLINIC_EMAIL', default='')
CLINIC_WEBSITE = config('CLINIC_WEBSITE', default='')
CLINIC_MAP_URL = config('CLINIC_MAP_URL', default='https://www.google.com/maps/place/Clinica+San+Felipe/@-38.2356192,-72.3361399,17z/data=!3m1!4b1!4m6!3m5!1s0x966b155a8306e093:0x46de06dfbc92e29d!8m2!3d-38.2356192!4d-72.333565!16s%2Fg%2F11sswz76yt?hl=es&entry=ttu')

# URL base del sitio para construir enlaces en mensajes
SITE_URL = config('SITE_URL', default='http://localhost:8001')

# Configuración de Email
# Email de la clínica para enviar correos
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='miclinicacontacto@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='rlih chbj etez srst')
# Email desde el cual se enviarán los correos (debe ser el mismo que EMAIL_HOST_USER para Gmail)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='miclinicacontacto@gmail.com')
