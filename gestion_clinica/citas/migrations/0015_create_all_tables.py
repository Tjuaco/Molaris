# Generated manually to create all tables from scratch

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0014_create_cita_table_final'),
    ]

    operations = [
        # Crear todas las tablas necesarias desde cero
        migrations.RunSQL(
            """
            -- Crear tabla citas_perfil si no existe
            CREATE TABLE IF NOT EXISTS citas_perfil (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
                nombre_completo VARCHAR(150) NOT NULL,
                telefono VARCHAR(20),
                email VARCHAR(254),
                rol VARCHAR(20) NOT NULL,
                especialidad VARCHAR(100),
                numero_colegio VARCHAR(50),
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS citas_perfil CASCADE;"
        ),
        migrations.RunSQL(
            """
            -- Crear tabla citas_cliente si no existe
            CREATE TABLE IF NOT EXISTS citas_cliente (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(254) NOT NULL,
                telefono VARCHAR(20),
                fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS citas_cliente CASCADE;"
        ),
        migrations.RunSQL(
            """
            -- Crear tabla citas_cita
            CREATE TABLE IF NOT EXISTS citas_cita (
                id SERIAL PRIMARY KEY,
                fecha_hora TIMESTAMP NOT NULL,
                tipo_consulta VARCHAR(50) NOT NULL,
                notas TEXT,
                estado VARCHAR(20) NOT NULL DEFAULT 'disponible',
                cliente_id INTEGER REFERENCES citas_cliente(id) ON DELETE SET NULL,
                dentista_id INTEGER REFERENCES citas_perfil(id) ON DELETE SET NULL,
                creada_por_id INTEGER REFERENCES citas_perfil(id) ON DELETE SET NULL,
                creada_el TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actualizada_el TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS citas_cita CASCADE;"
        ),
    ]