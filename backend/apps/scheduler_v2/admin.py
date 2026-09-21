from django.contrib import admin
from .models import Plan, PlanTask, PlanExecution, TaskInstance, TaskTemplate, AdhocTask


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'status', 'is_enabled', 'cron_expression', 'next_run_time', 'last_run_time']
    list_filter = ['plan_type', 'status', 'is_enabled']
    search_fields = ['name', 'description']
    ordering = ['-created_at']


@admin.register(PlanTask)
class PlanTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan', 'task_type', 'is_enabled', 'execution_order']
    list_filter = ['task_type', 'is_enabled']
    search_fields = ['name', 'description']


@admin.register(PlanExecution)
class PlanExecutionAdmin(admin.ModelAdmin):
    list_display = ['plan', 'status', 'trigger', 'start_time', 'end_time']
    list_filter = ['status', 'trigger']
    ordering = ['-created_at']


@admin.register(TaskInstance)
class TaskInstanceAdmin(admin.ModelAdmin):
    list_display = ['plan_task', 'status', 'start_time', 'end_time']
    list_filter = ['status']


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'task_type', 'usage_count']
    list_filter = ['category']


@admin.register(AdhocTask)
class AdhocTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'task_type', 'status', 'triggered_by', 'created_at']
    list_filter = ['status', 'task_type']
    ordering = ['-created_at']
