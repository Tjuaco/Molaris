#!/bin/bash
set -e

# Ejecutar migraciones (ya estamos en /app que es el Root Directory cliente_web)
echo "Running migrations..."
python manage.py migrate --noinput

# Iniciar Gunicorn
echo "Starting Gunicorn..."
exec gunicorn cliente_web.wsgi:application \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

