# Generated manually - only adds is_monitoring_item field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0003_alertthreshold_alertthresholdrule_alertthresholdtemplate'),
    ]

    operations = [
        migrations.AddField(
            model_name='alertthreshold',
            name='is_monitoring_item',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='开启后每次巡检将记录该指标的时间序列数据，便于观察变化趋势',
                verbose_name='是否监控项'
            ),
        ),
    ]
