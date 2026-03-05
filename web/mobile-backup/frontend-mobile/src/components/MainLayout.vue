<template>
  <div class="main-layout">
    <!-- 移动端顶部导航 -->
    <el-header class="mobile-header" v-if="isMobile">
      <div class="mobile-header-left">
        <el-icon :size="24" color="#409EFF"><Monitor /></el-icon>
        <span class="app-title">NekoHub</span>
      </div>
      <div class="mobile-header-right">
        <el-dropdown @command="handleCommand" trigger="click">
          <span class="user-avatar">
            <el-avatar :size="32" :style="{ backgroundColor: '#409EFF' }">
              <el-icon><User /></el-icon>
            </el-avatar>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- 侧边栏（桌面端） -->
    <el-aside width="220px" class="sidebar" v-show="!isMobile">
      <div class="logo">
        <el-icon :size="28" color="#409EFF"><Monitor /></el-icon>
        <span>NekoHub</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#ffffff"
        text-color="#606266"
        active-text-color="#409EFF"
        :unique-opened="true"
      >
        <el-menu-item index="/inbox">
          <el-icon><Message /></el-icon>
          <span>收件箱</span>
        </el-menu-item>
        
        <el-menu-item index="/ai-chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-menu-item>
        
        <el-menu-item index="/tasks">
          <el-icon><Calendar /></el-icon>
          <span>自动化任务</span>
        </el-menu-item>
        
        <el-menu-item index="/forward">
          <el-icon><Promotion /></el-icon>
          <span>通知转发</span>
        </el-menu-item>
        
        <el-menu-item index="/rss">
          <el-icon><Link /></el-icon>
          <span>RSS 订阅</span>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 底部导航栏（移动端） -->
    <el-footer class="mobile-footer" v-if="isMobile">
      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        router
        background-color="#ffffff"
        text-color="#606266"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/inbox">
          <el-icon><Message /></el-icon>
          <span>收件箱</span>
        </el-menu-item>
        
        <el-menu-item index="/ai-chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI</span>
        </el-menu-item>
        
        <el-menu-item index="/tasks">
          <el-icon><Calendar /></el-icon>
          <span>任务</span>
        </el-menu-item>
        
        <el-menu-item index="/rss">
          <el-icon><Link /></el-icon>
          <span>RSS</span>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </el-footer>
    
    <!-- 主内容区 -->
    <el-container class="main-container">
      <el-header class="header" v-show="!isMobile">
        <div class="header-left">
          <h2>{{ pageTitle }}</h2>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :style="{ backgroundColor: '#409EFF' }">
                <el-icon><User /></el-icon>
              </el-avatar>
              <span>{{ username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content" :class="{ 'mobile-content': isMobile }">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script>
export default {
  name: 'MainLayout',
  data() {
    return {
      username: localStorage.getItem('username') || 'Admin',
      isMobile: window.innerWidth <= 768
    }
  },
  mounted() {
    window.addEventListener('resize', this.handleResize)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
  },
  computed: {
    activeMenu() {
      return this.$route.path
    },
    pageTitle() {
      const titles = {
        '/inbox': '收件箱',
        '/ai-chat': 'AI 助手',
        '/tasks': '自动化任务',
        '/forward': '通知转发',
        '/rss': 'RSS 订阅',
        '/settings': '系统设置'
      }
      return titles[this.$route.path] || 'NekoHub'
    }
  },
  methods: {
    handleResize() {
      this.isMobile = window.innerWidth <= 768
    },
    handleCommand(command) {
      if (command === 'password') {
        this.showPasswordDialog()
      } else if (command === 'logout') {
        this.$confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          localStorage.removeItem('token')
          localStorage.removeItem('username')
          this.$message.success('已退出登录')
          this.$router.push('/login')
        }).catch(() => {})
      }
    },
    showPasswordDialog() {
      this.$prompt('请输入新密码', '修改密码', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /.{6,}/,
        inputErrorMessage: '密码至少 6 位',
        inputType: 'password'
      }).then(async ({ value }) => {
        try {
          const token = localStorage.getItem('token')
          const res = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
              'Authorization': 'Bearer ' + token,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ new_password: value })
          })
          if (res.ok) {
            this.$message.success('密码修改成功，请重新登录')
            localStorage.removeItem('token')
            localStorage.removeItem('username')
            this.$router.push('/login')
          } else {
            this.$message.error('修改失败')
          }
        } catch (e) {
          this.$message.error('网络错误')
        }
      }).catch(() => {})
    }
  }
}
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  background-color: #f5f7fa;
}

/* 桌面端侧边栏 */
.sidebar {
  background-color: #ffffff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  color: #409EFF;
  font-size: 20px;
  font-weight: bold;
  border-bottom: 1px solid #e4e7ed;
}

.el-menu {
  border-right: none;
  flex: 1;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 桌面端头部 */
.header {
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
}

.header-left h2 {
  color: #303133;
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #606266;
}

/* 主内容区 */
.main-content {
  background-color: #f5f7fa;
  padding: 24px;
  overflow-y: auto;
}

/* 移动端顶部导航 */
.mobile-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 50px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.mobile-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: #409EFF;
}

.user-avatar {
  cursor: pointer;
}

/* 移动端底部导航 */
.mobile-footer {
  background-color: #ffffff;
  border-top: 1px solid #e4e7ed;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  z-index: 1000;
}

.mobile-footer .el-menu {
  display: flex;
  justify-content: space-around;
  border-right: none;
}

.mobile-footer .el-menu-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 8px 0;
}

.mobile-footer .el-menu-item span {
  font-size: 12px;
  margin-top: 4px;
}

/* 移动端内容区适配 */
.mobile-content {
  padding: 16px !important;
  padding-top: 66px !important;
  padding-bottom: 76px !important;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
  
  .header {
    display: none;
  }
  
  .main-content {
    padding: 16px;
  }
}
</style>
