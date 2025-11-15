# Generated manually to fix PostgreSQL cita table

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0011_fix_postgresql_table'),
    ]

    operations = [
        # Eliminar la tabla si existe
        migrations.RunSQL(
            "DROP TABLE IF EXISTS citas_cita CASCADE;",
            reverse_sql="-- No reverse needed"
        ),
        # Crear la tabla con la estructura correcta para PostgreSQL
        migrations.RunSQL(
            """
            CREATE TABLE citas_cita (
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