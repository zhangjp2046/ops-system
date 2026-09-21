"""
知识包接收 API
接收 ops-center 主动推送的知识包更新
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def receive_knowledge_pack(request):
    """
    接收 ops-center 推送的知识包更新。

    POST /api/knowledge/receive-pack/
    Header: X-Update-Token: <共享密钥>
    Body: 完整知识包 JSON
    """
    # 验证密钥
    token = request.headers.get('X-Update-Token', '') or request.META.get('HTTP_X_UPDATE_TOKEN', '')
    if not token:
        return JsonResponse({'success': False, 'message': '缺少 X-Update-Token'}, status=401)

    # 验证 token（从系统设置读取）
    try:
        from apps.system.models import SystemSetting
        expected = SystemSetting.get('knowledge.update_token', '')
        if not expected:
            return JsonResponse({'success': False, 'message': '未配置更新密钥'}, status=401)
        if token != expected:
            return JsonResponse({'success': False, 'message': '更新密钥无效'}, status=401)
    except Exception:
        return JsonResponse({'success': False, 'message': '验证失败'}, status=500)

    # 解析请求体
    try:
        pack = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': '数据格式错误'}, status=400)

    version = pack.get('version', '')
    if not version:
        return JsonResponse({'success': False, 'message': '缺少版本号'}, status=400)

    # 应用知识包
    try:
        from apps.dashboard.knowledge_updater import apply_pack
        data = pack.get('data', {})
        result = apply_pack(data)
        return JsonResponse({
            'success': True,
            'version': version,
            'applied': result.get('applied', []),
            'stats': result.get('stats', {}),
        })
    except Exception as e:
        logger.exception(f'应用知识包失败: {e}')
        return JsonResponse({
            'success': False,
            'message': f'应用失败: {str(e)}',
        }, status=500)


@csrf_exempt
@require_POST
def trigger_knowledge_sync(request):
    """
    接收 ops-center 的同步触发信号。
    ops-center 发送此信号告知 ops-system 有新版本知识包。
    ops-system 收到后异步调用 check_and_update()。

    POST /api/knowledge/trigger-sync/
    Header: X-Update-Token: <共享密钥>
    Body: {"version": "1.0.0"}
    """
    # 验证密钥（同上）
    token = request.headers.get('X-Update-Token', '') or request.META.get('HTTP_X_UPDATE_TOKEN', '')
    try:
        from apps.system.models import SystemSetting
        expected = SystemSetting.get('knowledge.update_token', '')
        if not token or token != expected:
            return JsonResponse({'success': False, 'message': '无效密钥'}, status=401)
    except Exception:
        return JsonResponse({'success': False, 'message': '验证失败'}, status=500)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': '数据格式错误'}, status=400)

    new_version = body.get('version', '')

    # 异步触发同步（使用线程）
    import threading
    from apps.dashboard.knowledge_updater import check_and_update

    def _sync():
        try:
            result = check_and_update()
            if result.get('updated'):
                logger.info(f'知识包同步成功: {result.get("version")}')
            else:
                logger.info(f'知识包无需更新: {result.get("message", "")}')
        except Exception as e:
            logger.error(f'知识包同步异常: {e}')

    t = threading.Thread(target=_sync, daemon=True)
    t.start()

    return JsonResponse({
        'success': True,
        'message': f'知识包同步已触发 (版本: {new_version})',
    })


@require_GET
def check_knowledge_status(request):
    """
    检查本地知识包状态（供前端仪表盘使用）。

    GET /api/knowledge/status/
    """
    from apps.dashboard.knowledge_updater import check_version, _get_cached_version

    cached_version = _get_cached_version()
    try:
        remote = check_version()
        needs_update = remote.get('needs_update', False)
        latest_version = remote.get('latest_version', '')
    except Exception as e:
        needs_update = False
        latest_version = ''
        remote = {'error': str(e)}

    return JsonResponse({
        'cached_version': cached_version,
        'latest_version': latest_version or cached_version,
        'needs_update': needs_update,
        'remote_check_success': remote.get('success', False),
        'remote_error': remote.get('error', ''),
    })
