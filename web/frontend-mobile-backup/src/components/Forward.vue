<template>
  <div class="forward-page">
    <h2>📤 通知转发中心</h2>
    
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span>全局设置</span>
          <el-switch v-model="forwardEnabled" active-text="开启转发" />
        </div>
      </template>
      
      <el-form label-width="120px">
        <el-form-item label="转发内容">
          <el-select v-model="forwardMode" style="width: 300px">
            <el-option label="全部外转 (原始 +AI)" :value="0" />
            <el-option label="仅转发原始通知" :value="1" />
            <el-option label="仅转发 AI 分析结果" :value="2" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card style="margin-bottom: 20px">
      <template #header>钉钉机器人</template>
      <el-form label-width="120px">
        <el-form-item label="Webhook URL">
          <el-input v-model="dingtalk.webhook" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
        </el-form-item>
        <el-form-item label="加签密钥">
          <el-input v-model="dingtalk.secret" type="password" placeholder="SEC..." />
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card style="margin-bottom: 20px">
      <template #header>Telegram Bot</template>
      <el-form label-width="120px">
        <el-form-item label="Bot Token">
          <el-input v-model="telegram.token" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" />
        </el-form-item>
        <el-form-item label="Chat ID">
          <el-input v-model="telegram.chatId" placeholder="用户 ID 或群组 ID（-100 开头）" />
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card style="margin-bottom: 20px">
      <template #header>邮件 SMTP</template>
      <el-form label-width="120px">
        <el-form-item label="SMTP 服务器">
          <el-input v-model="email.host" placeholder="smtp.gmail.com" />
        </el-form-item>
        <el-form-item label="发件邮箱">
          <el-input v-model="email.user" placeholder="your@gmail.com" />
        </el-form-item>
        <el-form-item label="授权码">
          <el-input v-model="email.pass" type="password" />
        </el-form-item>
        <el-form-item label="收件邮箱">
          <el-input v-model="email.to" placeholder="recipient@example.com" />
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-button type="primary" @click="saveSettings" size="large">
      <el-icon><Check /></el-icon> 保存并应用配置
    </el-button>
    <el-button @click="testForward" size="large">
      <el-icon><Promotion /></el-icon> 测试转发
    </el-button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import api from '@/api'

const settingsStore = useSettingsStore()

const forwardEnabled = ref(false)
const forwardMode = ref(0)
const dingtalk = ref({ webhook: '', secret: '' })
const telegram = ref({ token: '', chatId: '' })
const email = ref({ host: '', user: '', pass: '', to: '' })

onMounted(async () => {
  await settingsStore.fetchSettings()
  loadSettings()
})

const loadSettings = () => {
  const s = settingsStore.settings
  forwardEnabled.value = s.forward_enabled === 'true'
  forwardMode.value = parseInt(s.forward_mode || '0')
  dingtalk.value.webhook = s.dingtalk_webhook || ''
  dingtalk.value.secret = s.dingtalk_secret || ''
  telegram.value.token = s.tg_bot_token || ''
  telegram.value.chatId = s.tg_chat_id || ''
  email.value.host = s.email_smtp || ''
  email.value.user = s.email_user || ''
  email.value.pass = s.email_pass || ''
  email.value.to = s.email_to || ''
}

const saveSettings = async () => {
  const newSettings = {
    forward_enabled: forwardEnabled.value ? 'true' : 'false',
    forward_mode: forwardMode.value.toString(),
    dingtalk_webhook: dingtalk.value.webhook,
    dingtalk_secret: dingtalk.value.secret,
    tg_bot_token: telegram.value.token,
    tg_chat_id: telegram.value.chatId,
    email_smtp: email.value.host,
    email_user: email.value.user,
    email_pass: email.value.pass,
    email_to: email.value.to
  }
  
  const success = await settingsStore.saveSettings(newSettings)
  if (success) {
    alert('保存成功！')
  }
}

const testForward = async () => {
  const config = {
    dingtalk_webhook: dingtalk.value.webhook,
    dingtalk_secret: dingtalk.value.secret,
    tg_bot_token: telegram.value.token,
    tg_chat_id: telegram.value.chatId,
    email_smtp: email.value.host,
    email_user: email.value.user,
    email_pass: email.value.pass,
    email_to: email.value.to
  }
  
  try {
    const res = await api.testForward(config)
    console.log('Test result:', res.data)
    alert('测试完成，请检查各平台是否收到消息')
  } catch (error) {
    alert('测试失败：' + error.message)
  }
}
</script>

<style scoped>
.forward-page {
  max-width: 800px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-card {
  margin-bottom: 20px;
  background: #ffffff;
}
</style>
