"""
技能库 API
提供技能的列表、执行、历史查询等接口
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .registry import SkillRegistry


class SkillListView(APIView):
    """技能列表"""

    def get(self, request):
        """获取所有已注册技能"""
        skills = []
        for code in SkillRegistry.list_codes():
            cls = SkillRegistry.get(code)
            skills.append({
                'code': cls.code,
                'name': cls.name,
                'description': cls.description,
                'param_schema': cls.param_schema,
                'is_enabled': cls.is_enabled,
            })
        return Response({'skills': skills})


class SkillExecuteView(APIView):
    """技能执行"""

    def post(self, request):
        """
        执行指定技能

        参数:
        - skill_code: 技能标识
        - config: 技能配置
        - context: 执行上下文（可选）
        """
        skill_code = request.data.get('skill_code')
        config = request.data.get('config', {})
        context = request.data.get('context', {})

        if not skill_code:
            return Response({'error': '缺少 skill_code'}, status=status.HTTP_400_BAD_REQUEST)

        skill_class = SkillRegistry.get(skill_code)
        if skill_class is None:
            return Response({'error': f'未知技能: {skill_code}'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证配置
        error = skill_class().validate_config(config)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        # 执行
        result = skill_class().execute(config, context)

        return Response({
            'skill_code': skill_code,
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'duration_ms': result.duration_ms,
        })


class SkillDetailView(APIView):
    """技能详情"""

    def get(self, request, skill_code):
        """获取技能详情"""
        skill_class = SkillRegistry.get(skill_code)
        if skill_class is None:
            return Response({'error': f'未知技能: {skill_code}'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'code': skill_class.code,
            'name': skill_class.name,
            'description': skill_class.description,
            'param_schema': skill_class.param_schema,
            'is_enabled': skill_class.is_enabled,
        })
