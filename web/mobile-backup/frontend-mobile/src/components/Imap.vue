<template>
  <div class="imap-page">
    <div class="page-header">
      <h2>📧 邮件中心</h2>
      <el-button type="primary" @click="showConfigDialog">
        <el-icon><Setting /></el-icon> 邮箱配置
      </el-button>
    </div>

    <el-row :gutter="20" style="flex: 1; overflow: hidden;">
      <el-col :span="6">
        <el-card class="account-card">
          <template #header>
            <div class="card-header">
              <span>邮箱账户</span>
              <el-button type="primary" size="small" @click="addAccount">
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>
          </template>
          <el-table :data="accounts" style="width: 100%" height="400" highlight-current-row @current-change="handleAccountSelect">
            <el-table-column prop="email" label="邮箱" />
            <el-table-column label="" width="50">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '已启用' : '已禁用' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card class="stats-card" style="margin-top: 20px;">
          <template #header>统计信息</template>
          <div class="stats-content">
            <div class="stat-item">
              <span class="stat-label">未读邮件</span>
              <span class="stat-value unread">{{ stats.unread }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">今日邮件</span>
              <span class="stat-value">{{ stats.today }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">总邮件数</span>
              <span class="stat-value">{{ stats.total }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card class="email-list-card">
          <template #header>
            <div class="card-header">
              <span>{{ currentAccount ? currentAccount.email : '选择邮箱账户' }}</span>
              <div class="header-actions">
                <el-button size="small" @click="refreshEmails" :loading="refreshing">
                  <el-icon><Refresh /></el-icon> 刷新
                </el-button>
                <el-input v-model="searchText" placeholder="搜索邮件..." size="small" style="width: 200px" clearable />
              </div>
            </div>
          </template>

          <div v-if="currentAccount" class="email-list">
            <el-table :data="filteredEmails" style="width: 100%" height="600" @row-click="openEmail">
              <el-table-column prop="from" label="发件人" width="200" />
              <el-table-column prop="subject" label="主题" />
              <el-table-column prop="date" label="日期" width="160" />
              <el-table-column label="" width="50">
                <template #default="{ row }">
                  <el-icon v-if="!row.read" color="#409EFF"><Bell /></el-icon>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-empty v-else description="请从左侧选择邮箱账户" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="configDialogVisible" title="邮箱配置" width="600px">
      <el-form :model="configForm" label-width="100px">
        <el-form-item label="邮箱地址">
          <el-input v-model="configForm.email" placeholder="your@gmail.com" />
        </el-form-item>
        <el-form-item label="IMAP 服务器">
          <el-input v-model="configForm.imapServer" placeholder="imap.gmail.com" />
        </el-form-item>
        <el-form-item label="IMAP 端口">
          <el-input-number v-model="configForm.imapPort" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="授权码">
          <el-input v-model="configForm.password" type="password" placeholder="应用专用密码" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="configForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="emailDialogVisible" :title="currentEmail?.subject" width="900px" top="5vh">
      <div v-if="currentEmail" class="email-detail">
        <div class="email-header">
          <div class="email-meta"><strong>发件人：</strong> {{ currentEmail.from }}</div>
          <div class="email-meta"><strong>收件人：</strong> {{ currentEmail.to }}</div>
          <div class="email-meta"><strong>日期：</strong> {{ currentEmail.date }}</div>
        </div>
        <el-divider />
        <div class="email-body" v-html="currentEmail.html || currentEmail.text"></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const accounts = ref([{ email: 'zhez25325@gmail.com', enabled: true, imapServer: 'imap.gmail.com', imapPort: 993 }])
const currentAccount = ref(null)
const emails = ref([])
const searchText = ref('')
const refreshing = ref(false)
const configDialogVisible = ref(false)
const emailDialogVisible = ref(false)
const currentEmail = ref(null)
const configForm = ref({ email: '', imapServer: '', imapPort: 993, password: '', enabled: true })
const stats = ref({ unread: 0, today: 0, total: 0 })

const filteredEmails = computed(() => {
  if (!searchText.value) return emails.value
  const text = searchText.value.toLowerCase()
  return emails.value.filter(e => (e.from || '').toLowerCase().includes(text) || (e.subject || '').toLowerCase().includes(text))
})

const showConfigDialog = () => {
  configForm.value = currentAccount.value ? { ...currentAccount.value } : { email: '', imapServer: '', imapPort: 993, password: '', enabled: true }
  configDialogVisible.value = true
}

const addAccount = () => {
  currentAccount.value = null
  showConfigDialog()
}

const saveConfig = () => {
  const existing = accounts.value.find(a => a.email === configForm.value.email)
  if (existing) {
    Object.assign(existing, configForm.value)
  } else {
    accounts.value.push({ ...configForm.value })
  }
  configDialogVisible.value = false
  ElMessage.success('配置已保存')
}

const handleAccountSelect = (account) => {
  currentAccount.value = account
  emails.value = [{ from: 'test@example.com', subject: '测试邮件', date: '2026-03-03 10:00', read: false, to: account.email, text: '这是测试内容' }]
  stats.value = { unread: 1, today: 1, total: 1 }
}

const refreshEmails = async () => {
  if (!currentAccount.value) return
  refreshing.value = true
  setTimeout(() => {
    refreshing.value = false
    ElMessage.success('刷新成功')
  }, 1000)
}

const openEmail = (email) => {
  currentEmail.value = email
  email.read = true
  emailDialogVisible.value = true
}
</script>

<style scoped>
.imap-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.account-card, .email-list-card, .stats-card {
  overflow: hidden;
}
.stats-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-label {
  color: #909399;
  font-size: 14px;
}
.stat-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}
.stat-value.unread {
  color: #f56c6c;
}
.email-list {
  height: 100%;
}
.email-detail {
  line-height: 1.8;
}
.email-header {
  margin-bottom: 16px;
}
.email-meta {
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}
.email-body {
  font-size: 15px;
  color: #303133;
  line-height: 1.8;
}
</style>
