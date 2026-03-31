# 通用运维系统数据库设计（灵活版）

## 1. 设计原则

### 1.1 灵活性
- 支持不同客户的资产结构
- 支持自定义字段
- 支持插件扩展

### 1.2 性能
- 合理索引设计
- 分区表支持
- 读写分离支持

### 1.3 可维护性
- 清晰的表关系
- 完整的外键约束
- 审计日志记录

## 2. 数据库表设计

### 2.1 核心表

#### 2.1.1 customers - 客户信息
```sql
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_code VARCHAR(50) UNIQUE NOT NULL COMMENT '客户编码',
    customer_name VARCHAR(100) NOT NULL COMMENT '客户名称',
    customer_type VARCHAR(50) COMMENT '客户类型',
    industry VARCHAR(50) COMMENT '行业',
    
    -- 联系信息
    contact_person VARCHAR(50) COMMENT '联系人',
    contact_phone VARCHAR(20) COMMENT '联系电话',
    contact_email VARCHAR(100) COMMENT '联系邮箱',
    address TEXT COMMENT '地址',
    
    -- 配置信息
    config JSON COMMENT '客户配置',
    plugins JSON COMMENT '启用的插件',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态',
    contract_start DATE COMMENT '合同开始',
    contract_end DATE COMMENT '合同结束',
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT COMMENT '创建人',
    updated_by INT COMMENT '更新人'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.2 asset_types - 资产类型定义
```sql
CREATE TABLE asset_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL COMMENT '客户ID',
    type_code VARCHAR(50) NOT NULL COMMENT '类型代码',
    type_name VARCHAR(100) NOT NULL COMMENT '类型名称',
    parent_type_id INT DEFAULT 0 COMMENT '父类型ID',
    plugin_id VARCHAR(100) COMMENT '插件ID',
    
    -- 配置信息
    icon VARCHAR(50) COMMENT '图标',
    color VARCHAR(20) COMMENT '颜色',
    description TEXT COMMENT '描述',
    
    -- 显示配置
    sort_order INT DEFAULT 0 COMMENT '排序',
    is_system BOOLEAN DEFAULT FALSE COMMENT '是否系统类型',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    
    -- 约束
    UNIQUE KEY uk_customer_type (customer_id, type_code),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.3 asset_fields - 资产字段定义
