"""
技能注册表
所有技能通过 @register 装饰器自动注册
"""
from typing import Dict, List, Type, Optional

from .base import Skill, SkillResult


class SkillRegistry:
    """技能注册表，管理所有技能的注册和获取"""

    _skills: Dict[str, Type[Skill]] = {}

    @classmethod
    def register(cls, skill_class: Type[Skill]) -> Type[Skill]:
        """
        注册技能，使用类属性 code 作为标识
        用法:
            @SkillRegistry.register
            class MySkill(Skill):
                code = "my_skill"
        """
        if not hasattr(skill_class, 'code') or not skill_class.code:
            raise ValueError(f"技能类 {skill_class.__name__} 必须定义 code 属性")
        if skill_class.code in cls._skills:
            raise ValueError(f"技能 code '{skill_class.code}' 已被注册")
        cls._skills[skill_class.code] = skill_class
        return skill_class

    @classmethod
    def get(cls, task_type: str) -> Optional[Type[Skill]]:
        """根据 task_type 获取技能类"""
        return cls._skills.get(task_type)

    @classmethod
    def get_instance(cls, task_type: str) -> Skill:
        """获取技能实例，不存在则抛出 ValueError"""
        skill_class = cls.get(task_type)
        if skill_class is None:
            raise ValueError(f"未知技能类型: {task_type}，可用: {cls.list_codes()}")
        return skill_class()

    @classmethod
    def list_codes(cls) -> List[str]:
        """列出所有已注册技能的 code"""
        return list(cls._skills.keys())

    @classmethod
    def list_skills(cls) -> Dict[str, Type[Skill]]:
        """返回所有已注册技能的字典"""
        return dict(cls._skills)

    @classmethod
    def unregister(cls, task_type: str) -> bool:
        """取消注册某个技能"""
        if task_type in cls._skills:
            del cls._skills[task_type]
            return True
        return False


def register_skill(code: str):
    """
    装饰器形式的注册函数
    用法:
        @register_skill("my_skill")
        class MySkill(Skill):
            ...
    """
    def decorator(cls: Type[Skill]) -> Type[Skill]:
        cls.code = code
        return SkillRegistry.register(cls)
    return decorator
