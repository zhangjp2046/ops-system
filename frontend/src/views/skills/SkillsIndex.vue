<template>
  <div class="skills-page">
    <div class="header">
      <h2>技能库</h2>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- ========== 技能列表 ========== -->
      <el-tab-pane label="技能列表" name="skills">
        <el-row :gutter="16" class="stats-row">
          <el-col :span="6">
            <el-card shadow="never">
              <el-statistic title="技能总数" :value="skills.length" />
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <el-statistic title="已启用" :value="enabledCount" />
            </el-card>
          </el-col>
        </el-row>

        <el-table :data="skills" stripe v-loading="loadingSkills">
          <el-table-column prop="code" label="编码" width="180">
            <template #default="{ row }">
              <code style="font-size: 13px; color: #409EFF">{{ row.code }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" width="140">
            <template #default="{ row }">
              <strong>{{ row.name }}</strong>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" />
          <el-table-column prop="is_enabled" label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_enabled" type="success" size="small">启用</el-tag>
              <el-tag v-else type="info" size="small">禁用</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="openExecuteDialog(row)">立即执行</el-button>
              <el-button size="small" @click="openTemplateDialog(row)">创建计划</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ========== 任务模板 ========== -->
      <el-tab-pane label="任务模板" name="templates">
        <div class="toolbar">
          <el-button type="primary" @click="showCreateTemplateDialog = true">
            <el-icon><Plus /></el-icon>
            新建模板
          </el-button>
        </div>
        <el-row :gutter="16">
          <el-col :span="6" v-for="tpl in templates" :key="tpl.id">
            <el-card class="template-card" shadow="never" @click="openUseTemplateDialog(tpl)">
              <div class="tpl-icon" :style="{ background: tpl.color }">
                <el-icon :size="24"><component :is="tpl.icon" /></el-icon>
              </div>
              <h4>{{ tpl.name }}</h4>
              <p style="font-size: 12px; color: #666; margin: 4px 0">{{ tpl.description }}</p>
              <div class="tpl-meta">
                <el-tag size="small">{{ getCategoryLabel(tpl.category) }}</el-tag>
                <span style="color: #999; font-size: 12px">使用 {{ tpl.usage_count || 0 }} 次</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
        <el-empty v-if="!loadingTemplates && templates.length === 0" description="暂无模板" />
      </el-tab-pane>

      <!-- ========== 巡检计划 ========== -->
      <el-tab-pane label="巡检计划" name="inspection">
        <div class="toolbar">
          <el-input v-model="inspectionSearch" placeholder="搜索计划名称" style="width: 200px" clearable @clear="loadInspectionPlans" />
          <el-select v-model="inspectionStatus" placeholder="状态" clearable style="width: 120px" @change="loadInspectionPlans">
            <el-option label="全部" value="" />
            <el-option label="草稿" value="draft" />
            <el-option label="启用" value="active" />
            <el-option label="暂停" value="paused" />
            <el-option label="归档" value="archived" />
          </el-select>
          <el-button @click="loadInspectionPlans">搜索</el-button>
          <el-button type="primary" @click="openInspectionPlanForm(null)">
            <el-icon><Plus /></el-icon>
            新建巡检计划
          </el-button>
        </div>

        <el-table :data="inspectionPlans" stripe v-loading="loadingInspectionPlans">
          <el-table-column prop="name" label="计划名称" min-width="150">
            <template #default="{ row }">
              <strong>{{ row.name }}</strong>
              <div style="font-size: 12px; color: #999">{{ row.code }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="protocol" label="协议" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ row.protocol?.toUpperCase() }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="cycle" label="周期" width="100">
            <template #default="{ row }">{{ getCycleLabel(row.cycle) }}</template>
          </el-table-column>
          <el-table-column prop="scheduled_time" label="时间" width="80">
            <template #default="{ row }">{{ row.scheduled_time }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="task_count" label="任务" width="70" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.task_count || 0 }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" align="center">
            <template #default="{ row }">
              <el-button size="small" @click="doExecuteInspectionPlan(row)">执行</el-button>
              <el-button size="small" @click="viewInspectionTasks(row)">任务</el-button>
              <el-button size="small" type="primary" @click="openInspectionPlanForm(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteInspectionPlanById(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="inspectionTotal > 0"
          layout="prev, pager, next"
          :total="inspectionTotal"
          :page-size="inspectionPageSize"
          :current-page="inspectionPage"
          @current-change="p => { inspectionPage = p; loadInspectionPlans() }"
          style="margin-top: 16px; justify-content: center"
        />
      </el-tab-pane>

      <!-- ========== 定时任务 ========== -->
      <el-tab-pane label="定时任务" name="scheduler">
        <div class="toolbar">
          <el-select v-model="schedulerPlanType" placeholder="计划类型" clearable style="width: 140px" @change="loadSchedulerPlans">
            <el-option label="全部" value="" />
            <el-option label="巡检计划" value="inspection" />
            <el-option label="推送计划" value="push" />
            <el-option label="监控计划" value="monitoring" />
            <el-option label="发现计划" value="discovery" />
            <el-option label="综合计划" value="mixed" />
          </el-select>
          <el-select v-model="schedulerEnabled" placeholder="状态" clearable style="width: 120px" @change="loadSchedulerPlans">
            <el-option label="已启用" value="true" />
            <el-option label="已禁用" value="false" />
          </el-select>
          <el-button @click="loadSchedulerPlans">筛选</el-button>
          <el-button type="primary" @click="openSchedulerPlanForm(null)">
            <el-icon><Plus /></el-icon>
            新建调度计划
          </el-button>
        </div>

        <el-table :data="schedulerPlans" stripe v-loading="loadingSchedulerPlans">
          <el-table-column prop="name" label="计划名称" min-width="150">
            <template #default="{ row }">
              <strong>{{ row.name }}</strong>
              <div style="font-size: 12px; color: #999">{{ row.description }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="plan_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ getPlanTypeLabel(row.plan_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="task_count" label="任务数" width="80" align="center" />
          <el-table-column label="关联巡检" width="140">
            <template #default="{ row }">
              <span v-if="row.inspection_plan_name" style="color: #67C23A; font-size: 13px">
                <el-icon><Link /></el-icon> {{ row.inspection_plan_name }}
              </span>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="is_enabled" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
                {{ row.is_enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="调度" width="160">
            <template #default="{ row }">
              <div v-if="row.schedule_info">
                <span v-if="row.schedule_info.schedule_type === 'daily'" style="font-size: 13px">
                  <el-icon><Clock /></el-icon> 每天 {{ row.schedule_info.daily_time }}
                </span>
                <span v-else-if="row.schedule_info.schedule_type === 'weekly'" style="font-size: 13px">
                  <el-icon><Clock /></el-icon> 每周{{ ['一','二','三','四','五','六','日'][row.schedule_info.weekday] }} {{ row.schedule_info.daily_time }}
                </span>
                <span v-else-if="row.schedule_info.schedule_type === 'interval'" style="font-size: 13px">
                  <el-icon><Timer /></el-icon> 每{{ row.schedule_info.interval_value }}{{ row.schedule_info.interval_unit === 'hours' ? '小时' : '分钟' }}
                </span>
                <span v-else style="font-size: 13px; color: #999">{{ row.cron_expression }}</span>
              </div>
              <span v-else style="color: #999">手动</span>
            </template>
          </el-table-column>
          <el-table-column prop="next_run_time" label="下次运行" width="160">
            <template #default="{ row }">
              <span v-if="row.next_run_time">{{ formatTime(row.next_run_time) }}</span>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" align="center">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="doExecuteSchedulerPlan(row)">执行</el-button>
              <el-button size="small" @click="openSchedulerPlanForm(row)">编辑</el-button>
              <el-button size="small" :type="row.is_enabled ? 'warning' : 'success'" @click="doToggleSchedulerPlan(row)">
                {{ row.is_enabled ? '禁用' : '启用' }}
              </el-button>
              <el-button size="small" type="danger" @click="doDeleteSchedulerPlan(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="schedulerTotal > 0"
          layout="prev, pager, next"
          :total="schedulerTotal"
          :page-size="schedulerPageSize"
          :current-page="schedulerPage"
          @current-change="p => { schedulerPage = p; loadSchedulerPlans() }"
          style="margin-top: 16px; justify-content: center"
        />
      </el-tab-pane>

      <!-- ========== 巡检记录 ========== -->
      <el-tab-pane label="巡检记录" name="records">
        <div class="toolbar">
          <el-input v-model="recordSearch" placeholder="搜索资产名称" style="width: 200px" clearable @clear="loadInspectionRecords" />
          <el-select v-model="recordStatus" placeholder="状态" clearable style="width: 140px" @change="loadInspectionRecords">
            <el-option label="全部" value="" />
            <el-option label="运行中" value="RUNNING" />
            <el-option label="完成" value="COMPLETED" />
            <el-option label="警告" value="WARNING" />
            <el-option label="失败" value="FAILED" />
          </el-select>
          <el-button @click="loadInspectionRecords">搜索</el-button>
        </div>

        <el-table :data="inspectionRecords" stripe v-loading="loadingRecords">
          <el-table-column prop="name" label="巡检名称" min-width="160" />
          <el-table-column prop="asset_name" label="资产" width="140" />
          <el-table-column prop="inspection_type" label="类型" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ row.inspection_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="getRecordStatusType(row.status)">
                {{ getRecordStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="检查结果" width="160">
            <template #default="{ row }">
              <span style="color: #67C23A">{{ row.passed_items || 0 }} 通过</span>
              <span style="color: #E6A23C; margin-left: 6px">{{ row.warning_items || 0 }} 警告</span>
              <span style="color: #F56C6C; margin-left: 6px">{{ row.failed_items || 0 }} 失败</span>
            </template>
          </el-table-column>
          <el-table-column prop="started_at" label="开始时间" width="160">
            <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button size="small" @click="viewRecordDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="recordTotal > 0"
          layout="prev, pager, next"
          :total="recordTotal"
          :page-size="recordPageSize"
          :current-page="recordPage"
          @current-change="p => { recordPage = p; loadInspectionRecords() }"
          style="margin-top: 16px; justify-content: center"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- ========== 执行技能对话框 ========== -->
    <el-dialog v-model="executeDialogVisible" :title="`执行技能: ${currentSkill?.name}`" width="600px">
      <el-form :model="executeForm" label-width="120px">
        <el-form-item label="技能编码">
          <el-input v-model="executeForm.skill_code" disabled />
        </el-form-item>
        <el-form-item label="技能描述">
          <div style="color: #666">{{ currentSkill?.description }}</div>
        </el-form-item>
        <el-divider v-if="currentSkill?.param_schema?.properties" content-position="left">参数配置</el-divider>
        <el-form-item
          v-for="(schema, key) in currentSkill?.param_schema?.properties"
          :key="key"
          :label="schema.description || key"
        >
          <el-input v-if="schema.type === 'string'" v-model="executeForm.config[key]" :placeholder="schema.description || key" />
          <el-input-number v-else-if="schema.type === 'integer'" v-model="executeForm.config[key]" :min="0" />
          <el-switch v-else-if="schema.type === 'boolean'" v-model="executeForm.config[key]" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="executeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleExecute" :loading="executing">立即执行</el-button>
      </template>
    </el-dialog>

    <!-- ========== 巡检计划表单 ========== -->
    <el-dialog v-model="inspectionPlanFormVisible" :title="inspectionPlanFormTitle" width="700px">
      <el-form :model="inspectionPlanForm" label-width="120px">
        <el-form-item label="计划名称" required>
          <el-input v-model="inspectionPlanForm.name" placeholder="如: MySQL数据库巡检" />
        </el-form-item>
        <el-form-item label="计划编码" required>
          <el-input v-model="inspectionPlanForm.code" placeholder="如: mysql_db_check" :disabled="!!inspectionPlanForm.id" />
        </el-form-item>
        <el-form-item label="协议类型">
          <el-select v-model="inspectionPlanForm.protocol" style="width: 100%">
            <el-option label="SNMP" value="snmp" />
            <el-option label="MySQL" value="mysql" />
            <el-option label="MSSQL" value="mssql" />
            <el-option label="Oracle" value="oracle" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="Ping" value="ping" />
            <el-option label="SSH" value="ssh" />
            <el-option label="Port" value="port" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行周期">
          <el-select v-model="inspectionPlanForm.cycle" style="width: 100%">
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" />
            <el-option label="每季度" value="quarterly" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划执行时间">
          <el-time-picker v-model="inspectionPlanForm.scheduled_time" format="HH:mm" value-format="HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="inspectionPlanForm.status" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="启用" value="active" />
            <el-option label="暂停" value="paused" />
            <el-option label="归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="inspectionPlanForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inspectionPlanFormVisible = false">取消</el-button>
        <el-button type="primary" @click="saveInspectionPlan" :loading="savingPlan">保存</el-button>
      </template>
    </el-dialog>

    <!-- ========== 巡检任务列表 ========== -->
    <el-dialog v-model="inspectionTasksDialogVisible" :title="`巡检任务 - ${currentInspectionPlan?.name}`" width="800px">
      <div style="margin-bottom: 12px">
        <el-button size="small" type="primary" @click="syncInspectionTasks">同步资产</el-button>
      </div>
      <el-table :data="inspectionTasks" size="small">
        <el-table-column prop="asset_name" label="资产" min-width="140" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="getTaskStatusType(row.status)">{{ getTaskStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scheduled_time" label="计划时间" width="160" />
        <el-table-column prop="executed_time" label="执行时间" width="160">
          <template #default="{ row }">{{ formatTime(row.executed_time) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- ========== 调度计划表单 ========== -->
    <el-dialog v-model="schedulerPlanFormVisible" :title="schedulerPlanFormTitle" width="700px">
      <el-form :model="schedulerPlanForm" label-width="130px">
        <el-form-item label="计划名称" required>
          <el-input v-model="schedulerPlanForm.name" placeholder="如: 每日巡检" />
        </el-form-item>
        <el-form-item label="计划类型">
          <el-select v-model="schedulerPlanForm.plan_type" style="width: 100%">
            <el-option label="巡检计划" value="inspection" />
            <el-option label="推送计划" value="push" />
            <el-option label="监控计划" value="monitoring" />
            <el-option label="发现计划" value="discovery" />
            <el-option label="综合计划" value="mixed" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联巡检计划">
          <el-select v-model="schedulerPlanForm.inspection_plan" style="width: 100%" clearable placeholder="选择关联的巡检计划">
            <el-option v-for="p in allInspectionPlans" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度类型">
          <el-select v-model="schedulerPlanForm.schedule_type" style="width: 100%">
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" />
            <el-option label="间隔执行" value="interval" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行时间" v-if="schedulerPlanForm.schedule_type === 'daily'">
          <el-time-picker v-model="schedulerPlanForm.daily_time" format="HH:mm" value-format="HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="执行时间" v-if="schedulerPlanForm.schedule_type === 'weekly'">
          <div style="display: flex; gap: 8px">
            <el-select v-model="schedulerPlanForm.weekday" style="width: 120px">
              <el-option v-for="(d, i) in ['周一','周二','周三','周四','周五','周六','周日']" :key="i" :label="d" :value="i" />
            </el-select>
            <el-time-picker v-model="schedulerPlanForm.daily_time" format="HH:mm" value-format="HH:mm" style="width: 150px" />
          </div>
        </el-form-item>
        <el-form-item label="每月几号" v-if="schedulerPlanForm.schedule_type === 'monthly'">
          <div style="display: flex; gap: 8px">
            <el-input-number v-model="schedulerPlanForm.day_of_month" :min="1" :max="28" style="width: 100px" />
            <el-time-picker v-model="schedulerPlanForm.daily_time" format="HH:mm" value-format="HH:mm" style="width: 150px" />
          </div>
        </el-form-item>
        <el-form-item label="间隔" v-if="schedulerPlanForm.schedule_type === 'interval'">
          <div style="display: flex; gap: 8px; align-items: center">
            每<el-input-number v-model="schedulerPlanForm.interval_value" :min="1" style="width: 100px" />
            <el-select v-model="schedulerPlanForm.interval_unit" style="width: 120px">
              <el-option label="分钟" value="minutes" />
              <el-option label="小时" value="hours" />
            </el-select>
          </div>
        </el-form-item>
        <el-form-item label="任务配置" v-if="schedulerPlanForm.plan_type === 'mixed' || !schedulerPlanForm.inspection_plan">
          <el-input v-model="schedulerTaskConfig" type="textarea" :rows="3" placeholder="JSON 格式任务配置，如: {&quot;asset_id&quot;: 1}" />
        </el-form-item>
        <el-form-item label="冲突策略">
          <el-select v-model="schedulerPlanForm.conflict_strategy" style="width: 100%">
            <el-option label="跳过" value="skip" />
            <el-option label="排队等待" value="queue" />
            <el-option label="强制执行" value="force" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="schedulerPlanForm.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="schedulerPlanFormVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSchedulerPlan" :loading="savingSchedulerPlan">保存</el-button>
      </template>
    </el-dialog>

    <!-- ========== 巡检记录详情 ========== -->
    <el-dialog v-model="recordDetailDialogVisible" title="巡检记录详情" width="700px">
      <el-descriptions :column="2" border v-if="currentRecord">
        <el-descriptions-item label="巡检名称">{{ currentRecord.name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getRecordStatusType(currentRecord.status)" size="small">{{ getRecordStatusLabel(currentRecord.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产">{{ currentRecord.asset_name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ currentRecord.inspection_type }}</el-descriptions-item>
        <el-descriptions-item label="通过">{{ currentRecord.passed_items }}</el-descriptions-item>
        <el-descriptions-item label="警告">{{ currentRecord.warning_items }}</el-descriptions-item>
        <el-descriptions-item label="失败">{{ currentRecord.failed_items }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentRecord.duration_ms }} ms</el-descriptions-item>
        <el-descriptions-item label="开始时间" :span="2">{{ formatTime(currentRecord.started_at) }}</el-descriptions-item>
        <el-descriptions-item label="摘要" :span="2">{{ currentRecord.summary }}</el-descriptions-item>
      </el-descriptions>
      <el-divider content-position="left">检查项</el-divider>
      <el-table :data="recordItems" size="small" max-height="300">
        <el-table-column prop="item_name" label="检查项" min-width="120" />
        <el-table-column prop="category" label="类别" width="100" />
        <el-table-column prop="result" label="结果" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="getItemResultType(row.result)">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actual_value" label="实际值" min-width="120" show-overflow-tooltip />
        <el-table-column prop="message" label="消息" min-width="150" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getSkillList, executeSkill,
  getInspectionPlans, createInspectionPlan, updateInspectionPlan, deleteInspectionPlan, executeInspectionPlan,
  getInspectionTasks, getInspectionRecords, getInspectionRecord,
  getTaskTemplates, useTaskTemplate,
  getSchedulerPlans, getSchedulerPlan, createSchedulerPlan, updateSchedulerPlan,
  deleteSchedulerPlan, executeSchedulerPlan, toggleSchedulerPlan
} from '@/api/skills'

const activeTab = ref('skills')

// ========== 技能 ==========
const skills = ref([])
const loadingSkills = ref(false)
const enabledCount = computed(() => skills.value.filter(s => s.is_enabled).length)

// ========== 任务模板 ==========
const templates = ref([])
const loadingTemplates = ref(false)
const showCreateTemplateDialog = ref(false)

// ========== 巡检计划 ==========
const inspectionPlans = ref([])
const loadingInspectionPlans = ref(false)
const inspectionSearch = ref('')
const inspectionStatus = ref('')
const inspectionPage = ref(1)
const inspectionPageSize = ref(10)
const inspectionTotal = ref(0)
const inspectionPlanFormVisible = ref(false)
const inspectionPlanFormTitle = ref('')
const inspectionPlanForm = ref({})
const savingPlan = ref(false)
const inspectionTasksDialogVisible = ref(false)
const currentInspectionPlan = ref(null)
const inspectionTasks = ref([])

// ========== 调度计划 ==========
const schedulerPlans = ref([])
const loadingSchedulerPlans = ref(false)
const schedulerPlanType = ref('')
const schedulerEnabled = ref('')
const schedulerPage = ref(1)
const schedulerPageSize = ref(10)
const schedulerTotal = ref(0)
const schedulerPlanFormVisible = ref(false)
const schedulerPlanFormTitle = ref('')
const schedulerPlanForm = ref({})
const schedulerTaskConfig = ref('')
const savingSchedulerPlan = ref(false)
const allInspectionPlans = ref([])

// ========== 巡检记录 ==========
const inspectionRecords = ref([])
const loadingRecords = ref(false)
const recordSearch = ref('')
const recordStatus = ref('')
const recordPage = ref(1)
const recordPageSize = ref(10)
const recordTotal = ref(0)
const recordDetailDialogVisible = ref(false)
const currentRecord = ref(null)
const recordItems = ref([])

// ========== 执行技能 ==========
const executeDialogVisible = ref(false)
const currentSkill = ref(null)
const executeForm = ref({ skill_code: '', config: {} })
const executing = ref(false)

onMounted(() => {
  const route = useRoute()
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  loadSkills()
  loadTemplates()
  loadInspectionPlans()
  loadInspectionRecords()
  loadSchedulerPlans()
})

// ========== 技能 ==========
async function loadSkills() {
  loadingSkills.value = true
  try {
    const res = await getSkillList()
    skills.value = res.skills || []
  } catch { ElMessage.error('加载技能列表失败') }
  finally { loadingSkills.value = false }
}

function openExecuteDialog(skill) {
  currentSkill.value = skill
  executeForm.value = { skill_code: skill.code, config: {} }
  executeDialogVisible.value = true
}

async function handleExecute() {
  executing.value = true
  try {
    const res = await executeSkill({ skill_code: executeForm.value.skill_code, config: executeForm.value.config })
    if (res.success) {
      ElMessage.success(`执行成功 (${res.duration_ms}ms)`)
      executeDialogVisible.value = false
    } else {
      ElMessage.error(`执行失败: ${res.error}`)
    }
  } catch { ElMessage.error('执行失败') }
  finally { executing.value = false }
}

function openTemplateDialog(skill) {
  ElMessage.info('可使用"任务模板"Tab，基于技能创建调度计划')
  activeTab.value = 'templates'
}

// ========== 任务模板 ==========
async function loadTemplates() {
  loadingTemplates.value = true
  try {
    const res = await getTaskTemplates()
    templates.value = res.results || []
  } catch { ElMessage.error('加载模板失败') }
  finally { loadingTemplates.value = false }
}

function openUseTemplateDialog(tpl) {
  ElMessageBox.confirm(
    `确定使用模板「${tpl.name}」创建调度计划？`,
    '使用模板',
    { type: 'info' }
  ).then(async () => {
    try {
      const res = await useTaskTemplate(tpl.id, { plan_name: `${tpl.name}（调度）` })
      if (res.plan_id) {
        ElMessage.success('调度计划已创建，请在"定时任务"Tab查看')
        activeTab.value = 'scheduler'
        loadSchedulerPlans()
      } else {
        ElMessage.error(res.message || '创建失败')
      }
    } catch { ElMessage.error('创建失败') }
  }).catch(() => {})
}

function getCategoryLabel(category) {
  const map = { inspection: '巡检', push: '推送', monitoring: '监控', discovery: '发现', maintenance: '维护' }
  return map[category] || category
}

// ========== 巡检计划 ==========
async function loadInspectionPlans() {
  loadingInspectionPlans.value = true
  try {
    const params = { page: inspectionPage.value, page_size: inspectionPageSize.value }
    if (inspectionSearch.value) params.search = inspectionSearch.value
    if (inspectionStatus.value) params.status = inspectionStatus.value
    const res = await getInspectionPlans(params)
    inspectionPlans.value = res.results || []
    inspectionTotal.value = res.count || 0
  } catch { ElMessage.error('加载巡检计划失败') }
  finally { loadingInspectionPlans.value = false }
}

function openInspectionPlanForm(plan) {
  if (plan) {
    inspectionPlanFormTitle.value = '编辑巡检计划'
    inspectionPlanForm.value = { ...plan }
  } else {
    inspectionPlanFormTitle.value = '新建巡检计划'
    inspectionPlanForm.value = { name: '', code: '', protocol: 'snmp', cycle: 'daily', scheduled_time: '00:00', status: 'draft', description: '', check_items: [] }
  }
  inspectionPlanFormVisible.value = true
}

async function saveInspectionPlan() {
  savingPlan.value = true
  try {
    const data = { ...inspectionPlanForm.value }
    if (data.id) {
      await updateInspectionPlan(data.id, data)
    } else {
      await createInspectionPlan(data)
    }
    ElMessage.success('保存成功')
    inspectionPlanFormVisible.value = false
    loadInspectionPlans()
  } catch { ElMessage.error('保存失败') }
  finally { savingPlan.value = false }
}

async function deleteInspectionPlanById(plan) {
  try {
    await ElMessageBox.confirm(`确定删除「${plan.name}」？`, '确认', { type: 'warning' })
    await deleteInspectionPlan(plan.id)
    ElMessage.success('删除成功')
    loadInspectionPlans()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

async function doExecuteInspectionPlan(plan) {
  try {
    await ElMessageBox.confirm(`确定立即执行「${plan.name}」？`, '确认', { type: 'info' })
    const res = await executeInspectionPlan(plan.id)
    ElMessage.success(res.message || '执行成功')
  } catch (e) { if (e !== 'cancel') ElMessage.error('执行失败') }
}

async function viewInspectionTasks(plan) {
  currentInspectionPlan.value = plan
  inspectionTasksDialogVisible.value = true
  try {
    const res = await getInspectionTasks({ plan: plan.id })
    inspectionTasks.value = res.results || []
  } catch { ElMessage.error('加载任务失败') }
}

async function syncInspectionTasks() {
  ElMessage.info('同步功能待实现')
}

function getCycleLabel(cycle) {
  return { daily: '每天', weekly: '每周', monthly: '每月', quarterly: '每季度' }[cycle] || cycle
}
function getStatusType(s) {
  return { draft: 'info', active: 'success', paused: 'warning', archived: '' }[s] || ''
}
function getStatusLabel(s) {
  return { draft: '草稿', active: '启用', paused: '暂停', archived: '归档' }[s] || s
}

// ========== 调度计划 ==========
async function loadSchedulerPlans() {
  loadingSchedulerPlans.value = true
  try {
    const params = { page: schedulerPage.value, page_size: schedulerPageSize.value }
    if (schedulerPlanType.value) params.plan_type = schedulerPlanType.value
    if (schedulerEnabled.value) params.is_enabled = schedulerEnabled.value
    const res = await getSchedulerPlans(params)
    schedulerPlans.value = res.results || []
    schedulerTotal.value = res.count || 0
  } catch { ElMessage.error('加载定时任务失败') }
  finally { loadingSchedulerPlans.value = false }
}

async function openSchedulerPlanForm(plan) {
  // 加载所有巡检计划供选择
  try {
    const res = await getInspectionPlans({ page: 1, page_size: 100 })
    allInspectionPlans.value = res.results || []
  } catch {}
  if (plan) {
    schedulerPlanFormTitle.value = '编辑调度计划'
    schedulerPlanForm.value = { ...plan }
    schedulerTaskConfig.value = JSON.stringify(plan.task_config || {}, null, 2)
  } else {
    schedulerPlanFormTitle.value = '新建调度计划'
    schedulerPlanForm.value = {
      name: '', plan_type: 'inspection', inspection_plan: null,
      schedule_type: 'daily', daily_time: '09:00', weekday: 0,
      day_of_month: 1, interval_value: 1, interval_unit: 'hours',
      conflict_strategy: 'queue', is_enabled: true
    }
    schedulerTaskConfig.value = ''
  }
  schedulerPlanFormVisible.value = true
}

async function saveSchedulerPlan() {
  savingSchedulerPlan.value = true
  try {
    const f = schedulerPlanForm.value
    const data = {
      name: f.name,
      plan_type: f.plan_type,
      inspection_plan: f.inspection_plan || null,
      is_enabled: f.is_enabled,
      conflict_strategy: f.conflict_strategy,
    }
    // 调度配置
    if (f.schedule_type === 'daily') {
      data.schedule_type = 'daily'
      data.daily_time = f.daily_time || '09:00'
    } else if (f.schedule_type === 'weekly') {
      data.schedule_type = 'weekly'
      data.daily_time = f.daily_time || '09:00'
      data.weekday = f.weekday ?? 0
    } else if (f.schedule_type === 'monthly') {
      data.schedule_type = 'monthly'
      data.daily_time = f.daily_time || '09:00'
      data.day_of_month = f.day_of_month || 1
    } else if (f.schedule_type === 'interval') {
      data.schedule_type = 'interval'
      data.interval_value = f.interval_value || 1
      data.interval_unit = f.interval_unit || 'hours'
    }
    // 任务配置
    if (schedulerTaskConfig.value) {
      try { data.task_config = JSON.parse(schedulerTaskConfig.value) } catch {}
    }
    if (f.id) {
      await updateSchedulerPlan(f.id, data)
    } else {
      await createSchedulerPlan(data)
    }
    ElMessage.success('保存成功')
    schedulerPlanFormVisible.value = false
    loadSchedulerPlans()
  } catch (e) { ElMessage.error('保存失败: ' + (e.message || '')) }
  finally { savingSchedulerPlan.value = false }
}

async function doExecuteSchedulerPlan(plan) {
  try {
    await ElMessageBox.confirm(`确定立即执行「${plan.name}」？`, '确认', { type: 'info' })
    const res = await executeSchedulerPlan(plan.id)
    ElMessage.success('任务已开始执行')
  } catch (e) { if (e !== 'cancel') ElMessage.error('执行失败') }
}

async function doToggleSchedulerPlan(plan) {
  try {
    await toggleSchedulerPlan(plan.id, !plan.is_enabled)
    ElMessage.success(plan.is_enabled ? '已禁用' : '已启用')
    loadSchedulerPlans()
  } catch { ElMessage.error('操作失败') }
}

async function doDeleteSchedulerPlan(plan) {
  try {
    await ElMessageBox.confirm(`确定删除「${plan.name}」？`, '确认', { type: 'warning' })
    await deleteSchedulerPlan(plan.id)
    ElMessage.success('删除成功')
    loadSchedulerPlans()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

function getPlanTypeLabel(t) {
  return { inspection: '巡检', push: '推送', monitoring: '监控', discovery: '发现', mixed: '综合' }[t] || t
}

// ========== 巡检记录 ==========
async function loadInspectionRecords() {
  loadingRecords.value = true
  try {
    const params = { page: recordPage.value, page_size: recordPageSize.value }
    if (recordSearch.value) params.search = recordSearch.value
    if (recordStatus.value) params.status = recordStatus.value
    const res = await getInspectionRecords(params)
    inspectionRecords.value = res.results || []
    recordTotal.value = res.count || 0
  } catch { ElMessage.error('加载巡检记录失败') }
  finally { loadingRecords.value = false }
}

async function viewRecordDetail(record) {
  try {
    const res = await getInspectionRecord(record.id)
    currentRecord.value = res
    recordItems.value = res.items || []
    recordDetailDialogVisible.value = true
  } catch { ElMessage.error('加载详情失败') }
}

function getRecordStatusType(s) {
  return { RUNNING: 'info', COMPLETED: 'success', WARNING: 'warning', FAILED: 'danger' }[s] || ''
}
function getRecordStatusLabel(s) {
  return { RUNNING: '运行中', COMPLETED: '完成', WARNING: '警告', FAILED: '失败' }[s] || s
}
function getTaskStatusType(s) {
  return { pending: 'info', in_progress: 'warning', completed: 'success', failed: 'danger', cancelled: 'info' }[s] || ''
}
function getTaskStatusLabel(s) {
  return { pending: '待巡检', in_progress: '巡检中', completed: '已完成', failed: '失败', cancelled: '已取消' }[s] || s
}
function getItemResultType(r) {
  return { PASS: 'success', WARNING: 'warning', FAIL: 'danger', SKIP: 'info' }[r] || ''
}
function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}
</script>

<style scoped>
.skills-page { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
.stats-row { margin-bottom: 16px; }
.main-tabs { background: #fff; padding: 16px; border-radius: 4px; }
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; }
.template-card { cursor: pointer; margin-bottom: 12px; }
.template-card:hover { border-color: #409EFF; }
.tpl-icon { width: 48px; height: 48px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; margin-bottom: 8px; }
.tpl-icon + h4 { margin: 0 0 4px; }
.tpl-meta { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
</style>
