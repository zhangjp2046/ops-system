from django.db import models


class SystemSetting(models.Model):
    """系统全局设置（键值对）"""

    CATEGORY_CHOICES = [
        ('general', '基本设置'),
        ('push', '推送设置'),
        ('notification', '通知设置'),
        ('security', '安全设置'),
    ]

    key = models.CharField('键', max_length=100, unique=True)
    value = models.TextField('值', blank=True, default='')
    category = models.CharField('分类', max_length=50, choices=CATEGORY_CHOICES, default='general')
    label = models.CharField('显示名称', max_length=200, blank=True)
    description = models.TextField('描述', blank=True)
    field_type = models.CharField('字段类型', max_length=20, default='string',
                                   help_text='string/boolean/json/password/select')
    options = models.JSONField('选项列表', default=list, blank=True)
    is_sensitive = models.BooleanField('敏感信息', default=False, help_text='如密码、Token等，前端展示时脱敏')

    updated_at = models.DateTimeField('更新时间', auto_now=True)
    updated_by = models.CharField('更新人', max_length=100, blank=True)

    class Meta:
        db_table = 'system_settings'
        verbose_name = '系统设置'
        verbose_name_plural = '系统设置'
        ordering = ['category', 'key']

    def __str__(self):
        return f'{self.label or self.key}: {self.value[:30]}'

    @classmethod
    def get(cls, key, default=''):
        """获取设置值"""
        try:
            obj = cls.objects.get(key=key)
            return obj.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_bool(cls, key, default=False):
        val = cls.get(key, '')
        if val.lower() in ('true', '1', 'yes'):
            return True
        if val.lower() in ('false', '0', 'no'):
            return False
        return default

    @classmethod
    def get_json(cls, key, default=None):
        import json
        val = cls.get(key, '')
        if not val:
            return default or {}
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default or {}

    @classmethod
    def set(cls, key, value, category='general', label='', description='', field_type='string', options=None, is_sensitive=False, user=''):
        """设置值"""
        obj, _ = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': str(value),
                'category': category,
                'label': label or key,
                'description': description,
                'field_type': field_type,
                'options': options or [],
                'is_sensitive': is_sensitive,
                'updated_by': user,
            }
        )
        return obj
