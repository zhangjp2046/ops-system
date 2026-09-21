# Generated migration for alert threshold models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0003_customer_api_key_customer_api_secret_and_more'),
        ('assets', '0005_alter_asset_status_alter_assetstatushistory_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('alerts', '0002_alter_alert_source'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertThreshold',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('check_item_code', models.CharField(max_length=50, verbose_name='检查项编码')),
                ('check_item_name', models.CharField(max_length=100, verbose_name='检查项名称')),
                ('protocol', models.CharField(choices=[('mysql', 'MySQL'), ('mssql', 'MSSQL'), ('oracle', 'Oracle'), ('postgresql', 'PostgreSQL'), ('snmp', 'SNMP'), ('ssh', 'SSH'), ('ping', 'Ping'), ('port', '端口检测')], max_length=20, verbose_name='协议类型')),
                ('threshold_direction', models.CharField(choices=[('upper', '越高越严重'), ('lower', '越低越严重'), ('range', '偏离范围严重'), ('exact', '精确匹配')], default='upper', max_length=10, verbose_name='阈值方向')),
                ('value_type', models.CharField(choices=[('number', '数值'), ('percentage', '百分比'), ('string', '字符串'), ('boolean', '布尔值')], default='number', max_length=20, verbose_name='值类型')),
                ('warning_threshold', models.CharField(blank=True, max_length=100, verbose_name='警告阈值')),
                ('error_threshold', models.CharField(blank=True, max_length=100, verbose_name='错误阈值')),
                ('critical_threshold', models.CharField(blank=True, max_length=100, verbose_name='严重阈值')),
                ('unit', models.CharField(blank=True, default='%', max_length=20, verbose_name='单位')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('config', models.JSONField(blank=True, default=dict, verbose_name='扩展配置')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('asset_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alert_thresholds', to='assets.assettype', verbose_name='资产类型')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alert_thresholds', to='customers.customer', verbose_name='客户')),
            ],
            options={
                'verbose_name': '告警阈值',
                'verbose_name_plural': '告警阈值配置',
                'db_table': 'alert_thresholds',
                'ordering': ['protocol', 'check_item_code'],
            },
        ),
        migrations.CreateModel(
            name='AlertThresholdRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('severity', models.IntegerField(choices=[(1, '信息'), (2, '警告'), (3, '错误'), (4, '严重')], verbose_name='严重程度')),
                ('operator', models.CharField(choices=[('>', '大于'), ('<', '小于'), ('>=', '大于等于'), ('<=', '小于等于'), ('=', '等于'), ('!=', '不等于'), ('contains', '包含'), ('not_contains', '不包含'), ('regex', '正则匹配')], max_length=20, verbose_name='操作符')),
                ('threshold_value', models.CharField(max_length=100, verbose_name='阈值')),
                ('rule_name', models.CharField(blank=True, max_length=100, verbose_name='规则名称')),
                ('description', models.TextField(blank=True, verbose_name='规则描述')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('threshold', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='alerts.alertthreshold', verbose_name='阈值配置')),
            ],
            options={
                'verbose_name': '阈值规则',
                'verbose_name_plural': '阈值规则',
                'db_table': 'alert_threshold_rules',
                'ordering': ['threshold', '-severity', 'sort_order'],
            },
        ),
        migrations.CreateModel(
            name='AlertThresholdTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='模板名称')),
                ('protocol', models.CharField(max_length=20, verbose_name='协议类型')),
                ('check_item_code', models.CharField(max_length=50, verbose_name='检查项编码')),
                ('check_item_name', models.CharField(max_length=100, verbose_name='检查项名称')),
                ('default_config', models.JSONField(default=dict, verbose_name='默认配置')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('is_system', models.BooleanField(default=False, verbose_name='是否系统模板')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '阈值模板',
                'verbose_name_plural': '阈值模板',
                'db_table': 'alert_threshold_templates',
                'ordering': ['protocol', 'check_item_code'],
            },
        ),
        migrations.AddIndex(
            model_name='alertthreshold',
            index=models.Index(fields=['customer', 'is_active'], name='alert_thres_custome_8b4c5a_idx'),
        ),
        migrations.AddIndex(
            model_name='alertthreshold',
            index=models.Index(fields=['protocol'], name='alert_thres_protoco_a5d3f2_idx'),
        ),
        migrations.AddIndex(
            model_name='alertthreshold',
            index=models.Index(fields=['check_item_code'], name='alert_thres_check_i_c8e7d1_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='alertthreshold',
            unique_together={('customer', 'asset_type', 'check_item_code')},
        ),
        migrations.AddIndex(
            model_name='alertthresholdrule',
            index=models.Index(fields=['threshold', 'severity'], name='alert_thres_thresho_f3a9b2_idx'),
        ),
    ]
