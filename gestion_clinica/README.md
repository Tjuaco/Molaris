# 🦷 Gestión Clínica Dental

Sistema web para gestionar citas, pacientes, odontogramas y radiografías.

## 🚀 Instalación Rápida

### 1. Clonar
```bash
git clone https://github.com/tu-usuario/gestion-clinica-dental.git
cd gestion-clinica-dental/gestion_clinica
```

### 2. Crear entorno virtual

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
copy .env.example .env
# Editar .env con tus credenciales
```

### 5. Crear base de datos PostgreSQL
```bash
psql -U postgres

# Dentro de PostgreSQL:
CREATE DATABASE clinica_db;
CREATE USER clinica_user WITH PASSWORD 'tu_contraseña';
ALTER ROLE clinica_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE clinica_db TO clinica_user;
\q
```

### 6. Ejecutar migraciones
```bash
python manage.py migrate
```

### 7. Crear superusuario
```bash
python manage.py createsuperuser
```

### 8. Iniciar servidor
```bash
python manage.py runserver
```

Ir a: http://localhost:8000

---

## 📋 Requisitos

- Python 3.10+
- PostgreSQL 12+

---

## 👥 Colaboración

```bash
# Actualizar cambios
git pull origin main

# Crear rama nueva
git checkout -b feature/tu-nombre

# Hacer cambios...

# Subir cambios
git add .
git commit -m "Descripción del cambio"
git push origin feature/tu-nombre
```

---

## ⚠️ Importante

- NUNCA subir `.env` con credenciales reales
- Cambiar `SECRET_KEY` en producción
- DEBUG debe ser `False` en producción