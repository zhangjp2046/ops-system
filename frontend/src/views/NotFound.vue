<template>
  <div class="not-found">
    <div class="content">
      <h1>404</h1>
      <p>页面不存在</p>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<style scoped>
.not-found {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f0f2f5;
}

.content {
  text-align: center;
}

h1 {
  font-size: 120px;
  font-weight: bold;
  color: #409eff;
  margin: 0;
}

p {
  font-size: 24px;
  color: #666;
  margin: 20px 0;
}
</style>