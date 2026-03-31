# 自然语言运维助手 - 功能规划

## SQLBot 核心架构学习

SQLBot 的 Text-to-SQL 实现流程：

```
用户提问 → 选择数据源(LLM) → 生成SQL(LLM) → 执行SQL → 生成图表(LLM) → 返回结果
```

### 关键组件

1. **LLM 工厂** (`model_factory.py`)
   - 基于 LangChain，支持 OpenAI/vLLM/Azure/通义
   - 统一接口 `BaseChatModel`
   - 可扩展注册新模型类型

2. **Prompt 模板** 
   - 系统提示词包含：数据库表结构(schema)、字段说明、术语表
   - 通过 Embedding 做语义搜索，找到相关的表和字段
   - 支持自定义 Prompt 和术语表

3. **数据训练** (`data_training`)
   - 用户可以上传文档/SQL示例来训练模型
   - 类似 RAG（检索增强生成）

4. **术语表** (`terminology`)
   - 定义业务术语和 SQL 的映射
   - 例如 "活跃用户" → "status = 'active' AND last_login > DATE_SUB(NOW(), INTERVAL 7 DAY)"

5. **权限过滤**
   - 生成 SQL 后自动添加行级权限过滤
   - 不同用户看到不同数据

### 我们需要的改造

SQLBot 面向数据分析场景（问数据、画图表）。
我们的运维平台需要的是 **运维排错 + 巡检自动化**，场景不同但技术栈可以复用。

---

## 自然语言运维助手规划

### 目标

用户输入自然语言问题，系统：
1. 理解意图（巡检、排错、查询、操作）
2. 生成对应的 SQL / 命令
3. 执行并返回结果
4. 给出分析建议

### 示例对话

```
用户: "帮我查一下172.26.11.50的MSSQL数据库最近7天的备份情况"
系统: [执行SQL查询备份记录]
      "最近7天备份情况：
       - goods 库：2025-05-05 全量备份 2.89MB
       - byproj 库：2025-03-31 全量备份 5.46MB
       ⚠️ 提示：bysoft, envmot 等8个库最近7天无备份记录，建议尽快安排备份"

用户: "这个数据库连接数是不是太多了？"
系统: [查询连接数]
      "当前活跃连接数 3，最大连接数 32767，使用率 0.01%，非常健康"

用户: "看看哪些表空间快满了"
系统: [查询表空间使用率]
      "表空间使用情况：...（列出所有表空间及使用率）"
```

### 技术方案

#### 阶段一：MVP（最小可用）

**1. 运维知识库**
- 收集常见运维场景的 SQL 模板
- 定义运维术语映射
- 存储在数据库中，供 LLM 参考

```
运维术语示例：
- "数据库连接" → SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1
- "备份情况" → SELECT database_name, MAX(backup_start_date)... FROM msdb.dbo.backupset
- "表空间" → SELECT DB_NAME(database_id)... FROM sys.master_files
- "慢查询" → SELECT TOP 10... FROM sys.dm_exec_query_stats
```

**2. Prompt 模板**
```
你是一个专业的数据库运维助手。你的任务是根据用户的问题，生成对应的SQL查询语句。

可用数据库类型：MySQL、MSSQL、Oracle

当前连接信息：
- 数据库类型：{db_type}
- 数据库版本：{version}
- 数据库列表：{databases}

可用的运维SQL模板：
{sql_templates}

数据库表结构：
{schema}

用户问题：{question}

请生成SQL查询语句，要求：
1. 只生成 SELECT 查询，不执行任何修改操作
2. 输出格式：```sql\n{SQL}\n```
3. 如果需要多个查询，用分号分隔
4. 查询结果要简洁有用，适合运维人员快速理解
```

**3. LLM 集成**
- 复用 SQLBot 的 LLM 工厂
- 支持 OpenAI 兼容 API（DeepSeek、通义、本地模型）
- 配置在系统设置中

**4. 执行流程**
```
用户输入 → LLM生成SQL → 安全检查(只允许SELECT) → 执行SQL → 格式化结果 → LLM总结分析 → 返回
```

#### 阶段二：增强功能

**5. 多轮对话**
- 保持上下文，支持追问
- "刚才那个慢查询的SQL能看一下完整的吗？"

**6. 自动巡检报告**
- "帮我生成本周的数据库巡检报告"
- 自动执行一系列检查，生成格式化报告

**7. 告警分析**
- "最近有哪些告警？帮我分析一下原因"
- 结合告警数据 + 巡检数据做分析

**8. 运维知识库训练**
- 用户可以上传运维文档/手册
- 通过 Embedding 做语义检索
- 类似 SQLBot 的 data_training

#### 阶段三：高级功能

**9. 自动修复建议**
- 不仅发现问题，还给出修复方案
- "磁盘空间不足，建议清理以下日志文件..."

**10. 预测性维护**
- 基于历史数据预测
- "按当前增长趋势，表空间将在7天后用完"

**11. 跨库关联分析**
- 同时查询多个数据库
- "对比一下这几个库的性能指标"

---

## 实现步骤

### 第一步：创建运维术语和SQL模板表

```python
class OpsTerm(models.Model):
    """运维术语"""
    term = models.CharField(max_length=100)  # 术语名称
    db_type = models.CharField(max_length=20)  # 数据库类型
    description = models.TextField()  # 术语说明
    sql_template = models.TextField()  # SQL模板
    category = models.CharField(max_length=50)  # 分类

class OpsKnowledge(models.Model):
    """运维知识库"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=50)
    db_type = models.CharField(max_length=20)
    embedding = models.JSONField(null=True)  # 向量嵌入
```

### 第二步：创建自然语言查询API

```python
class NLQueryViewSet(viewsets.ViewSet):
    """自然语言查询"""
    
    @action(detail=False, methods=['post'])
    def ask(self, request):
        question = request.data.get('question')
        asset_id = request.data.get('asset_id')
        
        # 1. 获取资产连接信息
        # 2. 加载运维术语和SQL模板
        # 3. 调用LLM生成SQL
        # 4. 安全检查（只允许SELECT）
        # 5. 执行SQL
        # 6. 调用LLM分析结果
        # 7. 返回
        
        return Response(result)
```

### 第三步：前端对话界面

- 类似 ChatGPT 的对话框
- 支持代码高亮（SQL）
- 支持表格展示查询结果
- 支持追问

---

## 依赖

- LLM API（DeepSeek / 通义千问 / 本地模型）
- LangChain（可选，也可以直接用 HTTP 调用）
- 向量数据库（可选，用于知识库检索）

## 优先级

1. **P0**：运维术语SQL模板 + LLM生成SQL + 执行查询
2. **P1**：多轮对话 + 自动巡检报告
3. **P2**：知识库训练 + 告警分析
4. **P3**：自动修复建议 + 预测性维护
