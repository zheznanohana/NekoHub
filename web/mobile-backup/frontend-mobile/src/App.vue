<template>
  <div id="app" :class="{ 'dark-mode': darkMode }">
    <router-view />
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'App',
  setup() {
    const darkMode = ref(false)

    const checkDarkMode = () => {
      darkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }

    onMounted(() => {
      checkDarkMode()
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', checkDarkMode)
    })

    onUnmounted(() => {
      window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', checkDarkMode)
    })

    return { darkMode }
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
}

/* 移动端优化 */
* {
  -webkit-tap-highlight-color: transparent;
}

/* 防止双击缩放 */
@media (max-width: 768px) {
  * {
    touch-action: manipulation;
  }
  
  input, select, textarea {
    font-size: 16px !important; /* 防止 iOS 缩放 */
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
</style>
