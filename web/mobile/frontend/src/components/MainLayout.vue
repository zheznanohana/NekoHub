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
            <el-avatar :size="36" :style="{ backgroundColor: '#409EFF' }">
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
    <el-aside width="240px" class="sidebar" v-show="!isMobile">
      <div class="logo">
        <el-icon :size="32" color="#409EFF"><Monitor /></el-icon>
        <span>NekoHub</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#ffffff"
        text-color="#606266"
        active-text-color="#409EFF"
        :unique-opened="true"
        class="sidebar-menu"
      >
        <el-menu-item index="/inbox">
          <el-icon><Message /></el-icon>
          <span>收件箱</span>
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
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
      
      <!-- 侧边栏底部信息 -->
      <div class="sidebar-footer">
        <div class="version-info">
          <span>v1.0.0</span>
          <span class="status-dot"></span>
        </div>
      </div>
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
        class="mobile-nav-menu"
      >
        <el-menu-item index="/inbox" class="nav-item">
          <el-icon :size="22"><Message /></el-icon>
          <span>收件箱</span>
          <span v-if="unreadCount > 0" class="mobile-badge">{{ unreadCount }}</span>
        </el-menu-item>
        
        <el-menu-item index="/ai-chat" class="nav-item">
          <el-icon :size="22"><ChatDotRound /></el-icon>
          <span>AI</span>
        </el-menu-item>
        
        <el-menu-item index="/tasks" class="nav-item">
          <el-icon :size="22"><Calendar /></el-icon>
          <span>任务</span>
        </el-menu-item>
        
        <el-menu-item index="/rss" class="nav-item">
          <el-icon :size="22"><Link /></el-icon>
          <span>RSS</span>
        </el-menu-item>
        
        <el-menu-item index="/settings" class="nav-item">
          <el-icon :size="22"><Setting /></el-icon>
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
          <span class="server-status">
            <span class="status-dot"></span>
            <span>在线</span>
          </span>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="36" :style="{ backgroundColor: '#409EFF' }">
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
      isMobile: window.innerWidth <= 768,
      unreadCount: 0
    }
  },
  mounted() {
    window.addEventListener('resize', this.handleResize)
    this.checkUnreadMessages()
    // 每 30 秒检查未读消息
    this.unreadInterval = setInterval(this.checkUnreadMessages, 30000)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
    if (this.unreadInterval) {
      clearInterval(this.unreadInterval)
    }
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
    checkUnreadMessages() {
      // TODO: 从 API 获取未读消息数
      this.unreadCount = 0
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
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  color: #409EFF;
  font-size: 22px;
  font-weight: bold;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-menu {
  border-right: none;
  flex: 1;
  padding: 8px 0;
}

.sidebar-menu .el-menu-item {
  height: 50px;
  margin: 4px 8px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.sidebar-menu .el-menu-item:hover {
  background-color: #f5f7fa;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #ecf5ff;
  color: #409EFF;
}

.sidebar-menu .badge {
  position: absolute;
  right: 16px;
  background-color: #f56c6c;
  color: white;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  background-color: #fafafa;
}

.version-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}

.status-dot {
  width: 8px;
  height: 8px;
  background-color: #67c23a;
  border-radius: 50%;
  display: inline-block;
}

/* 桌面端头部 */
.header {
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
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

.server-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #67c23a;
  padding: 6px 12px;
  background-color: #f0f9ff;
  border-radius: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #606266;
  padding: 6px 12px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.user-info:hover {
  background-color: #f5f7fa;
}

/* 主内容区 */
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-content {
  background-color: #f5f7fa;
  padding: 24px;
  overflow-y: auto;
}

/* 移动端顶部导航 */
.mobile-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 56px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.mobile-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: white;
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
  height: 64px;
  z-index: 1000;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.05);
}

.mobile-nav-menu {
  display: flex;
  justify-content: space-around;
  border-right: none;
  height: 100%;
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 8px 0;
  position: relative;
}

.nav-item span:not(.mobile-badge) {
  font-size: 11px;
  margin-top: 4px;
  color: #606266;
}

.nav-item.is-active span {
  color: #409EFF;
  font-weight: 500;
}

.mobile-badge {
  position: absolute;
  top: 8px;
  right: 20%;
  background-color: #f56c6c;
  color: white;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  min-width: 16px;
  text-align: center;
}

/* 移动端内容区适配 */
.mobile-content {
  padding: 16px !important;
  padding-top: 72px !important;
  padding-bottom: 80px !important;
  background-color: #f5f7fa;
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

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .main-layout {
    background-color: #1a1a1a;
  }
  
  .sidebar {
    background-color: #1e1e1e;
    border-right-color: #333;
  }
  
  .logo {
    border-bottom-color: #333;
  }
  
  .sidebar-menu .el-menu-item:hover {
    background-color: #2d2d2d;
  }
  
  .sidebar-footer {
    background-color: #1e1e1e;
    border-top-color: #333;
  }
  
  .header {
    background-color: #1e1e1e;
    border-bottom-color: #333;
  }
  
  .mobile-footer {
    background-color: #1e1e1e;
    border-top-color: #333;
  }
}
</style>
