from django.apps import AppConfig


class SchedulerV2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scheduler_v2'
    verbose_name = '任务调度V2'
