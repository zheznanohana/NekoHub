<template>
  <div class="login-page">
    <div class="login-container">
      <h1 class="login-title">NekoHub</h1>
      <p class="login-subtitle">智能通知管理系统</p>
      
      <div class="login-form">
        <div class="form-item">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="请输入用户名" />
        </div>
        
        <div class="form-item">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" @keydown.enter="handleLogin" />
        </div>
        
        <button class="login-btn" @click="handleLogin" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
        
        <div class="login-hint">
          默认账号：admin / admin
        </div>
        
        <div v-if="error" class="error-msg">{{ error }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginPage',
  data() {
    return {
      username: '',
      password: '',
      loading: false,
      error: ''
    }
  },
  methods: {
    async handleLogin() {
      this.loading = true
      this.error = ''
      
      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            username: this.username, 
            password: this.password 
          })
        })
        
        const data = await response.json()
        
        if (data.access_token) {
          localStorage.setItem('token', data.access_token)
          localStorage.setItem('username', this.username)
          this.$message.success('登录成功')
          this.$router.push('/inbox')
        } else {
          this.error = '登录失败：' + (data.message || '用户名或密码错误')
        }
      } catch (e) {
        this.error = '网络错误：' + e.message
      } finally {
        this.loading = false
      }
    }
  },
  mounted() {
    const token = localStorage.getItem('token')
    if (token) {
      this.$router.push('/inbox')
    }
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  margin: 0;
  padding: 0;
}

.login-container {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 400px;
  z-index: 1000;
}

.login-title {
  text-align: center;
  color: #303133;
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: bold;
}

.login-subtitle {
  text-align: center;
  color: #909399;
  margin: 0 0 30px 0;
  font-size: 14px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  color: #606266;
  font-size: 14px;
  font-weight: 500;
}

.form-item input {
  padding: 12px 16px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.form-item input:focus {
  outline: none;
  border-color: #409EFF;
}

.login-btn {
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-hint {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.error-msg {
  color: #f56c6c;
  font-size: 14px;
  text-align: center;
  padding: 10px;
  background: #fef0f0;
  border-radius: 6px;
}
</style>
