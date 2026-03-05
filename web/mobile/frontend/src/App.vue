<template>
  <div class="mobile-optimized">
    <!-- 启动画面 -->
    <SplashScreen v-if="showSplash" @ready="onSplashReady" />
    
    <!-- 主内容 -->
    <div v-show="!showSplash" class="main-wrapper">
      <router-view />
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import SplashScreen from './components/SplashScreen.vue'

export default {
  name: 'App',
  components: {
    SplashScreen
  },
  setup() {
    const showSplash = ref(true)

    const onSplashReady = () => {
      showSplash.value = false
    }

    return { showSplash, onSplashReady }
  }
}
</script>

<style>
/* 全局重置 */
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f5f7fa;
}

/* 移动端优化 */
* {
  -webkit-tap-highlight-color: transparent;
  box-sizing: border-box;
}

/* 防止双击缩放 */
@media (max-width: 768px) {
  * {
    touch-action: manipulation;
  }
  
  input, select, textarea {
    font-size: 16px !important; /* 防止 iOS 缩放 */
  }
  
  button, a {
    min-height: 44px; /* 最小触摸区域 */
    min-width: 44px;
  }
}

/* 深色模式变量 */
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --text-primary: #333333;
  --text-secondary: #666666;
  --border-color: #e0e0e0;
  --primary-color: #409eff;
  --success-color: #67c23a;
  --warning-color: #e6a23c;
  --danger-color: #f56c6c;
  --info-color: #909399;
}

/* 深色模式 */
.dark-mode {
  --bg-primary: #1a1a1a;
  --bg-secondary: #2d2d2d;
  --text-primary: #ffffff;
  --text-secondary: #b0b0b0;
  --border-color: #404040;
}

.dark-mode body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

/* 安全区域适配（iPhone 刘海屏） */
@supports (padding-top: env(safe-area-inset-top)) {
  body {
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}

/* 加载动画 */
.loading-spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 淡入动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 滑动动画 */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from {
  transform: translateX(-20px);
  opacity: 0;
}

.slide-leave-to {
  transform: translateX(20px);
  opacity: 0;
}

/* 卡片阴影 */
.card-shadow {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

.dark-mode .card-shadow {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.3);
}

/* 触摸反馈 */
.touch-feedback:active {
  opacity: 0.7;
  transform: scale(0.98);
  transition: all 0.1s ease;
}

/* 主内容区 */
.main-wrapper {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch; /* iOS 平滑滚动 */
}
</style>
