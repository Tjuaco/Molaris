# Generated manually to recreate cita table with correct foreign key
# Esta migración es un no-op ya que la tabla se crea correctamente en migraciones anteriores
# y las migraciones posteriores (0013, 0014) la corrigen para PostgreSQL

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0008_perfil_puede_crear_odontogramas_and_more'),
    ]

    operations = [
        # Esta migración es un no-op porque:
        # 1. La tabla citas_cita ya existe desde migraciones anteriores
        # 2. Las migraciones 0013 y 0014 corrigen la estructura para PostgreSQL
        # 3. El SQL original tenía sintaxis de SQLite que no funciona con PostgreSQL
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=migrations.RunSQL.noop
        ),
    ]