```sql
CREATE TABLE asset_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_type_id INT NOT NULL COMMENT '资产类型ID',
    field_code VARCHAR(50) NOT NULL COMMENT '字段代码',
    field_name VARCHAR(100) NOT NULL COMMENT '字段名称',
    field_type VARCHAR(20) NOT NULL COMMENT '字段类型',
    
    -- 字段配置
    is_required BOOLEAN DEFAULT FALSE COMMENT '是否必填',
    is_unique BOOLEAN DEFAULT FALSE COMMENT '是否唯一',
    is_searchable BOOLEAN DEFAULT TRUE COMMENT '是否可搜索',
    is_filterable BOOLEAN DEFAULT TRUE COMMENT '是否可过滤',
    
    -- 显示配置
    field_label VARCHAR(100) NOT NULL COMMENT '显示标签',
    placeholder VARCHAR(200) COMMENT '占位符',
    help_text TEXT COMMENT '帮助文本',
    sort_order INT DEFAULT 0 COMMENT '排序',
    
    -- 验证配置
    validation_rules JSON COMMENT '验证规则',
    default_value TEXT COMMENT '默认值',
    options JSON COMMENT '选项列表',
    
    -- 约束
    UNIQUE KEY uk_type_field (asset_type_id, field_code),
    
    FOREIGN KEY (asset_type_id) REFERENCES asset_types(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.4 assets - 资产主表
```sql
CREATE TABLE assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL COMMENT '客户ID',
    asset_type_id INT NOT NULL COMMENT '资产类型ID',
    
    -- 基本信息
    asset_code VARCHAR(100) NOT NULL COMMENT '资产编号',
    asset_name VARCHAR(200) NOT NULL COMMENT '资产名称',
    description TEXT COMMENT '描述',
    
    -- 位置信息
    location VARCHAR(200) COMMENT '位置',
    room VARCHAR(100) COMMENT '机房',
    rack VARCHAR(100) COMMENT '机柜',
    position VARCHAR(50) COMMENT '位置',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态',
    importance_level VARCHAR(20) DEFAULT 'MEDIUM' COMMENT '重要等级',
    
    -- 时间信息
    purchase_date DATE COMMENT '购买日期',
    warranty_end DATE COMMENT '保修到期',
    decommission_date DATE COMMENT '退役日期',
    
    -- 责任人
    owner VARCHAR(100) COMMENT '负责人',
    department VARCHAR(100) COMMENT '部门',
    vendor VARCHAR(100) COMMENT '供应商',
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT COMMENT '创建人',
    updated_by INT COMMENT '更新人',
    
    -- 约束
    UNIQUE KEY uk_customer_asset (customer_id, asset_code),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_type_id) REFERENCES asset_types(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.1.5 asset_data - 资产数据表（动态字段）
```sql
CREATE TABLE asset_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL COMMENT '资产ID',
    field_id INT NOT NULL COMMENT '字段ID',
    
    -- 数据值
    string_value TEXT COMMENT '字符串值',
    number_value DECIMAL(20,6) COMMENT '数字值',
    boolean_value BOOLEAN COMMENT '布尔值',
    date_value DATE COMMENT '日期值',
    datetime_value TIMESTAMP COMMENT '日期时间值',
    json_value JSON COMMENT 'JSON值',
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE KEY uk_asset_field (asset_id, field_id),
    
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (field_id) REFERENCES asset_fields(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.2 监控相关表

#### 2.2.1 monitoring_tasks - 监控任务
```sql
CREATE TABLE monitoring_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL COMMENT '客户ID',
    task_name VARCHAR(100) NOT NULL COMMENT '任务名称',
    task_type VARCHAR(50) NOT NULL COMMENT '任务类型',
    
    -- 目标配置
    target_type VARCHAR(50) COMMENT '目标类型',
    target_ids JSON COMMENT '目标ID列表',
    target_filter JSON COMMENT '目标过滤条件',
    
    -- 执行配置
    plugin_id VARCHAR(100) NOT NULL COMMENT '插件ID',
    config JSON NOT NULL COMMENT '任务配置',
    schedule VARCHAR(100) NOT NULL COMMENT '执行计划',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态',
    last_run_time TIMESTAMP COMMENT '最后执行时间',
    next_run_time TIMESTAMP COMMENT '下次执行时间',
    
    -- 性能配置
    timeout_seconds INT DEFAULT 300 COMMENT '超时时间',
    retry_count INT DEFAULT 3 COMMENT '重试次数',
    priority INT DEFAULT 5 COMMENT '优先级',
    
    -- 通知配置
    alert_enabled BOOLEAN DEFAULT TRUE COMMENT '启用告警',
    alert_rules JSON COMMENT '告警规则',
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.2.2 monitoring_results - 监控结果
```sql
CREATE TABLE monitoring_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL COMMENT '任务ID',
    asset_id INT NOT NULL COMMENT '资产ID',
    
    -- 执行信息
    execution_time TIMESTAMP NOT NULL COMMENT '执行时间',
    duration_ms INT COMMENT '执行时长',
    status VARCHAR(20) NOT NULL COMMENT '执行状态',
    
    -- 结果数据
    metrics JSON COMMENT '指标数据',
    raw_data TEXT COMMENT '原始数据',
    error_message TEXT COMMENT '错误信息',
    
    -- 评分
    score INT COMMENT '评分(0-100)',
    health_status VARCHAR(20) COMMENT '健康状态',
    
    -- 索引
    INDEX idx_task_time (task_id, execution_time),
    INDEX idx_asset_time (asset_id, execution_time),
    
    FOREIGN KEY (task_id) REFERENCES monitoring_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.3 告警相关表

#### 2.3.1 alert_rules - 告警规则
```sql
CREATE TABLE alert_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL COMMENT '客户ID',
    rule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
    
    -- 条件配置
    condition_type VARCHAR(50) NOT NULL COMMENT '条件类型',
    condition_config JSON NOT NULL COMMENT '条件配置',
    
    -- 目标配置
    target_type VARCHAR(50) COMMENT '目标类型',
    target_ids JSON COMMENT '目标ID列表',
    
    -- 告警配置
    severity VARCHAR(20) DEFAULT 'MEDIUM' COMMENT '严重程度',
    alert_message TEXT NOT NULL COMMENT '告警消息',
    recovery_message TEXT COMMENT '恢复消息',
    
    -- 抑制配置
    suppression_enabled BOOLEAN DEFAULT TRUE COMMENT '启用抑制',
    suppression_duration INT DEFAULT 300 COMMENT '抑制时长(秒)',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态',
    last_trigger_time TIMESTAMP COMMENT '最后触发时间',
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.3.2 alerts - 告警记录
```sql
CREATE TABLE alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL COMMENT '客户ID',
    rule_id INT COMMENT '规则ID',
    
    -- 告警信息
    alert_type VARCHAR(50) NOT NULL COMMENT '告警类型',
    severity VARCHAR(20) NOT NULL COMMENT '严重程度',
    title VARCHAR(200) NOT NULL COMMENT '标题',
    message TEXT NOT NULL COMMENT '消息',
    
    -- 目标信息
    asset_id INT COMMENT '资产ID',
    asset_name VARCHAR(200) COMMENT '资产名称',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'OPEN' COMMENT '状态',
    acknowledged BOOLEAN DEFAULT FALSE COMMENT '是否确认',
    acknowledged_by INT COMMENT '确认人',
    acknowledged_at TIMESTAMP COMMENT '确认时间',
    
    -- 时间信息
    triggered_at TIMESTAMP NOT NULL COMMENT '触发时间',
    resolved_at TIMESTAMP COMMENT '解决时间',
    duration_seconds INT COMMENT '持续时间',
    
    -- 数据信息
    trigger_data JSON COMMENT '触发数据',
    resolution_notes TEXT COMMENT '解决说明',
    
    -- 索引
    INDEX idx_customer_status (customer_id, status),
    INDEX idx_triggered_time (triggered_at),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id) ON DELETE SET NULL,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.4 系统管理表

#### 2.4.1 users - 用户表
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    
    -- 个人信息
    full_name VARCHAR(100) COMMENT '姓名',
    phone VARCHAR(20) COMMENT '电话',
    avatar_url VARCHAR(500) COMMENT '头像',
    
    -- 权限信息
    role VARCHAR(50) DEFAULT 'USER' COMMENT '角色',
    permissions JSON COMMENT '权限列表',
    
    -- 状态信息
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    is_superuser BOOLEAN DEFAULT FALSE COMMENT '是否超级用户',
    last_login_time TIMESTAMP COMMENT '最后登录时间',
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.4.2 plugins - 插件表
```sql
CREATE TABLE plugins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plugin_id VARCHAR(100) UNIQUE NOT NULL COMMENT '插件ID',
    plugin_name VARCHAR(100) NOT NULL COMMENT '插件名称',
    plugin_type VARCHAR(50) NOT NULL COMMENT '插件类型',
    
    -- 版本信息
    version VARCHAR(20) NOT NULL COMMENT '版本',
    author VARCHAR(100) COMMENT '作者',
    description TEXT COMMENT '描述',
    
    -- 配置信息
    config_schema JSON COMMENT '配置schema',
    assets_schema JSON COMMENT '资产schema',
    monitoring_schema JSON COMMENT '监控schema',
    
    -- 文件信息
    entry_point VARCHAR(200) COMMENT '入口文件',
    dependencies JSON COMMENT '依赖',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'INSTALLED' COMMENT '状态',
    is_system BOOLEAN DEFAULT FALSE COMMENT '是否系统插件',
    
    -- 审计信息
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3. 索引设计

### 3.1 核心索引
```sql
-- customers表
CREATE INDEX idx_customer_code ON customers(customer_code);
CREATE INDEX idx_customer_status ON customers(status);

-- assets表
CREATE INDEX idx_asset_code ON assets(asset_code);
CREATE INDEX idx_asset_status ON assets(status);
CREATE INDEX idx_asset_type ON assets(asset_type_id);
CREATE INDEX idx_asset_customer ON assets(customer_id);

-- asset_data表
CREATE INDEX idx_data_asset ON asset_data(asset_id);
CREATE INDEX idx_data_field ON asset_data(field_id);

-- monitoring_results表
CREATE INDEX idx_result_task_time ON monitoring_results(task_id, execution_time);
CREATE INDEX idx_result_asset_time ON monitoring_results(asset_id, execution_time);

-- alerts表
CREATE INDEX idx_alert_customer_status ON alerts(customer_id, status);
CREATE INDEX idx_alert_triggered ON alerts(triggered_at);
```

## 4. 分区策略

### 4.1 按时间分区
```sql
-- monitoring_results表按月分区
ALTER TABLE monitoring_results
PARTITION BY RANGE (UNIX_TIMESTAMP(execution_time)) (
    PARTITION p202601 VALUES LESS THAN (UNIX_TIMESTAMP('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (UNIX_TIMESTAMP('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (UNIX_TIMESTAMP('2026-04-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- alerts表按月分区
ALTER TABLE alerts
PARTITION BY RANGE (UNIX_TIMESTAMP(triggered_at)) (
    PARTITION p202601 VALUES LESS THAN (UNIX_TIMESTAMP('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (UNIX_TIMESTAMP('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (UNIX_TIMESTAMP('2026-04-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

## 5. 初始化数据

### 5.1 系统用户
```sql
INSERT INTO users (username, email, password_hash, full_name, role, is_superuser) VALUES
('admin', 'admin@ops-system.com', '$2y$10$dummyhash', '系统管理员', 'ADMIN', TRUE),
('operator', 'operator@ops-system.com', '$2y$10$dummyhash', '运维操作员', 'OPERATOR', FALSE);
```

### 5.2 系统插件
```sql
INSERT INTO plugins (plugin_id, plugin_name, plugin_type, version, is_system, description) VALUES
('core.assets', '核心资产插件', 'asset', '1.0.0', TRUE, '核心资产管理系统'),
('core.monitoring', '核心监控插件', 'monitoring', '1.0.0', TRUE, '核心监控系统'),
('core.alerts', '核心告警插件', 'alert', '1.0.0', TRUE, '核心告警系统'),
('hospital.assets', '医院资产插件', 'asset', '1.0.0', FALSE, '医院资产管理系统');
```

## 6. 数据库创建脚本

创建完整的数据库创建脚本，包含所有表、索引、分区和初始化数据。