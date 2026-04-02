<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '200px'" class="aside">
      <div class="logo">
        <span v-if="!isCollapsed">运维系统</span>
        <span v-else>运维</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        class="menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        
        <el-menu-item index="/assets">
          <el-icon><Box /></el-icon>
          <template #title>资产管理</template>
        </el-menu-item>

        <el-menu-item index="/monitoring">
          <el-icon><Monitor /></el-icon>
          <template #title>监控中心</template>
        </el-menu-item>

        <el-menu-item index="/monitoring/alerts">
          <el-icon><Bell /></el-icon>
          <template #title>告警中心</template>
        </el-menu-item>

        <el-sub-menu index="/inspection">
          <template #title>
            <el-icon><Calendar /></el-icon>
            <span>巡检管理</span>
          </template>
          <el-menu-item index="/inspection/plans">巡检计划</el-menu-item>
          <el-menu-item index="/inspection/records">巡检记录</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/scheduler">
          <el-icon><Timer /></el-icon>
          <template #title>定时任务</template>
        </el-menu-item>

        <el-menu-item index="/monitor-test">
          <el-icon><Tools /></el-icon>
          <template #title>采集测试</template>
        </el-menu-item>

        <el-menu-item index="/system">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-button
            :icon="isCollapsed ? 'Expand' : 'Fold'"
            text
            @click="toggleSidebar"
          />
        </div>
        
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ userStore.fullName || userStore.username }}</span>
              <el-icon class="arrow"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="settings">系统设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 内容区 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessageBox, ElMessage } from 'element-plus'
import { 
  Odometer, OfficeBuilding, Box, Monitor, Bell,
  User, Lock, ArrowDown, Calendar, Document, Tickets, Tools, Timer, Setting
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapsed = ref(false)

const activeMenu = computed(() => route.path)

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
}

async function handleCommand(command) {
  switch (command) {
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          type: 'warning'
        })
        await userStore.logoutAction()
        router.push('/login')
        ElMessage.success('已退出登录')
      } catch {
        // 取消操作
      }
      break
    case 'profile':
      ElMessage.info('功能开发中')
      break
    case 'settings':
      ElMessage.info('功能开发中')
      break
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background: #304156;
  transition: width 0.3s;
  overflow-x: hidden;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: white;
  font-size: 18px;
  font-weight: bold;
  background: #263445;
  border-bottom: 1px solid #3d4a5c;
}

.menu {
  border-right: none;
  background: transparent;
}

.menu:not(.el-menu--collapse) {
  width: 200px;
}

:deep(.el-menu-item) {
  color: #bfcbd9;
}

:deep(.el-menu-item:hover),
:deep(.el-menu-item.is-active) {
  background: #263445 !important;
  color: #409eff !important;
}

.header {
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  font-size: 14px;
  color: #333;
}

.arrow {
  color: #999;
}

.main {
  background: #f0f2f5;
  padding: 20px;
}
</style>