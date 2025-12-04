#!/bin/bash
set -e

# Mostrar información de debug
echo "=== Starting cliente_web ==="
echo "PORT: ${PORT}"
echo "PWD: $(pwd)"
echo "Python version: $(python --version)"

# Ejecutar migraciones (ya estamos en /app que es el Root Directory cliente_web)
echo "Running migrations..."
python manage.py migrate --noinput || echo "Migration failed, continuing..."

# Recopilar archivos estáticos
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Collectstatic failed, continuing..."

# Iniciar Gunicorn
echo "Starting Gunicorn on port ${PORT:-8080}..."
exec gunicorn cliente_web.wsgi:application \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info

