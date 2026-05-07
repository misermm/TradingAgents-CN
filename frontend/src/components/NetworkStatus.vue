<template>
  <div class="network-status" v-if="showStatus">
    <el-alert
      v-if="!appStore.isOnline"
      title="网络连接已断开"
      type="warning"
      :closable="false"
      show-icon
    >
      <template #default>
        <span>请检查您的网络连接</span>
      </template>
    </el-alert>

    <el-alert
      v-else-if="!appStore.apiConnected"
      title="后端服务连接失败"
      :type="retryCount > 3 ? 'error' : 'warning'"
      :closable="false"
      show-icon
    >
      <template #default>
        <span v-if="retryCount <= 3">后端服务正在启动中，请稍候...</span>
        <span v-else>无法连接到后端服务，请检查服务是否正常运行</span>
        <el-button
          type="primary"
          size="small"
          @click="retryConnection"
          :loading="retrying"
          style="margin-left: 10px;"
        >
          {{ retryCount <= 3 ? '立即检查' : '重试连接' }}
        </el-button>
      </template>
    </el-alert>

    <el-alert
      v-else-if="!appStore.apiReady"
      title="后端服务启动中..."
      type="warning"
      :closable="false"
      show-icon
    >
      <template #default>
        <div class="startup-info">
          <span>部分组件正在初始化，请稍候</span>
          <div class="component-list" v-if="pendingComponents.length > 0">
            <span
              v-for="comp in pendingComponents"
              :key="comp.name"
              class="component-tag"
              :class="comp.status"
            >
              {{ comp.label }}: {{ comp.statusText }}
            </span>
          </div>
          <el-button
            type="primary"
            size="small"
            @click="retryConnection"
            :loading="retrying"
            style="margin-left: 10px;"
          >
            刷新状态
          </el-button>
        </div>
      </template>
    </el-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const retrying = ref(false)
const retryCount = ref(0)

const COMPONENT_LABELS: Record<string, string> = {
  mongodb: 'MongoDB',
  redis: 'Redis',
  scheduler: '调度器',
}

const showStatus = computed(() => {
  return !appStore.isOnline || !appStore.apiConnected || !appStore.apiReady
})

const pendingComponents = computed(() => {
  const components = appStore.apiComponents
  if (!components || Object.keys(components).length === 0) return []
  return Object.entries(components)
    .filter(([, c]) => c.status !== 'ok')
    .map(([name, c]) => ({
      name,
      label: COMPONENT_LABELS[name] || name,
      status: c.status,
      statusText: c.status === 'unavailable' ? '未连接' : c.status === 'error' ? '异常' : c.status === 'stopped' ? '已停止' : '启动中',
    }))
})

const retryConnection = async () => {
  retrying.value = true
  try {
    await appStore.checkApiConnection()
    if (appStore.apiConnected && appStore.apiReady) {
      retryCount.value = 0
    }
  } catch (error) {
    console.error('重试连接失败:', error)
  } finally {
    retrying.value = false
  }
}

let checkInterval: number | null = null

onMounted(() => {
  const getCheckInterval = () => {
    if (retryCount.value < 3) return 5000
    if (retryCount.value < 6) return 10000
    return 30000
  }

  const scheduleCheck = () => {
    checkInterval = window.setTimeout(async () => {
      if (appStore.isOnline && (!appStore.apiConnected || !appStore.apiReady)) {
        retryCount.value++
        await appStore.checkApiConnection()
        if (!appStore.apiConnected || !appStore.apiReady) {
          scheduleCheck()
        } else {
          retryCount.value = 0
        }
      }
    }, getCheckInterval())
  }

  if (appStore.isOnline && (!appStore.apiConnected || !appStore.apiReady)) {
    scheduleCheck()
  }
})

onUnmounted(() => {
  if (checkInterval) {
    clearTimeout(checkInterval)
  }
})
</script>

<style scoped>
.network-status {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  max-width: 400px;
}

.network-status :deep(.el-alert) {
  margin-bottom: 10px;
}

.network-status :deep(.el-alert__content) {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.startup-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.component-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.component-tag {
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(230, 162, 60, 0.15);
  color: #e6a23c;
}

.component-tag.error {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.component-tag.unavailable {
  background: rgba(144, 147, 153, 0.15);
  color: #909399;
}
</style>
