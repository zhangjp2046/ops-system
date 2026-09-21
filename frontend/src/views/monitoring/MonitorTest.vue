<template>
  <div class="monitor-test">
    <div class="page-header">
      <h2>采集测试</h2>
      <div>
        <el-button @click="loadHistory">
          <el-icon><Clock /></el-icon> 历史记录
        </el-button>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon> 新建配置
        </el-button>
      </div>
    </div>

    <!-- 快速测试 -->
    <el-card class="quick-test-card">
      <template #header>
        <div class="card-header">
          <span>⚡ 快速测试</span>
          <span class="hint">选择协议 → 填写参数 → 点击测试 → 查看结果</span>
        </div>
      </template>

      <el-form :model="quickForm" label-width="80px">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="协议">
              <el-select v-model="quickForm.protocol" @change="onProtocolChange" style="width:100%">
                <el-option-group label="网络">
                  <el-option label="Ping (ICMP)" value="ping" />
                  <el-option label="端口检测" value="port" />
                  <el-option label="SNMP" value="snmp" />
                </el-option-group>
                <el-option-group label="服务器">
                  <el-option label="SSH" value="ssh" />
                </el-option-group>
                <el-option-group label="数据库">
                  <el-option label="MySQL" value="mysql" />
                  <el-option label="MSSQL" value="mssql" />
                  <el-option label="Oracle" value="oracle" />
                  <el-option label="PostgreSQL" value="postgresql" />
                </el-option-group>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="主机">
              <el-input v-model="quickForm.host" placeholder="IP 或主机名" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="端口">
              <el-input v-model="quickForm.port" :placeholder="defaultPort" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="超时(s)">
              <el-input-number v-model="quickForm.timeout" :min="3" :max="60" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label=" ">
              <el-button type="primary" @click="runQuickTest" :loading="testing" style="width:100%">
                <el-icon><VideoPlay /></el-icon> 开始测试
              </el-button>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 协议特定字段 -->
        <el-row :gutter="16" v-if="showAuthFields">
          <el-col :span="6">
            <el-form-item label="用户名">
              <el-input v-model="quickForm.username" placeholder="用户名" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="密码">
              <el-input v-model="quickForm.password" type="password" show-password placeholder="密码" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="showDbField">
            <el-form-item label="数据库">
              <el-input v-model="quickForm.database" :placeholder="dbPlaceholder" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="quickForm.protocol === 'snmp'">
            <el-form-item label="Community">
              <el-input v-model="quickForm.community" placeholder="public" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="quickForm.protocol === 'snmp'">
            <el-form-item label="SNMP版本">
              <el-select v-model="quickForm.snmpVersion" style="width:100%">
                <el-option label="v2c（推荐）" value="v2c" />
                <el-option label="v1" value="v1" />
                <el-option label="v3" value="v3" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="quickForm.protocol === 'snmp'">
            <el-form-item label="自定义OID">
              <el-input v-model="quickForm.customOid" placeholder="可选，如 1.3.6.1.2.1.1.5.0" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 测试结果 -->
    <el-card v-if="testResult" class="result-card" :class="testResult.success ? 'success' : 'error'">
      <template #header>
        <div class="card-header">
          <span>
            {{ testResult.success ? '✅ 测试成功' : '❌ 测试失败' }}
            <el-tag :type="testResult.success ? 'success' : 'danger'" size="small" style="margin-left:8px">
              {{ testResult.test_duration }}ms
            </el-tag>
          </span>
          <el-button link type="primary" @click="copyResult">复制结果</el-button>
          <el-button link type="success" @click="sendResult" :loading="sending">发送</el-button>
        </div>
      </template>

      <!-- 基本信息 -->
      <el-descriptions :column="3" border size="small" class="result-info">
        <el-descriptions-item label="协议">{{ testResult.protocol }}</el-descriptions-item>
        <el-descriptions-item label="主机">{{ testResult.host }}</el-descriptions-item>
        <el-descriptions-item label="端口">{{ testResult.port || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态" :span="3">
          <el-tag :type="testResult.success ? 'success' : 'danger'">
            {{ testResult.success ? '连接成功' : '连接失败' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 数据库测试结果 — MySQL 全面展示 -->
      <template v-if="testResult.protocol === 'mysql' && testResult.success">
        <el-divider content-position="left">🐬 MySQL 数据库信息</el-divider>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="版本" :span="3">{{ testResult.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主机名">{{ testResult.db_info?.hostname || '-' }}</el-descriptions-item>
          <el-descriptions-item label="版本注释">{{ testResult.db_info?.version_comment || '-' }}</el-descriptions-item>
          <el-descriptions-item label="数据库数量">
            <el-tag type="primary" size="small">{{ testResult.db_info?.db_count || 0 }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据目录">{{ testResult.db_info?.datadir || '-' }}</el-descriptions-item>
          <el-descriptions-item label="字符集">{{ testResult.db_info?.character_set || '-' }}</el-descriptions-item>
          <el-descriptions-item label="排序规则">{{ testResult.db_info?.collation || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最大连接数">{{ testResult.db_info?.max_connections || '-' }}</el-descriptions-item>
          <el-descriptions-item label="当前连接数">{{ testResult.db_info?.current_connections || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行时间">{{ formatUptime(testResult.status?.Uptime) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="二进制日志">{{ testResult.db_info?.log_bin || 'OFF' }}</el-descriptions-item>
          <el-descriptions-item label="SSL">{{ testResult.variables?.have_ssl || 'OFF' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 运行状态 -->
        <template v-if="testResult.status && Object.keys(testResult.status).length">
          <el-divider content-position="left">📊 运行状态</el-divider>
          <el-table :data="mysqlStatusData" size="small" stripe>
            <el-table-column prop="name" label="指标" width="180" />
            <el-table-column prop="value" label="值" min-width="200" />
          </el-table>
        </template>

        <!-- 关键变量 -->
        <template v-if="testResult.variables && Object.keys(testResult.variables).length">
          <el-divider content-position="left">⚙️ 关键系统变量</el-divider>
          <el-table :data="mysqlVariableData" size="small" stripe>
            <el-table-column prop="name" label="变量名" width="250" />
            <el-table-column prop="value" label="值" min-width="200" />
          </el-table>
        </template>

        <!-- 数据库列表 -->
        <template v-if="testResult.databases?.length">
          <el-divider content-position="left">📁 数据库列表 ({{ testResult.databases.length }}个)</el-divider>
          <div class="tag-list">
            <el-tag v-for="db in testResult.databases" :key="db" size="small" style="margin:2px">
              {{ db }}
            </el-tag>
          </div>
        </template>

        <!-- 存储引擎 -->
        <template v-if="testResult.engines?.length">
          <el-divider content-position="left">🔧 存储引擎</el-divider>
          <el-table :data="testResult.engines" size="small" stripe>
            <el-table-column prop="engine" label="引擎" width="150" />
            <el-table-column prop="support" label="支持" width="100">
              <template #default="{ row }">
                <el-tag :type="row.support === 'DEFAULT' ? 'success' : 'info'" size="small">
                  {{ row.support }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="comment" label="说明" min-width="250" />
          </el-table>
        </template>
      </template>

      <!-- 数据库测试结果 — MSSQL 全面展示 -->
      <template v-if="testResult.protocol === 'mssql' && testResult.success">
        <el-divider content-position="left">🗄️ MSSQL 数据库信息</el-divider>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="版本" :span="3">{{ testResult.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="数据库数量">
            <el-tag type="primary" size="small">{{ testResult.db_info?.db_count || 0 }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前连接">{{ testResult.db_info?.user_connections || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最大连接(限制)">{{ testResult.db_info?.user_connections_limit || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最大内存(MB)">{{ testResult.db_info?.max_memory_mb || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最大并行度">{{ testResult.db_info?.max_dop || '-' }}</el-descriptions-item>
          <el-descriptions-item label="页面预期寿命(PLE)">{{ testResult.db_info?.page_life_expectancy || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行中会话">{{ testResult.db_info?.running_sessions || '-' }}</el-descriptions-item>
          <el-descriptions-item label="阻塞进程">{{ testResult.db_info?.processes_blocked || '0' }}</el-descriptions-item>
          <el-descriptions-item label="总会话数">{{ testResult.db_info?.total_sessions || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 数据库列表 -->
        <template v-if="testResult.databases?.length">
          <el-divider content-position="left">📁 数据库列表 ({{ testResult.databases.length }}个)</el-divider>
          <div class="tag-list">
            <el-tag v-for="db in testResult.databases" :key="db" size="small" style="margin:2px">
              {{ db }}
            </el-tag>
          </div>
        </template>

        <!-- 配置参数 -->
        <template v-if="testResult.config && Object.keys(testResult.config).length">
          <el-divider content-position="left">⚙️ 关键配置参数</el-divider>
          <el-table :data="mssqlConfigData" size="small" stripe>
            <el-table-column prop="name" label="参数名" width="300" />
            <el-table-column prop="value" label="值" min-width="200" />
          </el-table>
        </template>

        <!-- 原始tsql输出 -->
        <template v-if="testResult.raw_output">
          <el-divider content-position="left">📋 原始 tsql 输出</el-divider>
          <el-collapse>
            <el-collapse-item title="查看原始输出">
              <pre class="raw-json">{{ testResult.raw_output }}</pre>
            </el-collapse-item>
          </el-collapse>
        </template>
      </template>

      <!-- 数据库测试结果 — PostgreSQL（通用展示） -->
      <template v-if="testResult.protocol === 'postgresql' && testResult.success">
        <el-divider content-position="left">🐘 PostgreSQL 数据库信息</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="版本" :span="2">{{ testResult.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="响应时间">{{ testResult.response_time || testResult.test_duration || '-' }}ms</el-descriptions-item>
          <el-descriptions-item label="连接方式">{{ testResult.data?.method || testResult.message || '直接连接' }}</el-descriptions-item>
        </el-descriptions>
        <template v-if="testResult.data?.databases?.length">
          <el-divider content-position="left">📁 数据库列表</el-divider>
          <div class="tag-list">
            <el-tag v-for="db in testResult.data.databases" :key="db" size="small" style="margin:2px">{{ db }}</el-tag>
          </div>
        </template>
      </template>

      <!-- 数据库测试结果 — Oracle 全面展示 -->
      <template v-if="testResult.protocol === 'oracle' && testResult.success">
        <el-divider content-position="left">🔴 Oracle 数据库信息</el-divider>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="版本" :span="3">{{ testResult.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="实例名">{{ testResult.db_info?.instance_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主机名">{{ testResult.db_info?.host_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="启动时间">{{ testResult.db_info?.startup_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="testResult.db_info?.status === 'OPEN' ? 'success' : 'warning'" size="small">
              {{ testResult.db_info?.status || '-' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据库状态">{{ testResult.db_info?.database_status || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 性能概览 -->
        <el-divider content-position="left">📊 性能概览</el-divider>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="总会话数">
            <el-tag type="primary" size="small">{{ testResult.status?.total_sessions || 0 }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="活跃会话">
            <el-tag :type="(testResult.status?.active_sessions || 0) > 50 ? 'danger' : 'success'" size="small">
              {{ testResult.status?.active_sessions || 0 }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="缓冲命中率">
            <el-tag :type="(testResult.status?.buffer_hit_ratio || 100) >= 95 ? 'success' : 'warning'" size="small">
              {{ testResult.status?.buffer_hit_ratio || '-' }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="SGA大小">{{ testResult.status?.sga_size_mb || '-' }} MB</el-descriptions-item>
          <el-descriptions-item label="物理读">{{ testResult.status?.physical_reads || 0 }}</el-descriptions-item>
          <el-descriptions-item label="逻辑读">{{ testResult.status?.logical_reads || 0 }}</el-descriptions-item>
        </el-descriptions>

        <!-- 表空间使用率 -->
        <template v-if="getOracleTablespaces.length">
          <el-divider content-position="left">💾 表空间使用率 ({{ getOracleTablespaces.length }}个)</el-divider>
          <el-table :data="getOracleTablespaces" size="small" stripe max-height="400">
            <el-table-column prop="name" label="表空间" min-width="150" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'ONLINE' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="总大小" width="100">
              <template #default="{ row }">{{ formatMB(row.total_mb) }}</template>
            </el-table-column>
            <el-table-column label="已用" width="100">
              <template #default="{ row }">{{ formatMB(row.used_mb) }}</template>
            </el-table-column>
            <el-table-column label="空闲" width="100">
              <template #default="{ row }">{{ formatMB(row.free_mb) }}</template>
            </el-table-column>
            <el-table-column label="使用率" width="150">
              <template #default="{ row }">
                <el-progress v-if="row.used_pct !== 'N/A' && row.used_pct !== undefined" :percentage="parseFloat(row.used_pct) || 0" :stroke-width="16"
                  :status="(parseFloat(row.used_pct) || 0) > 90 ? 'exception' : (parseFloat(row.used_pct) || 0) > 80 ? 'warning' : 'success'" />
                <span v-else class="text-muted">N/A</span>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- 归档日志 -->
        <template v-if="testResult.status?.archive_used_pct !== undefined">
          <el-divider content-position="left">📦 归档日志</el-divider>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="归档使用率">
              <el-progress :percentage="parseFloat(testResult.status.archive_used_pct) || 0" :stroke-width="16"
                :status="(parseFloat(testResult.status.archive_used_pct) || 0) > 85 ? 'exception' : 'success'"
                style="width:200px" />
            </el-descriptions-item>
            <el-descriptions-item label="已用空间">{{ formatMB(testResult.status.archive_used_mb) }}</el-descriptions-item>
            <el-descriptions-item label="总限额">{{ formatMB(testResult.status.archive_limit_mb) }}</el-descriptions-item>
          </el-descriptions>
        </template>
      </template>

      <!-- SNMP测试结果 — 全面展示 -->
      <template v-if="quickForm.protocol === 'snmp' && testResult.success">
        <el-divider content-position="left">🔌 设备信息摘要</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="SNMP版本" :span="1">
            <el-tag type="success" size="small">{{ testResult.snmp_version || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="设备类型" :span="1">
            <el-tag type="primary" size="small">{{ deviceTypeLabel }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="主机名" :span="2">{{ testResult.device_info?.hostname || '-' }}</el-descriptions-item>
          <el-descriptions-item label="位置" :span="2">{{ testResult.device_info?.location || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系人" :span="2">{{ testResult.device_info?.contact || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行时间" :span="2">{{ testResult.device_info?.uptime || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 系统描述 -->
        <el-descriptions :column="1" border size="small" style="margin-top:12px">
          <el-descriptions-item label="系统描述">
            <div class="text-wrap">{{ testResult.sysDescr || testResult.device_info?.os || '-' }}</div>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 接口统计 -->
        <template v-if="testResult.interface_summary?.total">
          <el-divider content-position="left">🌐 网络接口 ({{ testResult.interface_summary.total }}个)</el-divider>
          <el-descriptions :column="4" border size="small">
            <el-descriptions-item label="总数">{{ testResult.interface_summary.total }}</el-descriptions-item>
            <el-descriptions-item label="UP">
              <el-tag type="success" size="small">{{ testResult.interface_summary.up }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="DOWN">
              <el-tag v-if="testResult.interface_summary.down > 0" type="danger" size="small">{{ testResult.interface_summary.down }}</el-tag>
              <span v-else>0</span>
            </el-descriptions-item>
            <el-descriptions-item label="其他">{{ testResult.interface_summary.total - testResult.interface_summary.up - testResult.interface_summary.down }}</el-descriptions-item>
          </el-descriptions>

          <!-- 接口列表 -->
          <el-table :data="testResult.interface_summary.interfaces" size="small" stripe max-height="300" style="margin-top:8px">
            <el-table-column prop="index" label="#" width="50" />
            <el-table-column prop="name" label="接口名" min-width="180" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'up' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="speed_display" label="速率" width="100" />
          </el-table>
        </template>

        <!-- CPU信息 -->
        <template v-if="testResult.cpu">
          <el-divider content-position="left">💻 CPU</el-divider>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="数量">{{ testResult.cpu.count }}</el-descriptions-item>
            <el-descriptions-item label="平均负载">
              <el-tag :type="testResult.cpu.avg_load > 80 ? 'danger' : testResult.cpu.avg_load > 50 ? 'warning' : 'success'" size="small">
                {{ testResult.cpu.avg_load }}%
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </template>

        <!-- 存储信息 -->
        <template v-if="testResult.storage?.length">
          <el-divider content-position="left">💾 存储</el-divider>
          <el-table :data="testResult.storage" size="small" stripe>
            <el-table-column prop="name" label="名称" min-width="200" />
            <el-table-column prop="size_mb" label="总大小" width="100">
              <template #default="{ row }">{{ formatMB(row.size_mb) }}</template>
            </el-table-column>
            <el-table-column prop="used_mb" label="已用" width="100">
              <template #default="{ row }">{{ formatMB(row.used_mb) }}</template>
            </el-table-column>
            <el-table-column label="使用率" width="120">
              <template #default="{ row }">
                <el-progress :percentage="row.used_pct" :stroke-width="16" :status="row.used_pct > 90 ? 'exception' : row.used_pct > 70 ? 'warning' : 'success'" />
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- OID查询结果 -->
        <el-divider content-position="left">📡 系统OID查询结果</el-divider>
        <el-table :data="oidTableData" size="small" stripe>
          <el-table-column prop="name" label="OID名称" width="120" />
          <el-table-column prop="oid" label="OID" width="180" />
          <el-table-column prop="value" label="值" min-width="250" show-overflow-tooltip />
        </el-table>

        <!-- 版本兼容性测试 -->
        <el-divider content-position="left">🔬 SNMP版本兼容性测试</el-divider>
        <el-table :data="versionTestTableData" size="small" stripe>
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'ok' ? 'success' : 'danger'" size="small">{{ row.status === 'ok' ? '✅ 成功' : '❌ 失败' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" label="详情" min-width="300" show-overflow-tooltip />
        </el-table>

        <!-- 自定义OID -->
        <template v-if="testResult.custom_oid">
          <el-divider content-position="left">🎯 自定义OID查询</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="OID">{{ testResult.custom_oid.oid }}</el-descriptions-item>
            <el-descriptions-item label="执行命令">
              <code style="font-size:12px;word-break:break-all">{{ testResult.custom_oid.raw_cmd }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="返回结果" v-if="testResult.custom_oid.success">
              <div class="text-wrap">{{ testResult.custom_oid.stdout || testResult.custom_oid.stderr }}</div>
            </el-descriptions-item>
            <el-descriptions-item label="错误信息" v-if="!testResult.custom_oid.success">
              <span class="text-error">{{ testResult.custom_oid.stderr }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </template>

      <!-- SSH测试结果 -->
      <template v-if="quickForm.protocol === 'ssh' && testResult.success">
        <el-divider content-position="left">SSH连接信息</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="认证状态">
            <el-tag :type="testResult.authenticated ? 'success' : 'warning'">
              {{ testResult.authenticated ? '已认证' : '未认证' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </template>

      <!-- 错误信息 -->
      <template v-if="testResult.error">
        <el-divider content-position="left">错误信息</el-divider>
        <div class="error-box">
          <pre>{{ testResult.error }}</pre>
        </div>
      </template>

      <!-- 原始响应（开发者用） -->
      <el-collapse class="raw-collapse">
        <el-collapse-item title="📋 原始响应数据（开发者）">
          <pre class="raw-json">{{ JSON.stringify(testResult, null, 2) }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 测试配置列表 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>📋 测试配置</span>
          <el-input v-model="configSearch" placeholder="搜索配置" size="small" style="width:200px" clearable>
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </template>

      <el-table :data="filteredConfigs" v-loading="configLoading" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="protocol" label="协议" width="120">
          <template #default="{ row }">
            <el-tag :type="getProtocolTagType(row.protocol)" size="small">{{ row.protocol.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" min-width="140" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="last_test_status" label="最近状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.last_test_status" :type="row.last_test_status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.last_test_status === 'success' ? '成功' : '失败' }}
            </el-tag>
            <span v-else class="text-muted">未测试</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_test_time" label="最近测试" width="160">
          <template #default="{ row }">
            {{ row.last_test_time ? formatTime(row.last_test_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="runConfigTest(row)" :loading="row._testing">
              <el-icon><VideoPlay /></el-icon> 测试
            </el-button>
            <el-button link type="info" size="small" @click="viewConfigResults(row)">
              <el-icon><View /></el-icon> 结果
            </el-button>
            <el-button link type="danger" size="small" @click="deleteConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建配置弹窗 -->
    <el-dialog v-model="createVisible" title="新建测试配置" width="600px">
      <el-form :model="configForm" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="configForm.name" placeholder="如：核心交换机SNMP测试" />
        </el-form-item>
        <el-form-item label="协议">
          <el-select v-model="configForm.protocol" style="width:100%">
            <el-option v-for="p in protocols" :key="p.code" :label="p.name" :value="p.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机">
          <el-input v-model="configForm.host" placeholder="IP地址" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input v-model="configForm.port" />
        </el-form-item>
        <el-form-item label="间隔(秒)">
          <el-input-number v-model="configForm.interval" :min="10" :max="86400" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="createConfig" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 历史结果弹窗 -->
    <el-dialog v-model="historyVisible" title="测试历史记录" width="1000px">
      <el-table :data="historyData" stripe size="small" max-height="400">
        <el-table-column prop="created_at" label="时间" width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="config_name" label="配置名称" width="130" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="100">
          <template #default="{ row }">{{ row.response_time ? row.response_time + 'ms' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip min-width="200" />
        <el-table-column label="数据预览" min-width="200">
          <template #default="{ row }">
            <span v-if="row.data?.raw?.device_info?.hostname">设备: {{ row.data.raw.device_info.hostname }}</span>
            <span v-else-if="row.data?.snmp_version">SNMP v{{ row.data.snmp_version }}</span>
            <span v-else-if="row.data?.device_info?.hostname">设备: {{ row.data.device_info.hostname }}</span>
            <span v-else-if="row.data?.db_info?.hostname">MySQL: {{ row.data.db_info.hostname }}</span>
            <span v-else-if="row.data?.db_info?.version">MSSQL: v{{ row.data.db_info.version }}</span>
            <span v-else-if="row.data?.version">{{ row.data.version }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewHistoryDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay, Search, View, Clock } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const testing = ref(false)
const creating = ref(false)
const configLoading = ref(false)
const createVisible = ref(false)
const historyVisible = ref(false)
const testResult = ref(null)
const configs = ref([])
const historyData = ref([])
const configSearch = ref('')
const protocols = ref([])

const quickForm = reactive({
  protocol: 'ping', host: '', port: '', timeout: 10,
  username: '', password: '', database: '', community: 'public',
  snmpVersion: 'v2c', customOid: ''
})

const configForm = reactive({
  name: '', protocol: 'ping', host: '', port: '', interval: 300, customer: 1
})

// 计算属性
const defaultPort = computed(() => {
  const map = { snmp: '161', ssh: '22', mysql: '3306', mssql: '1433', oracle: '1521', postgresql: '5432', port: '80' }
  return map[quickForm.protocol] || ''
})

const showAuthFields = computed(() => ['ssh', 'mysql', 'mssql', 'oracle', 'postgresql', 'snmp'].includes(quickForm.protocol))
const showDbField = computed(() => ['mysql', 'mssql', 'oracle', 'postgresql'].includes(quickForm.protocol))
const isDbProtocol = computed(() => ['mysql', 'mssql', 'oracle', 'postgresql'].includes(quickForm.protocol))

const dbPlaceholder = computed(() => {
  const map = { mysql: 'mysql', mssql: 'master', oracle: 'ORCL', postgresql: 'postgres' }
  return map[quickForm.protocol] || '数据库名'
})

const filteredConfigs = computed(() => {
  if (!configSearch.value) return configs.value
  const s = configSearch.value.toLowerCase()
  return configs.value.filter(c =>
    (c.name || '').toLowerCase().includes(s) ||
    (c.host || '').toLowerCase().includes(s) ||
    (c.protocol || '').toLowerCase().includes(s)
  )
})

function getProtocolTagType(p) {
  const map = { ping: 'info', port: 'info', snmp: 'success', ssh: 'warning', mysql: '', mssql: 'danger', oracle: 'warning', postgresql: '' }
  return map[p] || 'info'
}

function formatTime(t) {
  return new Date(t).toLocaleString('zh-CN')
}

// 设备类型中文标签
const deviceTypeLabel = computed(() => {
  const map = {
    cisco: '思科(Cisco)',
    huawei: '华为(Huawei)',
    h3c: 'H3C',
    ruijie: '锐捷(Ruijie)',
    linux_server: 'Linux服务器',
    windows_server: 'Windows服务器',
    fortinet: '飞塔(Fortinet)',
    juniper: '瞻博(Juniper)',
    hp_aruba: 'HP/Aruba',
    unknown: '未知设备',
  }
  const dt = testResult.value?.device_type
  return map[dt] || dt || '未知'
})

// OID查询结果表格数据
const oidTableData = computed(() => {
  const oids = testResult.value?.oids
  if (!oids) return []
  const oidMap = {
    sysDescr: '1.3.6.1.2.1.1.1.0',
    sysObjectID: '1.3.6.1.2.1.1.2.0',
    sysUpTime: '1.3.6.1.2.1.1.3.0',
    sysContact: '1.3.6.1.2.1.1.4.0',
    sysName: '1.3.6.1.2.1.1.5.0',
    sysLocation: '1.3.6.1.2.1.1.6.0',
    sysServices: '1.3.6.1.2.1.1.7.0',
    ifNumber: '1.3.6.1.2.1.2.1.0',
  }
  return Object.entries(oids).map(([name, value]) => ({
    name,
    oid: oidMap[name] || '',
    value: String(value).substring(0, 200)
  }))
})

// 版本测试表格数据
const versionTestTableData = computed(() => {
  const vt = testResult.value?.version_tests
  if (!vt) return []
  return Object.entries(vt).map(([ver, info]) => ({
    version: ver,
    status: info.status,
    detail: info.status === 'ok' ? info.value?.substring(0, 150) || '成功' : info.error?.substring(0, 200) || '失败'
  }))
})

// 格式化大小（MB → 可读格式，用于 Oracle 表空间）
const getOracleTablespaces = computed(() => {
  const r = testResult.value
  if (!r) return []
  // 快速测试: 数据在顶层
  if (r.tablespaces?.length) {
    return r.tablespaces.map(ts => ({
      name: ts.TABLESPACE_NAME || ts.tablespace_name || '',
      status: ts.STATUS || ts.status || 'ONLINE',
      contents: ts.CONTENTS || ts.contents || '',
      total_mb: ts.total_mb || ts.TOTAL_MB || 0,
      used_mb: ts.used_mb || ts.USED_MB || 0,
      free_mb: ts.free_mb || ts.FREE_MB || 0,
      used_pct: ts.used_pct || ts.USED_PCT || 0,
    }))
  }
  // 配置测试: 数据在 data 层
  const data_tablespaces = r.data?.tablespaces || r.data?.tablespace_usage || []
  if (data_tablespaces.length) {
    return data_tablespaces.map(ts => ({
      name: ts.TABLESPACE_NAME || ts.tablespace_name || ts.name || '',
      status: ts.STATUS || ts.status || 'ONLINE',
      contents: ts.CONTENTS || ts.contents || '',
      total_mb: ts.total_mb || ts.TOTAL_MB || 0,
      used_mb: ts.used_mb || ts.USED_MB || 0,
      free_mb: ts.free_mb || ts.FREE_MB || 0,
      used_pct: ts.used_pct || ts.USED_PCT || 0,
    }))
  }
  return []
})

// 格式化存储大小
function formatMB(mb) {
  if (!mb && mb !== 0) return '-'
  if (mb === 'N/A') return 'N/A'
  const num = Number(mb)
  if (isNaN(num)) return '-'
  if (num >= 1024) return (num / 1024).toFixed(1) + ' GB'
  return num.toFixed(0) + ' MB'
}

// 格式化 MySQL 运行时间（秒 → 可读格式）
function formatUptime(seconds) {
  if (!seconds && seconds !== 0) return null
  const s = parseInt(seconds)
  if (isNaN(s)) return seconds
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${d}天 ${h}小时 ${m}分钟`
}

// MySQL 状态表格数据
const mysqlStatusData = computed(() => {
  const st = testResult.value?.status
  if (!st) return []
  const statusLabels = {
    Uptime: '运行时间', Threads_connected: '当前连接数', Threads_running: '运行中线程',
    Connections: '累计连接数', Questions: '查询数', Queries: '总查询数',
    Bytes_received: '接收字节', Bytes_sent: '发送字节',
    Slow_queries: '慢查询', Open_tables: '打开的表', Table_locks_immediate: '立即表锁',
    Table_locks_waited: '等待表锁', Innodb_buffer_pool_read_requests: 'InnoDB缓冲池读请求',
    Innodb_buffer_pool_reads: 'InnoDB磁盘读取', Innodb_rows_read: 'InnoDB行读取',
    Created_tmp_disk_tables: '磁盘临时表', Select_full_join: '全表连接',
    Aborted_connects: '中止连接', Max_used_connections: '最大并发连接',
  }
  return Object.entries(st).map(([k, v]) => ({
    name: statusLabels[k] || k,
    value: k === 'Uptime' ? formatUptime(v) : v
  }))
})

// MySQL 变量表格数据
const mysqlVariableData = computed(() => {
  const vars = testResult.value?.variables
  if (!vars) return []
  const varLabels = {
    version: '版本', version_comment: '版本注释', hostname: '主机名', port: '端口',
    max_connections: '最大连接数', max_allowed_packet: '最大允许包大小',
    character_set_server: '服务端字符集', collation_server: '服务端排序规则',
    innodb_buffer_pool_size: 'InnoDB缓冲池大小', innodb_log_file_size: 'InnoDB日志大小',
    wait_timeout: '等待超时(s)', interactive_timeout: '交互超时(s)',
    datadir: '数据目录', basedir: '安装目录', tmpdir: '临时目录',
    log_bin: '二进制日志', server_id: '服务器ID', thread_cache_size: '线程缓存大小',
    query_cache_type: '查询缓存', have_ssl: 'SSL支持',
  }
  return Object.entries(vars).map(([k, v]) => ({
    name: varLabels[k] || k,
    value: v || '-'
  }))
})

// MSSQL 配置表格数据
const mssqlConfigData = computed(() => {
  const cfg = testResult.value?.config
  if (!cfg) return []
  const cfgLabels = {
    'max server memory (MB)': '最大内存(MB)', 'min server memory (MB)': '最小内存(MB)',
    'user connections': '用户连接数', 'remote access': '远程访问',
    'remote query timeout (s)': '远程查询超时(s)', 'nested triggers': '嵌套触发器',
    'default language': '默认语言', 'max degree of parallelism': '最大并行度',
    'cost threshold for parallelism': '并行成本阈值', 'fill factor (%)': '填充因子(%)',
    'backup compression default': '备份压缩', 'blocked process threshold (s)': '阻塞进程阈值(s)',
    'cursor threshold': '游标阈值', 'max worker threads': '最大工作线程',
    'recovery interval (min)': '恢复间隔(分钟)', 'scan for startup procs': '启动时扫描存储过程',
  }
  return Object.entries(cfg).map(([k, v]) => ({
    name: cfgLabels[k] || k,
    value: v || '-'
  }))
})

function onProtocolChange() {
  quickForm.port = defaultPort.value
  if (quickForm.protocol === 'snmp') { quickForm.community = 'public'; quickForm.port = '161' }
}

async function runQuickTest() {
  if (!quickForm.host) { ElMessage.warning('请输入主机地址'); return }
  testing.value = true
  testResult.value = null

  const data = { protocol: quickForm.protocol, host: quickForm.host, timeout: quickForm.timeout }
  if (quickForm.port) data.port = parseInt(quickForm.port)
  if (showAuthFields.value) {
    data.username = quickForm.username
    data.password = quickForm.password
  }
  if (showDbField.value) data.database = quickForm.database
  if (quickForm.protocol === 'snmp') {
    data.community = quickForm.community
    data.version = quickForm.snmpVersion || 'v2c'
    if (quickForm.customOid) data.oid = quickForm.customOid
  }

  try {
    const res = await axios.post('/api/monitoring/quick-test/', data)
    testResult.value = res.data || res
    if (testResult.value.success) {
      ElMessage.success(`测试成功 (${testResult.value.test_duration}ms)`)
    } else {
      ElMessage.error(`测试失败: ${testResult.value.error || '未知错误'}`)
    }
  } catch (e) {
    testResult.value = { success: false, error: e.message || '请求失败', protocol: quickForm.protocol, host: quickForm.host }
    ElMessage.error('测试请求失败')
  } finally {
    testing.value = false
  }
}

const sending = ref(false)


async function sendResult() {
  if (!testResult.value?.result_id) {
    ElMessage.warning('请先执行测试')
    return
  }
  sending.value = true
  try {
    await axios.post(`/api/monitoring/test-results/${testResult.value.result_id}/push/`)
    ElMessage.success('已发送到中心端')
  } catch (e) {
    ElMessage.error('发送失败: ' + (e.response?.data?.message || e.message))
  } finally {
    sending.value = false
  }
}

function copyResult() {
  const text = JSON.stringify(testResult.value, null, 2)
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}

async function loadProtocols() {
  try {
    const res = await axios.get('/api/monitoring/test-configs/protocols/')
    protocols.value = res.data || res
  } catch { protocols.value = [] }
}

async function loadConfigs() {
  configLoading.value = true
  try {
    const res = await axios.get('/api/monitoring/test-configs/')
    configs.value = (res.results || res.data?.results || []).map(c => ({ ...c, _testing: false }))
  } catch { /* ignore */ }
  finally { configLoading.value = false }
}

async function runConfigTest(row) {
  row._testing = true
  try {
    const res = await axios.post(`/api/monitoring/test-configs/${row.id}/test/`)
    const result = res.data || res
    row.last_test_status = result.success ? 'success' : 'failed'
    row.last_test_time = new Date().toISOString()
    testResult.value = result
    ElMessage[result.success ? 'success' : 'error'](result.success ? '测试成功' : `测试失败: ${result.error || ''}`)
  } catch { ElMessage.error('测试失败') }
  finally { row._testing = false }
}

async function viewConfigResults(row) {
  try {
    const res = await axios.get('/api/monitoring/test-results/', { params: { config: row.id, page_size: 20 } })
    historyData.value = res.results || res.data?.results || []
    historyVisible.value = true
  } catch { ElMessage.error('加载失败') }
}

function showCreateDialog() {
  Object.assign(configForm, { name: '', protocol: 'ping', host: '', port: '', interval: 300 })
  createVisible.value = true
}

async function createConfig() {
  if (!configForm.name || !configForm.host) { ElMessage.warning('请填写名称和主机'); return }
  creating.value = true
  try {
    await axios.post('/api/monitoring/test-configs/', configForm)
    ElMessage.success('创建成功')
    createVisible.value = false
    loadConfigs()
  } catch { ElMessage.error('创建失败') }
  finally { creating.value = false }
}

async function deleteConfig(row) {
  await ElMessageBox.confirm('确定删除?', '提示')
  try {
    await axios.delete(`/api/monitoring/test-configs/${row.id}/`)
    ElMessage.success('已删除')
    loadConfigs()
  } catch { ElMessage.error('删除失败') }
}

async function viewHistoryDetail(row) {
  // 把历史记录的data内容填充到当前testResult展示
  if (row.data?.raw) {
    testResult.value = {
      ...row.data.raw,
      success: row.status === 'success'
    }
  } else if (row.data) {
    testResult.value = {
      ...row.data,
      success: row.status === 'success'
    }
  } else {
    testResult.value = {
      success: row.status === 'success',
      error: row.error_message,
      response_time: row.response_time,
    }
  }
  historyVisible.value = false
  ElMessage.info('已将历史记录加载到结果区域')
}

async function loadHistory() {
  try {
    const res = await axios.get('/api/monitoring/test-results/', { params: { page_size: 50 } })
    historyData.value = res.results || res.data?.results || []
    historyVisible.value = true
  } catch { ElMessage.error('加载失败') }
}

onMounted(() => {
  loadProtocols()
  loadConfigs()
})
</script>

<style scoped>
.monitor-test { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }

.card-header { display: flex; justify-content: space-between; align-items: center; }
.hint { font-size: 12px; color: #909399; font-weight: normal; }

.quick-test-card { margin-bottom: 16px; }
.result-card { margin-bottom: 16px; }
.result-card.success { border: 1px solid #67c23a; }
.result-card.error { border: 1px solid #f56c6c; }

.config-card { margin-bottom: 16px; }

.text-wrap { word-break: break-all; white-space: pre-wrap; }
.text-muted { color: #c0c4cc; }

.result-info { margin-bottom: 16px; }

.error-box {
  background: #fef0f0; border: 1px solid #fbc4c4; border-radius: 4px;
  padding: 12px 16px; margin: 8px 0;
}
.error-box pre { margin: 0; color: #f56c6c; white-space: pre-wrap; word-break: break-all; font-size: 13px; }

.raw-collapse { margin-top: 12px; }
.tag-list { display: flex; flex-wrap: wrap; gap: 4px; padding: 8px 0; }
.raw-json {
  background: #f5f7fa; padding: 12px; border-radius: 4px;
  font-size: 12px; max-height: 300px; overflow-y: auto;
  white-space: pre-wrap; word-break: break-all;
}
</style>
