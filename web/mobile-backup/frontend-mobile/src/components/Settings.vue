<template>
  <div class="settings-page">
    <h2>⚙️ 系统设置</h2>
    
    <el-card style="margin-bottom: 20px">
      <template #header>Gotify 服务器配置</template>
      <el-form label-width="150px">
        <el-form-item label="服务器 URL">
          <el-input v-model="settings.gotify_url" placeholder="https://notify.diu.ac.cn" />
        </el-form-item>
        <el-form-item label="接收 Token (Client)">
          <el-input v-model="settings.gotify_recv_token" type="password" />
        </el-form-item>
        <el-form-item label="发送 Token (App)">
          <el-input v-model="settings.gotify_send_token" type="password" />
        </el-form-item>
        <el-form-item>
          <el-button @click="testGotify" :loading="testing">测试连接</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card style="margin-bottom: 20px">
      <template #header>通知过滤</template>
      <el-form label-width="150px">
        <el-form-item label="过滤模式">
          <el-select v-model="settings.filter_mode" style="width: 200px">
            <el-option label="不过滤" :value="0" />
            <el-option label="黑名单 (包含关键字不提醒)" :value="1" />
            <el-option label="白名单 (仅包含关键字才提醒)" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input v-model="settings.filter_keywords" placeholder="多个关键字用逗号分隔" />
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-button type="primary" @click="saveSettings" size="large" :loading="saving">
      <el-icon><Check /></el-icon> {{ saving ? '保存中...' : '保存所有设置' }}
    </el-button>
  </div>
</template>

<script>
export default {
  name: 'SettingsPage',
  data() {
    return {
      settings: {},
      saving: false,
      testing: false
    }
  },
  methods: {
    async loadSettings() {
      try {
        const token = localStorage.getItem('token')
        const res = await fetch('/api/settings', {
          headers: { 'Authorization': 'Bearer ' + token }
        })
        if (res.ok) {
          this.settings = await res.json()
          // 确保类型正确
          this.settings.filter_mode = parseInt(this.settings.filter_mode || '0')
        }
      } catch (e) {
        console.error('加载设置失败:', e)
        this.settings = {}
      }
    },
    
    async saveSettings() {
      if (this.saving) return
      this.saving = true
      
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000)
      
      try {
        const token = localStorage.getItem('token')
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: { 
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.settings),
          signal: controller.signal
        })
        clearTimeout(timeoutId)
        
        if (res.ok) {
          this.$message.success('保存成功')
        } else {
          this.$message.error('保存失败')
        }
      } catch (e) {
        clearTimeout(timeoutId)
        console.error('保存失败:', e)
        this.$message.error(e.name === 'AbortError' ? '请求超时' : '保存失败')
      } finally {
        this.saving = false
      }
    },
    
    async testGotify() {
      if (this.testing) return
      this.testing = true
      
      try {
        const token = localStorage.getItem('token')
        const res = await fetch('/api/gotify/test', {
          method: 'POST',
          headers: { 
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            url: this.settings.gotify_url || '',
            recv_token: this.settings.gotify_recv_token || '',
            send_token: this.settings.gotify_send_token || ''
          })
        })
        
        if (res.ok) {
          const data = await res.json()
          this.$message.success(data.message || '连接成功')
        } else {
          this.$message.error('连接失败')
        }
      } catch (e) {
        this.$message.error('测试失败')
      } finally {
        this.testing = false
      }
    }
  },
  mounted() {
    this.loadSettings()
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}
.settings-page h2 {
  margin-bottom: 20px;
  color: #303133;
}
</style>
