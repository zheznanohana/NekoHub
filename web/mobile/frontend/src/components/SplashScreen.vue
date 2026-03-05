<template>
  <div class="splash-screen" v-if="show">
    <div class="splash-content">
      <div class="logo-animation">
        <el-icon :size="80" color="#409EFF" class="pulse">
          <Monitor />
        </el-icon>
      </div>
      <h1 class="app-name">NekoHub</h1>
      <p class="tagline">现代化的任务管理平台</p>
      <div class="loading-bar">
        <div class="loading-progress" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="loading-text">加载中... {{ progress }}%</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'SplashScreen',
  props: {
    duration: {
      type: Number,
      default: 2000
    }
  },
  emits: ['ready'],
  setup(props, { emit }) {
    const show = ref(true)
    const progress = ref(0)

    onMounted(() => {
      const interval = setInterval(() => {
        progress.value += 10
        if (progress.value >= 100) {
          clearInterval(interval)
          setTimeout(() => {
            show.value = false
            emit('ready')
          }, 300)
        }
      }, props.duration / 10)
    })

    return { show, progress }
  }
}
</script>

<style scoped>
.splash-screen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.splash-content {
  text-align: center;
  color: white;
}

.logo-animation {
  margin-bottom: 24px;
}

.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

.app-name {
  font-size: 36px;
  font-weight: bold;
  margin: 0 0 8px 0;
}

.tagline {
  font-size: 16px;
  opacity: 0.9;
  margin: 0 0 32px 0;
}

.loading-bar {
  width: 200px;
  height: 4px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  margin: 0 auto 12px;
  overflow: hidden;
}

.loading-progress {
  height: 100%;
  background: white;
  border-radius: 2px;
  transition: width 0.1s ease;
}

.loading-text {
  font-size: 14px;
  opacity: 0.8;
  margin: 0;
}
</style>
