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

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo el código del proyecto (Root Directory es cliente_web, así que copiamos todo)
COPY . .

# Copiar script de inicio
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Exponer el puerto (Railway usa variable PORT dinámicamente)
EXPOSE 8080

# Comando de inicio (usar bash explícitamente)
CMD ["/bin/bash", "/app/start.sh"]

