# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0019_mensaje_archivo_adjunto'),
    ]

    operations = [
        migrations.AddField(
            model_name='insumo',
            name='imagen',
            field=models.ImageField(blank=True, null=True, upload_to='insumos/imagenes/', verbose_name='Imagen del Insumo'),
        ),
    ]






























