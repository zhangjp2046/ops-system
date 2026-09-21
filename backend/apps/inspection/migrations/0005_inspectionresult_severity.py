from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inspection', '0004_inspectionplan_protocol'),
    ]

    operations = [
        migrations.AddField(
            model_name='inspectionresult',
            name='severity',
            field=models.IntegerField(default=1, verbose_name='严重程度'),
            preserve_default=False,
        ),
    ]
