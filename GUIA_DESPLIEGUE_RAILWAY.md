# 🚂 Guía Completa de Despliegue en Railway - Molaris

Esta guía te ayudará a desplegar ambos proyectos Django (`gestion_clinica` y `cliente_web`) en Railway.

## 📋 Pre-requisitos

- ✅ Cuenta en GitHub (ya tienes el repositorio: https://github.com/Tjuaco/Molaris.git)
- ✅ Cuenta en Railway (gratis en https://railway.app)
- ✅ Credenciales de Twilio (si usas SMS/WhatsApp)
- ✅ Credenciales de email (Gmail u otro proveedor)

---

## 🎯 Paso 1: Crear cuenta en Railway

1. Ve a https://railway.app
2. Click en **"Start a New Project"** o **"Login"**
3. Inicia sesión con tu cuenta de **GitHub**
4. Autoriza Railway para acceder a tus repositorios

---

## 🗄️ Paso 2: Crear Base de Datos PostgreSQL

1. En el dashboard de Railway, click en **"+ New Project"**
2. Selecciona **"Empty Project"**
3. Click en **"+ New"** → **"Database"** → **"Add PostgreSQL"**
4. Railway creará automáticamente una base de datos PostgreSQL
5. **IMPORTANTE**: Copia las variables de conexión que Railway te muestra:
   - `DATABASE_URL` (esta es la más importante)
   - `PGHOST`
   - `PGPORT`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGDATABASE`

**Guarda estas credenciales**, las necesitarás para ambos servicios.

---

## 🔧 Paso 3: Desplegar `gestion_clinica` (Sistema de Gestión)

### 3.1. Crear el servicio

1. En el mismo proyecto de Railway, click en **"+ New"**
2. Selecciona **"GitHub Repo"**
3. Busca y selecciona tu repositorio: **`Tjuaco/Molaris`**
4. Railway detectará automáticamente el proyecto

### 3.2. Configurar el servicio

1. Click en el servicio recién creado
2. Ve a la pestaña **"Settings"**
3. En **"Root Directory"**, escribe: `gestion_clinica`
4. En **"Start Command"**, deja vacío (Railway usará el `Procfile`)
5. En **"Build Command"**, deja vacío

### 3.3. Conectar la base de datos

1. En el servicio de `gestion_clinica`, ve a **"Variables"**
2. Click en **"Reference Variable"**
3. Selecciona tu base de datos PostgreSQL
4. Railway agregará automáticamente `DATABASE_URL`

### 3.4. Configurar Variables de Entorno

En **"Variables"**, agrega las siguientes variables:

#### Variables Obligatorias:
```
DEBUG=False
SECRET_KEY=tu-clave-secreta-muy-larga-y-aleatoria-genera-una-nueva
ALLOWED_HOSTS=*.railway.app,tu-dominio.com
DB_ENGINE=postgresql
```

#### Variables de Twilio:
```
TWILIO_ACCOUNT_SID=tu-account-sid
TWILIO_AUTH_TOKEN=tu-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

#### Variables de Email:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=tu-email@gmail.com
```

#### Variables de la Clínica:
```
CLINIC_NAME=Clínica Dental San Felipe
SITE_URL=https://gestion-clinica-tu-proyecto.railway.app
```

**Nota**: `SITE_URL` la actualizarás después de obtener la URL de Railway.

### 3.5. Desplegar

1. Railway comenzará a desplegar automáticamente
2. Espera a que termine el despliegue
3. Railway te dará una URL tipo: `gestion-clinica-xxxxx.railway.app`
4. **Copia esta URL**, la necesitarás para `cliente_web`

---

## 🌐 Paso 4: Desplegar `cliente_web` (Portal de Clientes)

### 4.1. Crear el segundo servicio

1. En el mismo proyecto de Railway, click en **"+ New"**
2. Selecciona **"GitHub Repo"**
3. Selecciona el mismo repositorio: **`Tjuaco/Molaris`**

### 4.2. Configurar el servicio

1. Click en el servicio recién creado
2. Ve a la pestaña **"Settings"**
3. En **"Root Directory"**, escribe: `cliente_web`
4. En **"Start Command"**, deja vacío
5. En **"Build Command"**, deja vacío

### 4.3. Conectar la misma base de datos

1. En el servicio de `cliente_web`, ve a **"Variables"**
2. Click en **"Reference Variable"**
3. Selecciona la **misma base de datos PostgreSQL** que usaste para `gestion_clinica`
4. Railway agregará automáticamente `DATABASE_URL`

### 4.4. Configurar Variables de Entorno

En **"Variables"**, agrega las siguientes variables:

#### Variables Obligatorias:
```
DEBUG=False
SECRET_KEY=otra-clave-secreta-diferente-genera-una-nueva
ALLOWED_HOSTS=*.railway.app,tu-dominio.com
```

#### Variables de Conexión con `gestion_clinica`:
```
GESTION_API_URL=https://gestion-clinica-xxxxx.railway.app/api
GESTION_BASE_URL=https://gestion-clinica-xxxxx.railway.app
GESTION_API_TOKEN=
```

**IMPORTANTE**: Reemplaza `gestion-clinica-xxxxx.railway.app` con la URL real que obtuviste en el Paso 3.5.

#### Variables de Twilio (opcionales, si las usas):
```
TWILIO_ACCOUNT_SID=tu-account-sid
TWILIO_AUTH_TOKEN=tu-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

#### Variables de Email:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
EMAIL_FROM=tu-email@gmail.com
DEFAULT_FROM_EMAIL=tu-email@gmail.com
```

#### Variables de la Clínica:
```
CLINIC_NAME=Clínica Dental San Felipe
SITE_URL=https://cliente-web-xxxxx.railway.app
```

**Nota**: `SITE_URL` la actualizarás después de obtener la URL de Railway.

### 4.5. Desplegar

1. Railway comenzará a desplegar automáticamente
2. Espera a que termine el despliegue
3. Railway te dará una URL tipo: `cliente-web-xxxxx.railway.app`

---

## ✅ Paso 5: Verificar el Despliegue

### 5.1. Verificar `gestion_clinica`

1. Visita la URL de `gestion_clinica`: `https://gestion-clinica-xxxxx.railway.app`
2. Deberías ver la página de login
3. Si hay errores, revisa los logs en Railway → **"Deployments"** → **"View Logs"**

### 5.2. Verificar `cliente_web`

1. Visita la URL de `cliente_web`: `https://cliente-web-xxxxx.railway.app`
2. Deberías ver la página de inicio
3. Si hay errores, revisa los logs

### 5.3. Crear Superusuario

Para crear un superusuario en `gestion_clinica`:

1. En Railway, ve al servicio de `gestion_clinica`
2. Click en **"Deployments"** → Click en el deployment activo
3. Click en **"View Logs"** → Abre la terminal
4. Ejecuta:
```bash
cd gestion_clinica
python manage.py createsuperuser
```

Repite el proceso para `cliente_web` si necesitas un superusuario allí también.

---

## 🔄 Paso 6: Actualizar URLs de Intercomunicación

Después de obtener las URLs finales de ambos servicios:

### 6.1. Actualizar `gestion_clinica`

1. Ve a **"Variables"** del servicio `gestion_clinica`
2. Actualiza:
```
SITE_URL=https://gestion-clinica-xxxxx.railway.app
```

### 6.2. Actualizar `cliente_web`

1. Ve a **"Variables"** del servicio `cliente_web`
2. Actualiza:
```
GESTION_API_URL=https://gestion-clinica-xxxxx.railway.app/api
GESTION_BASE_URL=https://gestion-clinica-xxxxx.railway.app
SITE_URL=https://cliente-web-xxxxx.railway.app
```

3. Railway redeployará automáticamente con las nuevas variables

---

## 🎨 Paso 7: Configurar Dominios Personalizados (Opcional)

Si quieres usar dominios personalizados:

1. En Railway, ve a **"Settings"** del servicio
2. Click en **"Domains"**
3. Agrega tu dominio personalizado
4. Sigue las instrucciones de Railway para configurar DNS

---

## 📝 Resumen de Variables de Entorno

### Para `gestion_clinica`:
- `DEBUG=False`
- `SECRET_KEY` (genera una nueva)
- `ALLOWED_HOSTS=*.railway.app`
- `DATABASE_URL` (automático desde Railway)
- `TWILIO_*` (tus credenciales)
- `EMAIL_*` (tus credenciales)
- `SITE_URL` (URL de Railway)

### Para `cliente_web`:
- `DEBUG=False`
- `SECRET_KEY` (genera una diferente)
- `ALLOWED_HOSTS=*.railway.app`
- `DATABASE_URL` (misma que gestion_clinica)
- `GESTION_API_URL` (URL de gestion_clinica + /api)
- `GESTION_BASE_URL` (URL de gestion_clinica)
- `SITE_URL` (URL de Railway)

---

## ⚠️ Problemas Comunes y Soluciones

### Error: "No module named 'gunicorn'"
**Solución**: Verifica que `requirements.txt` incluya `gunicorn==21.2.0`

### Error: "Static files not found"
**Solución**: Verifica que `whitenoise` esté en `requirements.txt` y en `MIDDLEWARE`

### Error: "Database connection failed"
**Solución**: Verifica que `DATABASE_URL` esté configurado correctamente en ambos servicios

### Error: "Connection refused" entre servicios
**Solución**: Verifica que `GESTION_API_URL` y `GESTION_BASE_URL` apunten a la URL correcta de `gestion_clinica`

### Error: "ALLOWED_HOSTS"
**Solución**: Agrega `*.railway.app` a `ALLOWED_HOSTS`

---

## 🎉 ¡Listo!

Ahora tienes ambos servicios desplegados en Railway y comunicándose entre sí.

**URLs de tus servicios:**
- Sistema de Gestión: `https://gestion-clinica-xxxxx.railway.app`
- Portal de Clientes: `https://cliente-web-xxxxx.railway.app`

---

## 📞 ¿Necesitas ayuda?

Si encuentras algún problema durante el despliegue:
1. Revisa los logs en Railway
2. Verifica que todas las variables de entorno estén configuradas
3. Asegúrate de que ambos servicios usen la misma base de datos

