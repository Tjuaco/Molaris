# Generated manually to match existing PostgreSQL database structure

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # La tabla citas_cita ya existe, creada por gestion_clinica
        # No creamos la tabla aquí porque está marcada como managed = False en el modelo
    ]
