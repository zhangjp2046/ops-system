"""
Scheduler V2 Serializers
"""
from rest_framework import serializers
from .models import Plan, PlanTask, PlanExecution, TaskInstance, TaskTemplate, AdhocTask


def build_cron_from_schedule(schedule_type, daily_time, weekday, day_of_month, interval_value, interval_unit):
    """根据调度类型构建 cron 表达式(前端传入北京时间,转换为UTC存储)"""
    if schedule_type in ['daily', 'weekly', 'monthly'] and daily_time:
        try:
            hour, minute = daily_time.split(':')
            hour = int(hour)
            minute = int(minute)
        except:
            hour, minute = 9, 0

        # 北京时间转UTC(减8小时)
        utc_hour = (hour - 8) % 24

        if schedule_type == 'daily':
            return f"{minute} {utc_hour} * * *"
        elif schedule_type == 'weekly':
            return f"{minute} {utc_hour} * * {weekday or 0}"
        elif schedule_type == 'monthly':
            return f"{minute} {utc_hour} {day_of_month or 1} * *"
    elif schedule_type == 'interval':
        seconds = interval_value * 3600 if interval_unit == 'hours' else interval_value * 60 if interval_unit == 'minutes' else interval_value
        return None, seconds
    return None, None


class PlanTaskSerializer(serializers.ModelSerializer):
    """计划任务序列化器"""

    class Meta:
        model = PlanTask
        fields = [
            'id', 'plan', 'task_type', 'name', 'description',
            'task_config', 'is_enabled', 'execution_order', 'timeout_seconds',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PlanTaskCreateSerializer(serializers.ModelSerializer):
    """计划任务创建序列化器"""

    class Meta:
        model = PlanTask
        fields = [
            'id', 'task_type', 'name', 'description',
            'task_config', 'is_enabled', 'execution_order', 'timeout_seconds'
        ]


class PlanSerializer(serializers.ModelSerializer):
    """任务计划序列化器"""
    tasks = PlanTaskSerializer(many=True, read_only=True)
    task_count = serializers.SerializerMethodField()
    schedule_info = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'description', 'plan_type', 'status',
            'inspection_plan', 'inspection_plan_name',
            'trigger_mode', 'cron_expression', 'interval_seconds',
            'is_enabled', 'max_concurrent', 'timeout_seconds',
            'next_run_time', 'last_run_time',
            'total_executions', 'success_count', 'failure_count',
            'tasks', 'task_count', 'schedule_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'next_run_time', 'last_run_time',
            'total_executions', 'success_count', 'failure_count',
            'created_at', 'updated_at'
        ]

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_schedule_info(self, obj):
        """从 cron_expression 和 interval_seconds 解析出调度信息（供前端展示）"""
        if obj.interval_seconds:
            if obj.interval_seconds >= 3600:
                return {'schedule_type': 'interval', 'interval_value': obj.interval_seconds // 3600, 'interval_unit': 'hours'}
            else:
                return {'schedule_type': 'interval', 'interval_value': obj.interval_seconds // 60, 'interval_unit': 'minutes'}
        cron = obj.cron_expression or ''
        parts = cron.split()
        if len(parts) >= 5:
            minute, hour, day, month, weekday = parts[0], parts[1], parts[2], parts[3], parts[4]
            # UTC 转北京时间（加8小时），处理跨天情况
            try:
                utc_hour = int(hour)
                beijing_hour = (utc_hour + 8) % 24
                daily_time = f"{beijing_hour:02d}:{minute.zfill(2)}"
            except:
                daily_time = f"{hour}:{minute}"
            if day == '*' and month == '*' and weekday != '*':
                try:
                    return {'schedule_type': 'weekly', 'weekday': int(weekday), 'daily_time': daily_time}
                except:
                    pass
            elif day != '*' and month == '*':
                try:
                    return {'schedule_type': 'monthly', 'day_of_month': int(day), 'daily_time': daily_time}
                except:
                    pass
            elif day == '*' and month == '*' and weekday == '*':
                return {'schedule_type': 'daily', 'daily_time': daily_time}
        return None


class PlanCreateSerializer(serializers.ModelSerializer):
    """计划创建序列化器"""
    # 前端字段(不作为model字段)
    schedule_type = serializers.CharField(required=False, allow_blank=True, write_only=True)
    daily_time = serializers.CharField(required=False, allow_blank=True, write_only=True)
    weekday = serializers.IntegerField(required=False, default=0, write_only=True)
    day_of_month = serializers.IntegerField(required=False, default=1, write_only=True)
    interval_value = serializers.IntegerField(required=False, default=1, write_only=True)
    interval_unit = serializers.CharField(required=False, default='hours', write_only=True)

    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'description', 'plan_type', 'status',
            'inspection_plan', 'inspection_plan_name',
            'trigger_mode', 'cron_expression', 'interval_seconds',
            'is_enabled', 'max_concurrent', 'timeout_seconds',
            # 前端字段
            'schedule_type', 'daily_time', 'weekday', 'day_of_month',
            'interval_value', 'interval_unit'
        ]

    def create(self, validated_data):
        # 提取前端字段
        schedule_type = validated_data.pop('schedule_type', '')
        daily_time = validated_data.pop('daily_time', '09:00')
        weekday = validated_data.pop('weekday', 0)
        day_of_month = validated_data.pop('day_of_month', 1)
        interval_value = validated_data.pop('interval_value', 1)
        interval_unit = validated_data.pop('interval_unit', 'hours')

        # 转换调度配置
        cron = build_cron_from_schedule(schedule_type, daily_time, weekday, day_of_month, interval_value, interval_unit)
        if isinstance(cron, str):
            validated_data['cron_expression'] = cron
        elif isinstance(cron, tuple) and cron[1]:
            validated_data['interval_seconds'] = cron[1]

        return super().create(validated_data)


class PlanUpdateSerializer(serializers.ModelSerializer):
    """计划更新序列化器"""
    # 前端字段(不作为model字段)
    schedule_type = serializers.CharField(required=False, allow_blank=True, write_only=True)
    daily_time = serializers.CharField(required=False, allow_blank=True, write_only=True)
    weekday = serializers.IntegerField(required=False, default=0, write_only=True)
    day_of_month = serializers.IntegerField(required=False, default=1, write_only=True)
    interval_value = serializers.IntegerField(required=False, default=1, write_only=True)
    interval_unit = serializers.CharField(required=False, default='hours', write_only=True)

    class Meta:
        model = Plan
        fields = [
            'name', 'description', 'plan_type', 'status',
            'inspection_plan', 'inspection_plan_name',
            'trigger_mode', 'cron_expression', 'interval_seconds',
            'is_enabled', 'max_concurrent', 'timeout_seconds',
            # 前端字段
            'schedule_type', 'daily_time', 'weekday', 'day_of_month',
            'interval_value', 'interval_unit'
        ]

    def update(self, instance, validated_data):
        # 提取前端字段
        schedule_type = validated_data.pop('schedule_type', '')
        daily_time = validated_data.pop('daily_time', '09:00')
        weekday = validated_data.pop('weekday', 0)
        day_of_month = validated_data.pop('day_of_month', 1)
        interval_value = validated_data.pop('interval_value', 1)
        interval_unit = validated_data.pop('interval_unit', 'hours')

        # 转换调度配置
        cron = build_cron_from_schedule(schedule_type, daily_time, weekday, day_of_month, interval_value, interval_unit)
        if isinstance(cron, str):
            validated_data['cron_expression'] = cron
        elif isinstance(cron, tuple) and cron[1]:
            validated_data['interval_seconds'] = cron[1]

        return super().update(instance, validated_data)


class TaskInstanceSerializer(serializers.ModelSerializer):
    """任务实例序列化器"""

    class Meta:
        model = TaskInstance
        fields = [
            'id', 'plan_execution', 'plan_task', 'status',
            'start_time', 'end_time', 'duration_ms',
            'result_data', 'error_message', 'created_at'
        ]


class PlanExecutionSerializer(serializers.ModelSerializer):
    """计划执行记录序列化器"""
    task_instances = TaskInstanceSerializer(many=True, read_only=True)

    class Meta:
        model = PlanExecution
        fields = [
            'id', 'plan', 'status', 'trigger',
            'total_tasks', 'completed_tasks', 'success_tasks', 'failed_tasks',
            'start_time', 'end_time', 'duration_ms',
            'result_data', 'error_message', 'created_at',
            'task_instances'
        ]


class PlanExecutionListSerializer(serializers.ModelSerializer):
    """计划执行记录列表序列化器(不含实例详情)"""
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = PlanExecution
        fields = [
            'id', 'plan', 'plan_name', 'status', 'trigger',
            'total_tasks', 'completed_tasks', 'success_tasks', 'failed_tasks',
            'start_time', 'end_time', 'duration_ms',
            'created_at'
        ]


class TaskTemplateSerializer(serializers.ModelSerializer):
    """任务模板序列化器"""

    class Meta:
        model = TaskTemplate
        fields = [
            'id', 'name', 'description', 'category',
            'icon', 'color', 'task_type', 'default_config',
            'usage_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class TaskTemplateCreateSerializer(serializers.ModelSerializer):
    """任务模板创建序列化器"""

    class Meta:
        model = TaskTemplate
        fields = [
            'name', 'description', 'category',
            'icon', 'color', 'task_type', 'default_config'
        ]


class AdhocTaskSerializer(serializers.ModelSerializer):
    """临时任务序列化器"""

    class Meta:
        model = AdhocTask
        fields = [
            'id', 'name', 'task_type', 'task_config', 'status',
            'triggered_by', 'start_time', 'end_time', 'duration_ms',
            'result_data', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'start_time', 'end_time', 'duration_ms', 'result_data', 'error_message', 'created_at']


class AdhocTaskCreateSerializer(serializers.ModelSerializer):
    """临时任务创建序列化器"""

    class Meta:
        model = AdhocTask
        fields = ['id', 'name', 'task_type', 'task_config', 'triggered_by']
        read_only_fields = ['id']
