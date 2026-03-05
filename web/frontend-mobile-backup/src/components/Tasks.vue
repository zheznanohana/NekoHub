<template>
  <div class="tasks-page">
    <div class="page-header">
      <h2>🤖 AI 自动化任务中心</h2>
      <el-button type="primary" @click="addTask">
        <el-icon><Plus /></el-icon> 新建任务
      </el-button>
    </div>
    
    <el-alert
      title="💡 使用指南"
      type="info"
      :closable="false"
      style="margin-bottom: 20px"
    >
      <p>1. <strong>累计计数</strong>：每满 N 条通知运行一次</p>
      <p>2. <strong>定时触发</strong>：每天 08:00, 20:00 准点总结</p>
      <p>3. <strong>固定频率</strong>：每隔 60 分钟梳理一次</p>
    </el-alert>
    
    <div class="page-actions" v-if="taskStore.tasks.length > 0">
      <el-button type="primary" @click="saveTasks" :loading="saving">
        <el-icon><Check /></el-icon> 保存所有修改
      </el-button>
      <span class="save-hint">{{ saveHint }}</span>
    </div>
    
    <div class="task-list">
      <el-card v-for="task in taskStore.tasks" :key="task.id" class="task-card">
        <div class="task-header">
          <div class="task-title">
            <el-tag :type="task.enabled ? 'success' : 'info'">
              {{ task.enabled ? '已启用' : '已禁用' }}
            </el-tag>
            <span>{{ task.name }}</span>
          </div>
          <div class="task-actions">
            <el-button size="small" @click="editTask(task)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button size="small" @click="runTask(task.id)">
              <el-icon><VideoPlay /></el-icon> 执行
            </el-button>
            <el-button size="small" type="danger" @click="deleteTask(task.id)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </div>
        </div>
        
        <el-form label-width="100px" size="small">
          <el-form-item label="任务指令">
            <el-input v-model="task.prompt" type="textarea" :rows="2" />
          </el-form-item>
          
          <el-form-item label="触发模式">
            <el-select v-model="task.mode" style="width: 200px">
              <el-option label="累计计数" value="count" />
              <el-option label="定时触发" value="time" />
              <el-option label="固定间隔" value="interval" />
            </el-select>
            <el-input
              v-model="task.value"
              :placeholder="getModePlaceholder(task.mode)"
              style="width: 200px; margin-left: 12px"
            />
          </el-form-item>
          
          <el-form-item label="数据源">
            <div style="display: flex; flex-direction: column; gap: 8px;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-checkbox v-model="task.domains" label="gotify">通知</el-checkbox>
                <el-input-number v-if="task.domains.includes('gotify')" v-model="task.limit_gotify" size="small" :min="1" :max="100" style="width: 80px" />
                <span v-if="task.domains.includes('gotify')" style="font-size: 12px; color: #909399;">条</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-checkbox v-model="task.domains" label="rss">订阅</el-checkbox>
                <el-input-number v-if="task.domains.includes('rss')" v-model="task.limit_rss" size="small" :min="1" :max="50" style="width: 80px" />
                <span v-if="task.domains.includes('rss')" style="font-size: 12px; color: #909399;">条</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-checkbox v-model="task.domains" label="imap">邮件</el-checkbox>
                <el-input-number v-if="task.domains.includes('imap')" v-model="task.limit_imap" size="small" :min="1" :max="50" style="width: 80px" />
                <span v-if="task.domains.includes('imap')" style="font-size: 12px; color: #909399;">条</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-checkbox v-model="task.domains" label="web3">链上</el-checkbox>
                <el-input-number v-if="task.domains.includes('web3')" v-model="task.limit_web3" size="small" :min="1" :max="50" style="width: 80px" />
                <span v-if="task.domains.includes('web3')" style="font-size: 12px; color: #909399;">条</span>
              </div>
            </div>
          </el-form-item>
        </el-form>
        
        <div class="task-footer">
          <span>已运行 {{ task.run_count || 0 }} 次</span>
          <el-switch v-model="task.enabled" @change="saveTasks" />
        </div>
      </el-card>
      
      <el-empty v-if="taskStore.tasks.length === 0" description="暂无任务，点击右上角创建" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTaskStore } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'

const taskStore = useTaskStore()
const saving = ref(false)
const saveHint = ref('')

onMounted(() => {
  taskStore.fetchTasks()
})

const addTask = async () => {
  const newTask = {
    name: '新任务',
    prompt: '请总结以下信息',
    mode: 'count',
    value: '10',
    enabled: true,
    domains: ['gotify', 'rss'],
    limit_gotify: 20,
    limit_rss: 10,
    limit_imap: 10,
    limit_web3: 20
  }
  await taskStore.createTask(newTask)
}

const editTask = (task) => {
  // 任务已在卡片中直接编辑
  saveHint.value = '修改后请点击保存按钮'
}

const runTask = async (id) => {
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/tasks/${id}/run`, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token }
    })
    const data = await res.json()
    
    if (data.status === 'success') {
      ElMessage.success(`✅ ${data.message}\n运行次数：${data.run_count}`)
      // 显示 AI 结果
      if (data.result) {
        ElMessageBox.alert(data.result, 'AI 分析结果', {
          confirmButtonText: '确定',
          showClose: true,
          customStyle: { maxWidth: '600px' }
        })
      }
      // 刷新任务列表更新运行次数
      await taskStore.fetchTasks()
    } else if (data.status === 'no_data') {
      ElMessage.warning(data.message)
    } else {
      ElMessage.error(data.message || '执行失败')
    }
  } catch (error) {
    ElMessage.error('执行失败：' + error.message)
  }
}

const deleteTask = async (id) => {
  if (confirm('确定删除此任务？')) {
    await taskStore.deleteTask(id)
  }
}

const saveTasks = async () => {
  saving.value = true
  try {
    const token = localStorage.getItem('token')
    // 批量保存所有任务
    const promises = taskStore.tasks.map(task =>
      fetch(`/api/tasks/${task.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: task.name,
          prompt: task.prompt,
          mode: task.mode,
          value: task.value,
          enabled: task.enabled,
          domains: task.domains,
          limit_gotify: task.limit_gotify,
          limit_rss: task.limit_rss,
          limit_imap: task.limit_imap,
          limit_web3: task.limit_web3
        })
      })
    )
    
    await Promise.all(promises)
    ElMessage.success('保存成功')
    saveHint.value = '✅ 已保存'
    // 不要重新加载数据，保持当前状态
    // await taskStore.fetchTasks()
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  } finally {
    saving.value = false
  }
}

const getModePlaceholder = (mode) => {
  const placeholders = {
    count: '如：10（条）',
    time: '如：08:00, 20:00',
    interval: '如：60（分钟）'
  }
  return placeholders[mode] || ''
}
</script>

<style scoped>
.tasks-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.save-hint {
  font-size: 13px;
  color: #909399;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.task-card {
  transition: all 0.3s;
  background: #ffffff;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.task-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}
</style>
