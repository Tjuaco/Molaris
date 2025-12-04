# Generated manually to fix PostgreSQL table
# Esta migración es un no-op ya que la tabla se crea correctamente en migraciones anteriores
# y las migraciones posteriores (0013, 0014) la corrigen para PostgreSQL

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0010_recreate_cita_table_final'),
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
