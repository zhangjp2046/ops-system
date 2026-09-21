"""
技能基类定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: int = 0

    @classmethod
    def ok(cls, data: Dict[str, Any] = None, duration_ms: int = 0) -> 'SkillResult':
        return cls(success=True, data=data or {}, duration_ms=duration_ms)

    @classmethod
    def fail(cls, error: str, data: Dict[str, Any] = None) -> 'SkillResult':
        return cls(success=False, error=error, data=data or {})


class Skill(ABC):
    """技能基类，所有技能必须继承此类并实现 execute 方法"""

    # 技能唯一标识（与 PlanTask.task_type 一一对应）
    code: str = "unknown"

    # 技能显示名称
    name: str = "未知技能"

    # 技能描述
    description: str = ""

    # 参数 Schema (JSON Schema for validation/documentation)
    param_schema: Dict[str, Any] = field(default_factory=dict)

    # 是否默认启用
    is_enabled: bool = True

    @abstractmethod
    def execute(self, config: dict, context: dict) -> SkillResult:
        """
        执行技能

        Args:
            config: 任务配置，来自 PlanTask.task_config
            context: 执行上下文，包含:
                - plan_id: 调度计划ID
                - execution_id: 执行记录ID
                - task_instance_id: 任务实例ID
                - customer_id: 客户ID（如果有）
                - triggered_by: 触发方式 (manual/schedule/api)

        Returns:
            SkillResult: 执行结果
        """
        raise NotImplementedError

    def validate_config(self, config: dict) -> Optional[str]:
        """
        验证配置是否合法，返回错误信息，无误返回 None
        """
        return None
