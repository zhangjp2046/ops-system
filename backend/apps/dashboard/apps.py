from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = '驾驶舱'

    def ready(self):
        # 启动心跳后台线程
        try:
            from .push_service import start_heartbeat
            start_heartbeat()
        except Exception:
            pass
