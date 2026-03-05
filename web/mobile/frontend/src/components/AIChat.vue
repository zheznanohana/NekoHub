<template>
  <div class="ai-chat-page">
    <div class="chat-container">
      <!-- 左侧：配置区 -->
      <div class="config-panel">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🤖 AI 模型配置</span>
              <el-button size="small" @click="showConfigDialog">
                <el-icon><Setting /></el-icon> 管理
              </el-button>
            </div>
          </template>
          
          <el-form label-width="100px" size="small">
            <el-form-item label="当前模型">
              <el-select v-model="currentModelId" @change="switchModel" style="width: 100%">
                <el-option
                  v-for="model in modelConfigs"
                  :key="model.id"
                  :label="model.name"
                  :value="model.id"
                >
                  <span>{{ model.name }}</span>
                  <span style="float: right; color: #8492a6; font-size: 12px">{{ model.model }}</span>
                </el-option>
              </el-select>
            </el-form-item>
            
            <el-form-item label="数据源">
              <el-checkbox-group v-model="selectedDomains">
                <el-checkbox label="gotify">通知</el-checkbox>
                <el-checkbox label="rss">订阅</el-checkbox>
                <el-checkbox label="imap">邮件</el-checkbox>
                <el-checkbox label="web3">链上</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item label="条数限制">
              <div class="limit-inputs">
                <el-input-number v-model="limits.gotify" size="small" :min="1" :max="100" />
                <el-input-number v-model="limits.rss" size="small" :min="1" :max="50" />
                <el-input-number v-model="limits.imap" size="small" :min="1" :max="50" />
                <el-input-number v-model="limits.web3" size="small" :min="1" :max="50" />
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
      
      <!-- 右侧：对话区 -->
      <div class="chat-panel">
        <div class="chat-history" ref="chatHistoryRef">
          <div v-for="(msg, index) in chatHistory" :key="index" class="chat-message" :class="msg.role">
            <div class="avatar">
              <el-avatar v-if="msg.role === 'user'" icon="User" />
              <el-avatar v-else icon="ChatDotRound" />
            </div>
            <div class="content">
              <div class="bubble" v-html="renderMarkdown(msg.content)"></div>
            </div>
          </div>
          
          <div v-if="loading" class="chat-message ai">
            <div class="avatar"><el-avatar icon="ChatDotRound" /></div>
            <div class="content">
              <div class="bubble">AI 正在思考中...</div>
            </div>
          </div>
        </div>
        
        <div class="chat-input">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="3"
            placeholder="在此输入你想问的问题，AI 将结合上方勾选的数据源为您解答..."
            @keydown.ctrl.enter="sendMessage"
          />
          <el-button type="primary" @click="sendMessage" :loading="loading" style="margin-top: 12px">
            <el-icon><Promotion /></el-icon> 发送
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 模型配置管理对话框 -->
    <el-dialog v-model="dialogVisible" title="AI 模型配置管理" width="700px">
      <div class="model-list">
        <h4>已配置的模型</h4>
        <el-table :data="modelConfigs" style="width: 100%; margin-bottom: 20px" highlight-current-row>
          <el-table-column prop="name" label="名称" width="150" />
          <el-table-column prop="baseUrl" label="API Base URL" />
          <el-table-column prop="model" label="模型" width="150" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" @click="editModel(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteModel(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <el-button type="primary" @click="addNewModel" style="margin-bottom: 20px">
          <el-icon><Plus /></el-icon> 添加新模型
        </el-button>
      </div>
      
      <el-divider />
      
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="配置名称">
          <el-input v-model="configForm.name" placeholder="如：DeepSeek、Claude" />
        </el-form-item>
        <el-form-item label="API Base URL">
          <el-input v-model="configForm.baseUrl" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="configForm.apiKey" type="password" placeholder="sk-xxx" />
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="configForm.model" placeholder="deepseek-chat" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfigSave">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'AIChatPage',
  data() {
    return {
      chatHistory: [
        { role: 'ai', content: '你好！我是 AI 助手，可以帮你分析通知、RSS、邮件和链上数据。请问有什么可以帮你的？' }
      ],
      inputText: '',
      loading: false,
      selectedDomains: ['gotify', 'rss'],
      limits: {
        gotify: 20,
        rss: 10,
        imap: 10,
        web3: 20
      },
      modelConfigs: [],
      currentModelId: '',
      dialogVisible: false,
      configForm: {
        id: '',
        name: '',
        baseUrl: '',
        apiKey: '',
        model: ''
      }
    }
  },
  methods: {
    async loadModelConfigs() {
      try {
        const token = localStorage.getItem('token')
        const res = await fetch('/api/settings', {
          headers: { 'Authorization': 'Bearer ' + token }
        })
        if (res.ok) {
          const data = await res.json()
          const configs = JSON.parse(data.ai_model_configs || '[]')
          this.modelConfigs = configs
          
          if (configs.length > 0) {
            this.currentModelId = data.ai_current_model || configs[0].id
          }
        }
      } catch (e) {
        console.error('加载模型配置失败:', e)
      }
    },
    
    async saveModelConfigs() {
      try {
        const token = localStorage.getItem('token')
        await fetch('/api/settings', {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ai_model_configs: JSON.stringify(this.modelConfigs),
            ai_current_model: this.currentModelId
          })
        })
      } catch (e) {
        console.error('保存模型配置失败:', e)
      }
    },
    
    switchModel() {
      console.log('切换到模型:', this.currentModelId)
      this.$message.success('已切换到 ' + this.modelConfigs.find(m => m.id === this.currentModelId)?.name)
    },
    
    addNewModel() {
      this.configForm = {
        id: '',
        name: '',
        baseUrl: '',
        apiKey: '',
        model: ''
      }
    },
    
    editModel(model) {
      this.configForm = { ...model }
    },
    
    deleteModel(id) {
      this.$confirm('确定要删除这个模型配置吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.modelConfigs = this.modelConfigs.filter(m => m.id !== id)
        if (this.currentModelId === id) {
          this.currentModelId = this.modelConfigs.length > 0 ? this.modelConfigs[0].id : ''
        }
        this.saveModelConfigs()
        this.$message.success('删除成功')
      }).catch(() => {})
    },
    
    handleConfigSave() {
      if (!this.configForm.name || !this.configForm.baseUrl || !this.configForm.apiKey || !this.configForm.model) {
        this.$message.warning('请填写完整信息')
        return
      }
      
      if (this.configForm.id) {
        // 编辑现有配置
        const index = this.modelConfigs.findIndex(m => m.id === this.configForm.id)
        if (index >= 0) {
          this.modelConfigs[index] = { ...this.configForm }
        }
      } else {
        // 添加新配置
        const newConfig = {
          ...this.configForm,
          id: 'model_' + Date.now()
        }
        this.modelConfigs.push(newConfig)
        if (!this.currentModelId) {
          this.currentModelId = newConfig.id
        }
      }
      
      this.saveModelConfigs()
      this.$message.success('保存成功')
      this.dialogVisible = false
    },
    
    async sendMessage() {
      if (!this.inputText.trim() || this.loading) return
      
      const userMsg = this.inputText.trim()
      this.chatHistory.push({ role: 'user', content: userMsg })
      this.inputText = ''
      this.loading = true
      
      this.$nextTick(() => {
        this.scrollToBottom()
      })
      
      try {
        const model = this.modelConfigs.find(m => m.id === this.currentModelId)
        if (!model) {
          throw new Error('请先配置 AI 模型')
        }
        
        const token = localStorage.getItem('token')
        const response = await fetch('/api/ai/chat', {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: userMsg,
            domains: this.selectedDomains,
            limit: this.limits,
            model_config: model
          })
        })
        
        if (response.ok) {
          const data = await response.json()
          this.chatHistory.push({ role: 'ai', content: data.response })
        } else {
          throw new Error('API 请求失败')
        }
      } catch (error) {
        this.chatHistory.push({ role: 'ai', content: '❌ 请求失败：' + error.message })
      } finally {
        this.loading = false
        this.$nextTick(() => {
          this.scrollToBottom()
        })
      }
    },
    
    scrollToBottom() {
      if (this.$refs.chatHistoryRef) {
        this.$refs.chatHistoryRef.scrollTop = this.$refs.chatHistoryRef.scrollHeight
      }
    },
    
    renderMarkdown(text) {
      if (typeof window !== 'undefined' && window.markdownIt) {
        return window.markdownIt().render(text)
      }
      return text
    },
    
    showConfigDialog() {
      this.addNewModel()
      this.dialogVisible = true
    }
  },
  mounted() {
    this.loadModelConfigs()
  }
}
</script>

<style scoped>
.ai-chat-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-container {
  display: flex;
  gap: 20px;
  height: 100%;
}

.config-panel {
  width: 300px;
  flex-shrink: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.limit-inputs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 8px;
  overflow: hidden;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.chat-message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.chat-message.ai {
  align-self: flex-start;
}

.avatar {
  flex-shrink: 0;
}

.content {
  flex: 1;
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-wrap: break-word;
}

.chat-message.user .bubble {
  background: #409EFF;
  color: white;
}

.chat-message.ai .bubble {
  background: #f5f7fa;
  color: #303133;
}

.chat-input {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
  background: #f5f7fa;
}

.model-list h4 {
  margin: 0 0 12px 0;
  color: #303133;
}
</style>
