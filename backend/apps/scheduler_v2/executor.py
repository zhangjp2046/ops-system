"""
任务执行器
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class TaskExecutor:
    """任务执行器"""
    
    @classmethod
    def execute(cls, task_type, task_config, context=None):
        """执行任务"""
        method_name = f'_do_{task_type}'
        if hasattr(cls, method_name):
            return getattr(cls, method_name)(task_config, context)
        else:
            return {'success': False, 'error': f'未知任务类型: {task_type}'}
    
    @classmethod
    def _do_inspection(cls, task_config, context=None):
        """执行巡检任务"""
        from apps.skills.registry import SkillRegistry
        
        plan_id = task_config.get('inspection_plan_id')
        force = task_config.get('force', False)
        
        if not plan_id:
            return {'success': False, 'error': '缺少 inspection_plan_id'}
        
        try:
            skill = SkillRegistry.get('inspection')()
            result = skill.execute({
                'inspection_plan_id': plan_id,
                'force': force
            }, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'巡检任务执行失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_push_alert(cls, task_config, context=None):
        """执行告警推送"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('push_alert')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'告警推送失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_push_inspection(cls, task_config, context=None):
        """执行巡检结果推送"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('push_inspection')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'巡检结果推送失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_push_status(cls, task_config, context=None):
        """执行状态推送"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('push_status')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'状态推送失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_status_refresh(cls, task_config, context=None):
        """执行状态刷新"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('status_refresh')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'状态刷新失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_discovery_scan(cls, task_config, context=None):
        """执行发现扫描"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('discovery_scan')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'发现扫描失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_cleanup(cls, task_config, context=None):
        """执行数据清理"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('cleanup')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'数据清理失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_report(cls, task_config, context=None):
        """执行报表生成"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('report')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'报表生成失败: {e}')
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _do_dashboard_refresh(cls, task_config, context=None):
        """执行仪表盘刷新"""
        from apps.skills.registry import SkillRegistry
        
        try:
            skill = SkillRegistry.get('dashboard_refresh')()
            result = skill.execute(task_config, context or {})
            return {'success': result.success, 'data': result.data, 'error': result.error}
        except Exception as e:
            logger.exception(f'仪表盘刷新失败: {e}')
            return {'success': False, 'error': str(e)}
