# Instrucciones para Subir el Proyecto a GitHub

## Paso 1: Configurar Git (si aún no lo has hecho)

Antes de hacer el commit, necesitas configurar tu identidad en Git:

```bash
git config user.email "tu-email@ejemplo.com"
git config user.name "Tu Nombre"
```

O si quieres configurarlo globalmente para todos tus repositorios:

```bash
git config --global user.email "tu-email@ejemplo.com"
git config --global user.name "Tu Nombre"
```

## Paso 2: Hacer el Commit Inicial

Una vez configurado Git, haz el commit:

```bash
git commit -m "Commit inicial: Sistema de gestión clínica dental con dos proyectos Django"
```

## Paso 3: Crear el Repositorio en GitHub

1. Ve a [GitHub.com](https://github.com) e inicia sesión
2. Haz clic en el botón **"+"** en la esquina superior derecha
3. Selecciona **"New repository"**
4. Completa el formulario:
   - **Repository name**: `gestion-clinica-dental` (o el nombre que prefieras)
   - **Description**: "Sistema de gestión para clínica dental con portal de clientes"
   - **Visibility**: Elige **Private** (recomendado) o **Public**
   - **NO marques** "Initialize this repository with a README" (ya tenemos uno)
   - **NO agregues** .gitignore ni licencia (ya los tenemos)
5. Haz clic en **"Create repository"**

## Paso 4: Conectar el Repositorio Local con GitHub

GitHub te mostrará instrucciones. Ejecuta estos comandos (reemplaza `TU_USUARIO` con tu usuario de GitHub):

```bash
git remote add origin https://github.com/TU_USUARIO/gestion-clinica-dental.git
git branch -M main
git push -u origin main
```

Si GitHub te muestra una URL diferente, usa esa en lugar de la del ejemplo.

## Paso 5: Verificar que se Subió Correctamente

1. Refresca la página de GitHub
2. Deberías ver todos tus archivos en el repositorio
3. Verifica que el archivo `.gitignore` esté presente y que `venv/` y archivos sensibles NO estén visibles

## Importante: Configuración de Credenciales

⚠️ **ADVERTENCIA**: Los archivos `settings.py` contienen credenciales sensibles (contraseñas de base de datos, tokens, etc.). 

**Para tu compañero:**

1. Después de clonar el repositorio, debe crear sus propios archivos de configuración
2. Las credenciales en `settings.py` son solo para desarrollo local
3. Cada desarrollador debe usar sus propias credenciales de:
   - Base de datos PostgreSQL
   - Email (Gmail u otro proveedor)
   - Twilio (si aplica)
   - Otras APIs externas

## Para tu Compañero: Clonar y Configurar

Tu compañero debe seguir estos pasos:

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/gestion-clinica-dental.git
cd gestion-clinica-dental

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar base de datos PostgreSQL
# (Debe crear la base de datos 'clinica_db' y configurar credenciales en settings.py)

# 6. Aplicar migraciones
cd gestion_clinica
python manage.py migrate
python manage.py createsuperuser
cd ../cliente_web
python manage.py migrate
python manage.py createsuperuser
cd ..
```

## Solución de Problemas

### Si Git pide credenciales al hacer push:

1. **Opción 1**: Usa un Personal Access Token de GitHub
   - Ve a GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Genera un nuevo token con permisos `repo`
   - Úsalo como contraseña cuando Git lo pida

2. **Opción 2**: Configura SSH (más seguro a largo plazo)
   - Genera una clave SSH: `ssh-keygen -t ed25519 -C "tu-email@ejemplo.com"`
   - Agrega la clave pública a GitHub: Settings → SSH and GPG keys
   - Cambia la URL del remote: `git remote set-url origin git@github.com:TU_USUARIO/gestion-clinica-dental.git`

### Si hay conflictos con archivos grandes:

Si tienes archivos muy grandes (como imágenes en `media/`), considera usar Git LFS:
```bash
git lfs install
git lfs track "*.png"
git lfs track "*.jpg"
git add .gitattributes
```

## Próximos Pasos

Una vez que el repositorio esté en GitHub:

1. Invita a tu compañero como colaborador:
   - Ve a Settings → Collaborators → Add people
   - Ingresa el usuario de GitHub de tu compañero

2. Considera crear ramas para desarrollo:
   ```bash
   git checkout -b develop
   git push -u origin develop
   ```

3. Establece reglas de trabajo en equipo:
   - Usar ramas para features nuevas
   - Hacer pull antes de trabajar
   - Hacer commits frecuentes con mensajes descriptivos

