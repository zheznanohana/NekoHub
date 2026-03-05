<template>
  <div class="inbox-page">
    <div class="action-bar">
      <el-button type="primary" @click="loadMessages" :loading="loading">
        {{ loading ? '加载中...' : '🔄 刷新' }}
      </el-button>
      <el-button @click="markAllRead" :disabled="loading || unreadCount === 0">
        全部标为已读 ({{ unreadCount }})
      </el-button>
      <el-input v-model="searchText" placeholder="搜索消息..." style="width: 300px" clearable />
    </div>

    <div class="message-list">
      <div v-if="loading && messages.length === 0" class="loading-state">
        <span>📥 加载消息中...</span>
      </div>
      
      <el-empty v-else-if="messages.length === 0" description="暂无消息" />
      
      <div
        v-else
        v-for="msg in filteredMessages"
        :key="msg.id"
        class="message-item"
        :class="{ 'unread': !msg.is_read }"
        @click="markRead(msg.id)"
      >
        <div class="message-dot" v-if="!msg.is_read"></div>
        <div class="message-body">
          <div class="message-header">
            <el-tag :type="getSourceType(msg.source)" size="small">{{ msg.source }}</el-tag>
            <span class="message-time">{{ formatTime(msg.created_at) }}</span>
          </div>
          <div class="message-title">{{ msg.title || '无标题' }}</div>
          <div class="message-content">{{ msg.message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'InboxPage',
  data() {
    return {
      messages: [],
      searchText: '',
      loading: false
    }
  },
  computed: {
    unreadCount() {
      return this.messages.filter(m => !m.is_read).length
    },
    filteredMessages() {
      if (!this.searchText) return this.messages
      const text = this.searchText.toLowerCase()
      return this.messages.filter(m =>
        (m.title || '').toLowerCase().includes(text) ||
        (m.message || '').toLowerCase().includes(text)
      )
    }
  },
  methods: {
    async loadMessages() {
      console.log('🔄 开始加载消息...')
      if (this.loading) return
      
      this.loading = true
      const token = localStorage.getItem('token')
      
      try {
        const response = await fetch('/api/messages?limit=50', {
          headers: { 'Authorization': 'Bearer ' + token }
        })
        
        if (!response.ok) {
          throw new Error('HTTP ' + response.status)
        }
        
        this.messages = await response.json()
        console.log('✅ 加载成功:', this.messages.length, '条消息')
        if (this.messages.length > 0) {
          console.log('📝 第一条消息:', this.messages[0])
        }
      } catch (error) {
        console.error('❌ 加载失败:', error)
        this.$message.error('加载消息失败')
        this.messages = []
      } finally {
        this.loading = false
      }
    },
    
    async markRead(id) {
      const token = localStorage.getItem('token')
      try {
        await fetch('/api/messages/' + id + '/read', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token }
        })
        const msg = this.messages.find(m => m.id === id)
        if (msg) msg.is_read = true
      } catch (e) {
        console.error('标记失败:', e)
      }
    },
    
    async markAllRead() {
      const token = localStorage.getItem('token')
      const unread = this.messages.filter(m => !m.is_read)
      
      for (const msg of unread) {
        try {
          await fetch('/api/messages/' + msg.id + '/read', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
          })
          msg.is_read = true
        } catch (e) {}
      }
      
      this.$message.success('已全部标记为已读')
    },
    
    formatTime(timeStr) {
      const date = new Date(timeStr)
      const now = new Date()
      const diff = now - date
      if (diff < 60000) return '刚刚'
      if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
      if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
      return date.toLocaleDateString('zh-CN')
    },
    
    getSourceType(source) {
      const types = { gotify: 'success', rss: 'warning', imap: 'info', web3: 'danger' }
      return types[source] || ''
    }
  },
  mounted() {
    this.loadMessages()
  }
}
</script>

<style scoped>
.inbox-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  color: #909399;
}

.message-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  cursor: pointer;
  transition: all 0.3s;
  /* 移除固定高度，让内容自适应 */
  height: auto;
  min-height: auto;
}

.message-item:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.message-item.unread {
  background-color: #ecf5ff;
  border-left: 4px solid #409EFF;
  padding-left: 12px;
}

.message-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #409EFF;
  flex-shrink: 0;
  margin-top: 4px;
}

.message-body {
  flex: 1;
  min-width: 0;
  /* 允许内容撑开 */
  height: auto;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 12px;
}

.message-time {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.message-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  line-height: 1.4;
  /* 标题自动换行 */
  word-wrap: break-word;
  word-break: break-word;
}

.message-content {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  /* 移除行数限制，显示完整内容 */
  display: block;
  -webkit-line-clamp: unset;
  -webkit-box-orient: unset;
  overflow: visible;
  /* 最大高度限制，超出滚动 */
  max-height: 300px;
  overflow-y: auto;
}
</style>
