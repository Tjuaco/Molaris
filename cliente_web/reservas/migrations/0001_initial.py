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
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_hora', models.DateTimeField(unique=True)),
                ('paciente_nombre', models.CharField(blank=True, max_length=150, null=True)),
                ('paciente_email', models.CharField(blank=True, max_length=254, null=True)),
                ('paciente_telefono', models.CharField(blank=True, max_length=20, null=True)),
                ('creada_el', models.DateTimeField(default=django.utils.timezone.now)),
                ('actualizada_el', models.DateTimeField(default=django.utils.timezone.now)),
                ('estado', models.CharField(default='disponible', max_length=50)),
                ('notas', models.TextField(blank=True, null=True)),
                ('tipo_consulta', models.CharField(blank=True, max_length=100, null=True)),
                ('creada_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citas_creadas', to='auth.user')),
                ('dentista', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citas_dentista', to='auth.user')),
            ],
            options={
                'db_table': 'citas_cita',
            },
        ),
    ]
