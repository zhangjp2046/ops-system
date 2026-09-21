# 技能库框架设计

## 核心理念

- **调度器** = 只负责"什么时候触发"，调用技能，不关心技能内部实现
- **技能库** = 各种技能的定义和实现，技能自包含，调度器透明调用

## 整体架构

```
scheduler_v2 (调度器)
    │
    └── TaskExecutor._do_task(task_type, config, timeout)
            │
            └── SkillRegistry.get_instance(task_type).execute(config, context)
                    │
                    └── InspectionSkill / AlertPushSkill / ...

skills/ (技能库)
    ├── base.py       - Skill 基类、SkillResult 定义
    ├── registry.py   - 技能注册表（task_type → Skill 类映射）
    ├── inspection.py - 巡检技能
    ├── push.py        - 推送类技能（告警/巡检结果/状态）
    └── ops.py         - 运维类技能（状态刷新/发现扫描/清理/报表）
```

## 技能接口

```python
class Skill(ABC):
    code: str           # 技能标识（与 task_type 对应）
    name: str            # 显示名称
    description: str     # 描述
    param_schema: dict  # 参数 Schema

    def execute(self, config: dict, context: dict) -> SkillResult:
        """执行技能"""
        raise NotImplementedError

    def validate_config(self, config: dict) -> Optional[str]:
        """验证配置，返回错误信息或 None"""
        return None
```

### SkillResult

```python
@dataclass
class SkillResult:
    success: bool
    data: dict = field(default_factory=dict)
    error: str = ""
    duration_ms: int = 0
```

## 已实现技能

| code | 类名 | 描述 | 参数 |
|------|------|------|------|
| `inspection` | InspectionSkill | 巡检技能 | `inspection_plan_id` / `asset_id` / `customer_id` |
| `push_alert` | AlertPushSkill | 告警推送 | `alert_ids` / `customer_id` |
| `push_inspection` | InspectionResultPushSkill | 巡检结果推送 | `customer_id`, `limit` |
| `push_status` | StatusPushSkill | 状态推送 | `customer_id`, `limit` |
| `status_refresh` | StatusRefreshSkill | 状态刷新 | `customer_id` |
| `discovery_scan` | DiscoveryScanSkill | 发现扫描 | `subnets`, `scan_type` |
| `cleanup` | CleanupSkill | 数据清理 | `retention_days` |
| `report` | ReportSkill | 生成报表 | `report_type`, `customer_id` |

## 技能注册机制

```python
@SkillRegistry.register
class MySkill(Skill):
    code = "my_skill"
    name = "我的技能"
    ...
```

或

```python
@register_skill("my_skill")
class MySkill(Skill):
    ...
```

## 分步实施状态

### ✅ Phase 1: 基础框架 (完成)
- ✅ `apps/skills/` 目录创建
- ✅ `Skill`, `SkillResult`, `SkillRegistry` 定义
- ✅ 技能注册装饰器 `@SkillRegistry.register`

### ✅ Phase 2: 技能迁移 (完成)
- ✅ InspectionSkill (从 executor._do_inspection 迁移)
- ✅ AlertPushSkill / InspectionResultPushSkill / StatusPushSkill
- ✅ StatusRefreshSkill / DiscoveryScanSkill / CleanupSkill / ReportSkill

### ✅ Phase 3: 调度器改造 (完成)
- ✅ `TaskExecutor._do_task` 优先调用 `SkillRegistry`
- ✅ 回退机制：技能库不可用时回退到内置实现
- ⚠️ **注意**：目前 context 传空 `{}`，后续可扩展

### ⏳ Phase 4: 技能库管理界面 (待实施)
- 后台管理技能的启用/禁用
- 参数配置界面
- 执行历史查看

## 使用示例

```python
# 调度器调用（已实现，自动路由）
TaskExecutor._do_task('inspection', {'inspection_plan_id': 8}, timeout=300)

# 直接调用技能
from apps.skills import SkillRegistry

skill = SkillRegistry.get_instance('report')
result = skill.execute({'report_type': 'summary'}, {})
print(result.success, result.data)
```

## API 接口

```
GET  /api/skills/           - 列出所有技能
POST /api/skills/execute/   - 执行指定技能
GET  /api/skills/<code>/   - 获取技能详情
```
