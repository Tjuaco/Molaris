# Generated manually to create cita table using Django ORM

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0013_fix_postgresql_cita_table'),
    ]

    operations = [
        # Eliminar la tabla si existe
        migrations.RunSQL(
            "DROP TABLE IF EXISTS citas_cita CASCADE;",
            reverse_sql="-- No reverse needed"
        ),
        # Crear la tabla usando el ORM de Django
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_hora', models.DateTimeField()),
                ('tipo_consulta', models.CharField(max_length=50)),
                ('notas', models.TextField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('disponible', 'Disponible'), ('reservada', 'Reservada'), ('completada', 'Completada'), ('cancelada', 'Cancelada')], default='disponible', max_length=20)),
                ('creada_el', models.DateTimeField(auto_now_add=True)),
                ('actualizada_el', models.DateTimeField(auto_now=True)),
                ('cliente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='citas.cliente')),
                ('creada_por', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='citas_creadas', to='citas.perfil')),
                ('dentista', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citas_asignadas', to='citas.perfil')),
            ],
            options={
                'verbose_name': 'Cita',
                'verbose_name_plural': 'Citas',
                'ordering': ['fecha_hora'],
            },
        ),
    ]