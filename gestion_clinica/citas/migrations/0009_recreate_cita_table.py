# Generated manually to recreate cita table with correct foreign key

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0008_perfil_puede_crear_odontogramas_and_more'),
    ]

    operations = [
        # Recrear la tabla citas_cita con la estructura correcta
        migrations.RunSQL(
            """
            CREATE TABLE citas_cita (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora DATETIME NOT NULL,
                tipo_consulta VARCHAR(50) NOT NULL,
                notas TEXT,
                estado VARCHAR(20) NOT NULL DEFAULT 'disponible',
                cliente_id INTEGER REFERENCES citas_cliente(id) ON DELETE SET NULL,
                dentista_id INTEGER REFERENCES citas_perfil(id) ON DELETE SET NULL,
                creada_por_id INTEGER REFERENCES citas_perfil(id) ON DELETE SET NULL,
                creada_el DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actualizada_el DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS citas_cita;"
        ),
    ]