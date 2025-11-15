# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0018_mensaje'),
    ]

    operations = [
        migrations.AddField(
            model_name='mensaje',
            name='archivo_adjunto',
            field=models.FileField(blank=True, null=True, upload_to='mensajes/archivos/%Y/%m/', verbose_name='Archivo Adjunto'),
        ),
    ]
































