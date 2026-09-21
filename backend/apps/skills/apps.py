from django.apps import AppConfig


class SkillsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.skills'
    verbose_name = '技能库'

    def ready(self):
        # 在 Django 完全加载后才导入技能，触发注册
        from . import registry    # noqa: F401
        from . import inspection  # noqa: F401
        from . import push        # noqa: F401
        from . import ops         # noqa: F401
        from . import dashboard   # noqa: F401
