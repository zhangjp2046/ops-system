<template>
  <div class="topology-page">
    <div class="header">
      <h2>网络拓扑图</h2>
      <div class="header-actions">
        <el-select
          v-model="selectedCustomer"
          placeholder="选择客户"
          style="width: 200px; margin-right: 12px"
          @change="loadTopology"
        >
          <el-option
            v-for="c in customers"
            :key="c.id"
            :label="c.customer_name"
            :value="c.id"
          />
        </el-select>
        <el-button @click="loadTopology">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="toggleLayout">
          {{ layoutMode === 'force' ? '切换到网格布局' : '切换到力导向布局' }}
        </el-button>
      </div>
    </div>

    <!-- 拓扑图容器 -->
    <el-card class="topology-card" shadow="never">
      <div class="topology-container" ref="containerRef">
        <svg ref="svgRef" class="topology-svg">
          <defs>
            <!-- 箭头标记 -->
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
            </marker>
            <!-- 选中效果 -->
            <filter id="selected-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
        </svg>

        <!-- 节点信息面板 -->
        <div v-if="selectedNode" class="node-panel">
          <div class="panel-header">
            <span>节点信息</span>
            <el-button text @click="selectedNode = null">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <div class="panel-body">
            <div class="info-row">
              <span class="label">名称:</span>
              <span class="value">{{ selectedNode.name }}</span>
            </div>
            <div class="info-row">
              <span class="label">IP:</span>
              <span class="value">{{ selectedNode.ip || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="label">类型:</span>
              <span class="value">{{ getDeviceTypeLabel(selectedNode.deviceType || selectedNode.device_type) }}</span>
            </div>
            <div class="info-row">
              <span class="label">状态:</span>
              <el-tag :type="selectedNode.online ? 'success' : 'danger'" size="small">
                {{ selectedNode.online ? '在线' : '离线' }}
              </el-tag>
            </div>
            <div class="info-row" v-if="selectedNode.metadata && selectedNode.metadata.mac">
              <span class="label">MAC:</span>
              <span class="value">{{ selectedNode.metadata.mac }}</span>
            </div>
          </div>
          <div class="panel-footer">
            <el-button
              v-if="selectedNode.type === 'asset' || selectedNode.node_type === 'asset'"
              type="primary"
              size="small"
              @click="goToAsset"
            >
              查看资产
            </el-button>
            <el-button type="danger" size="small" @click="deleteNode">
              删除节点
            </el-button>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="nodes.length === 0 && !loading" class="empty-state">
          <el-icon class="empty-icon"><Connection /></el-icon>
          <p>暂无拓扑数据</p>
          <p class="hint">请先在"资产发现"页面扫描网络并生成拓扑</p>
        </div>
      </div>

      <!-- 图例 -->
      <div class="legend">
        <div class="legend-item">
          <span class="legend-icon server"></span>
          <span>服务器</span>
        </div>
        <div class="legend-item">
          <span class="legend-icon router"></span>
          <span>路由器</span>
        </div>
        <div class="legend-item">
          <span class="legend-icon switch"></span>
          <span>交换机</span>
        </div>
        <div class="legend-item">
          <span class="legend-icon firewall"></span>
          <span>防火墙</span>
        </div>
        <div class="legend-item">
          <span class="legend-icon camera"></span>
          <span>摄像头</span>
        </div>
        <div class="legend-item">
          <span class="legend-icon unknown"></span>
          <span>其他设备</span>
        </div>
      </div>
    </el-card>

    <!-- 在线设备列表 -->
    <el-card class="devices-card" shadow="never">
      <template #header>
        <span>设备列表 ({{ filteredDevices.length }})</span>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索IP地址或名称"
          style="width: 200px; margin-left: 12px"
          clearable
        />
      </template>
      <el-table :data="filteredDevices" stripe max-height="300">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="ip" label="IP地址" width="140">
          <template #default="{ row }">
            {{ row.ip || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="deviceType" label="类型" width="100">
          <template #default="{ row }">
            {{ getDeviceTypeLabel(row.deviceType || row.device_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="online" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.online ? 'success' : 'danger'" size="small">
              {{ row.online ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" @click="focusNode(row)">定位</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import discoveryApi from '@/api/discovery'
import { getCustomerList } from '@/api/customer'

const router = useRouter()

// 状态
const loading = ref(false)
const selectedCustomer = ref(null)
const customers = ref([])
const nodes = ref([])
const links = ref([])
const layoutMode = ref('force')
const selectedNode = ref(null)
const searchKeyword = ref('')
const containerRef = ref(null)
const svgRef = ref(null)

// 力导向模拟
let simulation = null
let rafId = null

// 计算属性
const filteredDevices = computed(() => {
  if (!searchKeyword.value) return nodes.value
  const kw = searchKeyword.value.toLowerCase()
  return nodes.value.filter(
    n =>
      (n.name && n.name.toLowerCase().includes(kw)) ||
      (n.ip && n.ip.toLowerCase().includes(kw))
  )
})

// 加载客户列表
async function loadCustomers() {
  try {
    const res = await getCustomerList()
    customers.value = res.results || res.data || []
    if (customers.value.length > 0) {
      selectedCustomer.value = customers.value[0].id
    }
  } catch (e) {
    console.error('加载客户失败', e)
  }
}

// 加载拓扑数据
async function loadTopology() {
  if (!selectedCustomer.value) return

  loading.value = true
  try {
    const res = await discoveryApi.exportGraph(selectedCustomer.value)
    nodes.value = res.nodes || []
    links.value = res.links || []

    await nextTick()
    renderTopology()
  } catch (e) {
    console.error('加载拓扑失败', e)
    ElMessage.error('加载拓扑失败')
  } finally {
    loading.value = false
  }
}

// 渲染拓扑图
function renderTopology() {
  if (!svgRef.value || !containerRef.value) return

  const svg = svgRef.value
  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight - 40

  // 清除旧内容（保留 defs）
  const defs = svg.querySelector('defs')
  const defsClone = defs ? defs.cloneNode(true) : null
  svg.innerHTML = ''
  if (defsClone) svg.appendChild(defsClone)

  // 取消旧动画
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }

  if (nodes.value.length === 0) return

  // 创建节点和连线数据
  const nodeMap = new Map()
  nodes.value.forEach((n, i) => {
    // 初始化位置
    if (n.x == null || n.y == null) {
      n.x = width / 2 + (Math.random() - 0.5) * 400
      n.y = height / 2 + (Math.random() - 0.5) * 400
    }
    nodeMap.set(n.id, n)
  })

  // 绘制连线
  const linkGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  linkGroup.setAttribute('class', 'links')

  links.value.forEach(link => {
    const source = nodeMap.get(link.source)
    const target = nodeMap.get(link.target)
    if (!source || !target) return

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
    line.setAttribute('x1', source.x)
    line.setAttribute('y1', source.y)
    line.setAttribute('x2', target.x)
    line.setAttribute('y2', target.y)
    line.setAttribute('stroke', '#ccc')
    line.setAttribute('stroke-width', '2')
    line.setAttribute('marker-end', 'url(#arrowhead)')
    line.setAttribute('data-link-id', link.id)
    linkGroup.appendChild(line)
  })
  svg.appendChild(linkGroup)

  // 绘制节点
  const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  nodeGroup.setAttribute('class', 'nodes')

  nodes.value.forEach(node => {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    g.setAttribute('class', 'node')
    g.setAttribute('data-node-id', node.id)
    g.style.cursor = 'pointer'

    // 图标背景
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
    const r = 28
    circle.setAttribute('cx', node.x)
    circle.setAttribute('cy', node.y)
    circle.setAttribute('r', r)
    circle.setAttribute('fill', getNodeColor(node.deviceType || node.device_type || 'unknown'))
    circle.setAttribute('stroke', '#fff')
    circle.setAttribute('stroke-width', '3')

    // 状态指示
    if (!node.online) {
      circle.setAttribute('opacity', '0.5')
    }

    // 文字
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    text.setAttribute('x', node.x)
    text.setAttribute('y', node.y)
    text.setAttribute('text-anchor', 'middle')
    text.setAttribute('dominant-baseline', 'middle')
    text.setAttribute('fill', '#fff')
    text.setAttribute('font-size', '18')
    text.setAttribute('font-weight', 'bold')
    text.textContent = getNodeIcon(node.deviceType || node.device_type || 'unknown')

    // IP标签
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    label.setAttribute('x', node.x)
    label.setAttribute('y', node.y + r + 16)
    label.setAttribute('text-anchor', 'middle')
    label.setAttribute('fill', '#666')
    label.setAttribute('font-size', '12')
    label.textContent = node.ip || node.name || ''

    g.appendChild(circle)
    g.appendChild(text)
    g.appendChild(label)
    nodeGroup.appendChild(g)

    // 拖拽事件（统一在 SVG 容器处理，g 元素只做 hit-test）
    g.style.pointerEvents = 'all'
    g.addEventListener('pointerdown', e => {
      e.stopPropagation()
      g._dragStartX = e.clientX
      g._dragStartY = e.clientY
      g._dragNodeX = node.x
      g._dragNodeY = node.y
      g._isDragging = false
      svg.setPointerCapture(e.pointerId)
    })
  })

  // SVG 统一处理指针移动和释放
  svg.addEventListener('pointermove', e => {
    const nodeEls = svg.querySelectorAll('.node')
    let hitNode = null
    nodeEls.forEach(el => {
      if (el.contains(e.target)) hitNode = el
    })
    if (!hitNode) return
    const g = hitNode
    if (!g._dragStartX && g._dragStartX !== 0) return
    const dx = e.clientX - g._dragStartX
    const dy = e.clientY - g._dragStartY
    if (!g._isDragging && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
      g._isDragging = true
    }
    if (!g._isDragging) return
    const newX = g._dragNodeX + dx
    const newY = g._dragNodeY + dy
    const nodeId = parseInt(hitNode.getAttribute('data-node-id'))
    const n = nodes.value.find(n => n.id === nodeId)
    if (!n) return
    n.x = newX
    n.y = newY
    const circle = hitNode.querySelector('circle')
    const texts = hitNode.querySelectorAll('text')
    if (circle) { circle.setAttribute('cx', newX); circle.setAttribute('cy', newY) }
    if (texts[0]) { texts[0].setAttribute('x', newX); texts[0].setAttribute('y', newY) }
    if (texts[1]) { texts[1].setAttribute('x', newX); texts[1].setAttribute('y', newY + 28 + 16) }
    updateLinks()
  })

  svg.addEventListener('pointerup', e => {
    const nodeEls = svg.querySelectorAll('.node')
    let hitNode = null
    nodeEls.forEach(el => {
      if (el.contains(e.target)) hitNode = el
    })
    if (hitNode && hitNode._isDragging) {
      const nodeId = parseInt(hitNode.getAttribute('data-node-id'))
      const n = nodes.value.find(n => n.id === nodeId)
      if (n) saveNodePosition(n)
    } else if (hitNode && !hitNode._isDragging) {
      const nodeId = parseInt(hitNode.getAttribute('data-node-id'))
      const n = nodes.value.find(n => n.id === nodeId)
      if (n) {
        selectedNode.value = n
        highlightNode(n.id)
      }
    }
    nodeEls.forEach(el => {
      el._isDragging = false
      el._dragStartX = null
      el._dragStartY = null
    })
    svg.releasePointerCapture(e.pointerId)
  })
  svg.appendChild(nodeGroup)

  // 如果是力导向模式，启动动画
  if (layoutMode.value === 'force') {
    runForceLayout(width, height)
  }
}

// 仅渲染节点（不走力导向，用于网格布局等场景）
function renderNodesOnly() {
  const svg = svgRef.value
  if (!svg || !containerRef.value) return

  const defs = svg.querySelector('defs')
  const defsClone = defs ? defs.cloneNode(true) : null
  svg.innerHTML = ''
  if (defsClone) svg.appendChild(defsClone)

  if (nodes.value.length === 0) return

  const nodeMap = new Map()
  nodes.value.forEach(n => nodeMap.set(n.id, n))

  // 绘制连线
  const linkGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  linkGroup.setAttribute('class', 'links')
  links.value.forEach(link => {
    const source = nodeMap.get(link.source)
    const target = nodeMap.get(link.target)
    if (!source || !target) return
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
    line.setAttribute('x1', source.x); line.setAttribute('y1', source.y)
    line.setAttribute('x2', target.x); line.setAttribute('y2', target.y)
    line.setAttribute('stroke', '#ccc'); line.setAttribute('stroke-width', '2')
    line.setAttribute('marker-end', 'url(#arrowhead)')
    linkGroup.appendChild(line)
  })
  svg.appendChild(linkGroup)

  // 绘制节点
  const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  nodeGroup.setAttribute('class', 'nodes')

  nodes.value.forEach(node => {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    g.setAttribute('class', 'node')
    g.setAttribute('data-node-id', node.id)
    g.style.cursor = 'pointer'

    const r = 28
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
    circle.setAttribute('cx', node.x); circle.setAttribute('cy', node.y)
    circle.setAttribute('r', r)
    circle.setAttribute('fill', getNodeColor(node.deviceType || node.device_type || 'unknown'))
    circle.setAttribute('stroke', '#fff'); circle.setAttribute('stroke-width', '3')
    if (!node.online) circle.setAttribute('opacity', '0.5')

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    text.setAttribute('x', node.x); text.setAttribute('y', node.y)
    text.setAttribute('text-anchor', 'middle'); text.setAttribute('dominant-baseline', 'middle')
    text.setAttribute('fill', '#fff'); text.setAttribute('font-size', '18')
    text.setAttribute('font-weight', 'bold')
    text.textContent = getNodeIcon(node.deviceType || node.device_type || 'unknown')

    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    label.setAttribute('x', node.x); label.setAttribute('y', node.y + r + 16)
    label.setAttribute('text-anchor', 'middle'); label.setAttribute('fill', '#666')
    label.setAttribute('font-size', '12')
    label.textContent = node.ip || node.name || ''

    g.appendChild(circle); g.appendChild(text); g.appendChild(label)
    nodeGroup.appendChild(g)
    g.style.pointerEvents = 'all'
    g.addEventListener('pointerdown', e => {
      e.stopPropagation()
      g._dragStartX = e.clientX; g._dragStartY = e.clientY
      g._dragNodeX = node.x; g._dragNodeY = node.y
      g._isDragging = false
      svg.setPointerCapture(e.pointerId)
    })
  })

  svg.addEventListener('pointermove', e => {
    const nodeEls = svg.querySelectorAll('.node')
    let hitNode = null
    nodeEls.forEach(el => { if (el.contains(e.target)) hitNode = el })
    if (!hitNode) return
    if (!hitNode._dragStartX && hitNode._dragStartX !== 0) return
    const dx = e.clientX - hitNode._dragStartX
    const dy = e.clientY - hitNode._dragStartY
    if (!hitNode._isDragging && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) hitNode._isDragging = true
    if (!hitNode._isDragging) return
    const newX = hitNode._dragNodeX + dx, newY = hitNode._dragNodeY + dy
    const nodeId = parseInt(hitNode.getAttribute('data-node-id'))
    const n = nodes.value.find(n => n.id === nodeId)
    if (!n) return
    n.x = newX; n.y = newY
    const circle = hitNode.querySelector('circle'), texts = hitNode.querySelectorAll('text')
    if (circle) { circle.setAttribute('cx', newX); circle.setAttribute('cy', newY) }
    if (texts[0]) { texts[0].setAttribute('x', newX); texts[0].setAttribute('y', newY) }
    if (texts[1]) { texts[1].setAttribute('x', newX); texts[1].setAttribute('y', newY + 28 + 16) }
    updateLinks()
  })

  svg.addEventListener('pointerup', e => {
    const nodeEls = svg.querySelectorAll('.node')
    let hitNode = null
    nodeEls.forEach(el => { if (el.contains(e.target)) hitNode = el })
    if (hitNode && hitNode._isDragging) {
      const n = nodes.value.find(n => n.id === parseInt(hitNode.getAttribute('data-node-id')))
      if (n) saveNodePosition(n)
    } else if (hitNode && !hitNode._isDragging) {
      const n = nodes.value.find(n => n.id === parseInt(hitNode.getAttribute('data-node-id')))
      if (n) { selectedNode.value = n; highlightNode(n.id) }
    }
    nodeEls.forEach(el => { el._isDragging = false; el._dragStartX = null })
    svg.releasePointerCapture(e.pointerId)
  })

  svg.appendChild(nodeGroup)
}

// 更新连线位置
function updateLinks() {
  const svg = svgRef.value
  const linkGroup = svg.querySelector('.links')
  if (!linkGroup) return

  const nodeMap = new Map()
  nodes.value.forEach(n => nodeMap.set(n.id, n))

  const lines = linkGroup.querySelectorAll('line')
  links.value.forEach((link, i) => {
    const source = nodeMap.get(link.source)
    const target = nodeMap.get(link.target)
    if (source && target && lines[i]) {
      lines[i].setAttribute('x1', source.x)
      lines[i].setAttribute('y1', source.y)
      lines[i].setAttribute('x2', target.x)
      lines[i].setAttribute('y2', target.y)
    }
  })
}

// 力导向布局
function runForceLayout(width, height) {
  if (simulation) simulation.stop()
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }

  const nodeMap = new Map()
  nodes.value.forEach(n => nodeMap.set(n.id, n))

  // 构建副本数据用于力导向计算
  const nodesCopy = nodes.value.map(n => ({ ...n }))
  const linksCopy = links.value.map(l => ({
    source: nodeMap.get(l.source) || l.source,
    target: nodeMap.get(l.target) || l.target
  })).filter(l => l.source && l.target)

  // 节点ID到索引的映射
  const nodeIndexMap = new Map(nodesCopy.map((n, i) => [n.id, i]))

  simulation = {
    nodes: nodesCopy,
    links: linksCopy
  }

  let alpha = 1
  const tick = () => {
    if (alpha < 0.01) {
      rafId = null
      // 布局结束后把位置写回 reactive state
      nodesCopy.forEach(nc => {
        const node = nodes.value.find(n => n.id === nc.id)
        if (node) {
          node.x = nc.x
          node.y = nc.y
        }
      })
      return
    }

    // 节点间斥力
    for (let i = 0; i < nodesCopy.length; i++) {
      for (let j = i + 1; j < nodesCopy.length; j++) {
        const dx = nodesCopy[j].x - nodesCopy[i].x
        const dy = nodesCopy[j].y - nodesCopy[i].y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = -500 / (dist * dist)
        const fx = (dx / dist) * force * alpha
        const fy = (dy / dist) * force * alpha
        nodesCopy[i].x += fx
        nodesCopy[i].y += fy
        nodesCopy[j].x -= fx
        nodesCopy[j].y -= fy
      }
    }

    // 连线引力
    linksCopy.forEach(link => {
      if (!link.source || !link.target) return
      const dx = link.target.x - link.source.x
      const dy = link.target.y - link.source.y
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const force = (dist - 150) * 0.05 * alpha
      const fx = (dx / dist) * force
      const fy = (dy / dist) * force
      link.source.x += fx
      link.source.y += fy
      link.target.x -= fx
      link.target.y -= fy
    })

    // 边界约束
    const padding = 50
    nodesCopy.forEach(n => {
      n.x = Math.max(padding, Math.min(width - padding, n.x))
      n.y = Math.max(padding, Math.min(height - padding, n.y))
    })

    alpha *= 0.95

    // 更新视图（使用 simulation.nodes 数据）
    updateNodePositions()
    updateLinks()

    if (alpha > 0.01) {
      rafId = requestAnimationFrame(tick)
    }
  }

  rafId = requestAnimationFrame(tick)
}

// 更新节点位置
function updateNodePositions() {
  const svg = svgRef.value
  const nodeGroups = svg.querySelectorAll('.node')
  const nodeMap = new Map(simulation.nodes.map(n => [n.id, n]))

  nodeGroups.forEach(g => {
    const id = parseInt(g.getAttribute('data-node-id'))
    const node = nodeMap.get(id)
    if (!node) return

    const circle = g.querySelector('circle')
    const texts = g.querySelectorAll('text')
    if (circle) {
      circle.setAttribute('cx', node.x)
      circle.setAttribute('cy', node.y)
    }
    texts.forEach((t, i) => {
      if (i === 0) {
        // 图标
        t.setAttribute('x', node.x)
        t.setAttribute('y', node.y)
      } else if (i === 1) {
        // IP标签
        t.setAttribute('x', node.x)
        t.setAttribute('y', node.y + 28 + 16)
      }
    })
  })
}

// 保存节点位置
async function saveNodePosition(node) {
  try {
    await discoveryApi.updateNodePosition(node.id, Math.round(node.x), Math.round(node.y))
  } catch (e) {
    console.error('保存位置失败', e)
  }
}

// 高亮选中节点
function highlightNode(nodeId) {
  const svg = svgRef.value
  svg.querySelectorAll('.node').forEach(g => {
    const id = parseInt(g.getAttribute('data-node-id'))
    const circle = g.querySelector('circle')
    if (id === nodeId) {
      circle.setAttribute('stroke', '#409EFF')
      circle.setAttribute('stroke-width', '4')
      circle.setAttribute('filter', 'url(#selected-glow)')
    } else {
      circle.setAttribute('stroke', '#fff')
      circle.setAttribute('stroke-width', '3')
      circle.removeAttribute('filter')
    }
  })
}

// 切换布局
function toggleLayout() {
  layoutMode.value = layoutMode.value === 'force' ? 'grid' : 'force'
  if (!containerRef.value) return
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight - 40

  // 取消旧动画
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  if (simulation) simulation.stop()

  if (layoutMode.value === 'grid') {
    // 网格布局
    const cols = Math.ceil(Math.sqrt(nodes.value.length)) || 1
    const padding = 80
    const cellW = (width - padding * 2) / cols
    const cellH = 120

    nodes.value.forEach((n, i) => {
      const col = i % cols
      const row = Math.floor(i / cols)
      n.x = padding + col * cellW + cellW / 2
      n.y = padding + row * cellH + cellH / 2
    })

    // 只重新渲染，不启动力导向
    renderNodesOnly()
  } else {
    runForceLayout(width, height)
  }
}

// 定位节点
function focusNode(node) {
  selectedNode.value = node
  highlightNode(node.id)
}

// 查看资产
function goToAsset() {
  if (!selectedNode.value) return
  const assetId = selectedNode.value.assetId || selectedNode.value.asset_id
  if (assetId) {
    router.push(`/assets/${assetId}`)
  }
}

// 删除节点
async function deleteNode() {
  if (!selectedNode.value) return
  try {
    await ElMessageBox.confirm('确定要删除这个拓扑节点吗?', '删除确认', { type: 'warning' })
    // TODO: 调用删除API
    ElMessage.success('节点已删除')
    selectedNode.value = null
    loadTopology()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除失败', e)
    }
  }
}

// 辅助函数
function getNodeColor(type) {
  const colors = {
    server: '#409EFF',
    router: '#67C23A',
    switch: '#E6A23C',
    firewall: '#F56C6C',
    loadbalancer: '#9B59B6',
    storage: '#1ABC9C',
    printer: '#95A5A6',
    camera: '#FF9800',
    access_point: '#00BCD4',
    workstation: '#607D8B',
    virtual: '#8BC34A',
    cloud: '#3F51B5',
    unknown: '#909399'
  }
  return colors[type] || colors.unknown
}

function getNodeIcon(type) {
  const icons = {
    server: '🖥',
    router: '📡',
    switch: '🔌',
    firewall: '🔥',
    loadbalancer: '⚖',
    storage: '💾',
    printer: '🖨',
    camera: '📷',
    access_point: '📶',
    workstation: '💻',
    virtual: '☁',
    cloud: '🌐',
    unknown: '❓'
  }
  return icons[type] || icons.unknown
}

function getDeviceTypeLabel(type) {
  const map = {
    server: '服务器',
    router: '路由器',
    switch: '交换机',
    firewall: '防火墙',
    loadbalancer: '负载均衡器',
    storage: '存储设备',
    printer: '打印机',
    camera: '摄像头',
    access_point: '无线AP',
    workstation: '工作站',
    virtual: '虚拟机',
    cloud: '云资源',
    network: '网络设备',
    unknown: '未知'
  }
  return map[type] || type || '未知'
}

// 生命周期
onMounted(() => {
  loadCustomers()
})

onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId)
  if (simulation) simulation.stop()
})
</script>

<style scoped>
.topology-page {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
}

.topology-card {
  margin-bottom: 16px;
  position: relative;
}

.topology-container {
  height: 550px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
  border-radius: 4px;
}

.topology-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.node {
  transition: opacity 0.3s;
}

.node:hover {
  opacity: 0.85;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state p {
  margin: 8px 0;
}

.empty-state .hint {
  font-size: 13px;
  color: #bbb;
}

.node-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 260px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  font-weight: 500;
}

.panel-body {
  padding: 16px;
}

.info-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.info-row .label {
  width: 60px;
  color: #666;
  font-size: 13px;
}

.info-row .value {
  flex: 1;
  font-size: 13px;
  word-break: break-all;
}

.panel-footer {
  padding: 12px 16px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 8px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px 16px;
  border-top: 1px solid #eee;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666;
}

.legend-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-block;
}

.legend-icon.server {
  background: #409EFF;
}
.legend-icon.router {
  background: #67C23A;
}
.legend-icon.switch {
  background: #E6A23C;
}
.legend-icon.firewall {
  background: #F56C6C;
}
.legend-icon.camera {
  background: #FF9800;
}
.legend-icon.unknown {
  background: #909399;
}

.devices-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
