from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import SystemSetting
from .serializers import SystemSettingSerializer, SystemSettingWriteSerializer


class SystemSettingViewSet(viewsets.ModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        cat = self.request.query_params.get('category')
        if cat:
            qs = qs.filter(category=cat)
        return qs

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """获取所有分类"""
        cats = SystemSetting.objects.values_list('category', flat=True).distinct()
        return Response(list(cats))

    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """批量更新设置"""
        ser = SystemSettingWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        for key, value in ser.validated_data['settings'].items():
            try:
                obj = SystemSetting.objects.get(key=key)
                obj.value = value
                obj.save(update_fields=['value', 'updated_at'])
            except SystemSetting.DoesNotExist:
                pass
        return Response({'success': True, 'message': '更新成功'})

    @action(detail=False, methods=['post'])
    def init_defaults(self, request):
        """初始化默认设置"""
        _init_default_settings()
        return Response({'success': True, 'message': '默认设置已初始化'})

    @action(detail=False, methods=['post'])
    def test_push(self, request):
        """测试推送连接"""
        from apps.dashboard.push_service import test_push
        result = test_push()
        code = 200 if result['success'] else 400
        return Response(result, status=code)


def _init_default_settings():
    """初始化系统默认设置"""
    defaults = [
        # 推送设置
        ('push.enabled', 'false', 'push', '启用推送', '是否启用推送到ops-center', 'boolean'),
        ('push.center_url', '', 'push', '中心平台地址', 'ops-center的访问地址，如 http://center.example.com:9000', 'string'),
        ('push.api_key', '', 'push', 'API Key', '租户的API密钥（从ops-center租户管理获取）', 'string', True),
        ('push.push_alerts', 'true', 'push', '推送告警', '是否推送告警到中心平台', 'boolean'),
        ('push.push_inspections', 'true', 'push', '推送巡检', '是否推送巡检结果到中心平台', 'boolean'),
        ('push.push_asset_status', 'true', 'push', '推送资产状态', '是否推送资产在线状态到中心平台', 'boolean'),
        ('push.timeout', '10', 'push', '超时时间(秒)', '推送请求超时时间', 'string'),
        ('push.retry_count', '3', 'push', '重试次数', '推送失败时的重试次数', 'string'),

        # 通知设置
        ('notification.email_host', '', 'notification', 'SMTP服务器', '邮件SMTP服务器地址', 'string'),
        ('notification.email_port', '465', 'notification', 'SMTP端口', '邮件SMTP端口', 'string'),
        ('notification.email_user', '', 'notification', '发件人邮箱', '邮件发件人账号', 'string'),
        ('notification.email_password', '', 'notification', '邮箱密码', '邮件发件人密码', 'string', True),
        ('notification.email_use_ssl', 'true', 'notification', '使用SSL', '邮件是否使用SSL', 'boolean'),
    ]

    for item in defaults:
        key, value, category, label, desc = item[0], item[1], item[2], item[3], item[4]
        field_type = item[5] if len(item) > 5 else 'string'
        is_sensitive = item[6] if len(item) > 6 else False
        SystemSetting.objects.get_or_create(
            key=key,
            defaults={
                'value': value,
                'category': category,
                'label': label,
                'description': desc,
                'field_type': field_type,
                'is_sensitive': is_sensitive,
            }
        )
