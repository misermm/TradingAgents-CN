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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const retrying = ref(false)
const retryCount = ref(0)

const showStatus = computed(() => {
  return !appStore.isOnline || !appStore.apiConnected
})

const retryConnection = async () => {
  retrying.value = true
  try {
    await appStore.checkApiConnection()
    if (appStore.apiConnected) {
      retryCount.value = 0
    }
  } catch (error) {
    console.error('❌ 重试连接失败:', error)
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
      if (appStore.isOnline && !appStore.apiConnected) {
        retryCount.value++
        await appStore.checkApiConnection()
        if (!appStore.apiConnected) {
          scheduleCheck()
        } else {
          retryCount.value = 0
        }
      }
    }, getCheckInterval())
  }

  if (appStore.isOnline && !appStore.apiConnected) {
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
</style>
