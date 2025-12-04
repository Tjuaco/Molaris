#!/bin/bash
set -e

cd /app/gestion_clinica

# Ejecutar migraciones
echo "Running migrations..."
python manage.py migrate --noinput

# Iniciar Gunicorn
echo "Starting Gunicorn..."
exec gunicorn gestion_clinica.wsgi:application \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

