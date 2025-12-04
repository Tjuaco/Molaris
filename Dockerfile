# Usar imagen base de Python
FROM python:3.11.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements.txt primero (para cachear la instalación)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Cambiar al directorio de gestion_clinica
WORKDIR /app/gestion_clinica

# Recopilar archivos estáticos
RUN python manage.py collectstatic --noinput

# Exponer el puerto
EXPOSE $PORT

# Comando de inicio
CMD python manage.py migrate --noinput && \
    gunicorn gestion_clinica.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120

