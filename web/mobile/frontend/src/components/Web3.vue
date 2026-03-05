<template>
  <div class="web3-page">
    <div class="page-header">
      <h2>🔗 Web3 资产雷达 Pro</h2>
      <div class="header-actions">
        <el-button type="primary" @click="refreshAll" :loading="refreshing">
          <el-icon><Refresh /></el-icon> 深度同步
        </el-button>
        <el-button @click="addAccount">
          <el-icon><Plus /></el-icon> 新增账户
        </el-button>
        <el-button type="danger" @click="deleteAccount">
          <el-icon><Delete /></el-icon> 删除账户
        </el-button>
      </div>
    </div>
    
    <el-row :gutter="20" style="flex: 1; overflow: hidden;">
      <!-- 左侧：地址列表 -->
      <el-col :span="6">
        <el-card class="addr-card">
          <template #header>监控地址 ({{ accounts.length }})</template>
          <el-table 
            :data="accounts" 
            style="width: 100%" 
            height="500"
            highlight-current-row
            @current-change="handleAccountSelect"
          >
            <el-table-column label="名称" width="100">
              <template #default="{ row }">
                <span>{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="地址">
              <template #default="{ row }">
                <span class="mono-text">{{ shortenAddress(row.addr) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <el-card class="total-card" style="margin-top: 20px;">
          <template #header>总资产估值</template>
          <div class="total-value">
            <span class="value">¥123,456</span>
            <span class="change positive">+2.5%</span>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：交易记录 + 配置 -->
      <el-col :span="18">
        <el-card class="tx-card" style="margin-bottom: 20px;">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <span>{{ currentAccount ? currentAccount.name : '选择地址查看交易' }}</span>
                <div class="chain-tags" v-if="currentAccount">
                  <el-tag v-for="chain in currentAccount.chains" :key="chain" size="small" style="margin-left: 8px;">
                    {{ chain }}
                  </el-tag>
                </div>
              </div>
            </div>
          </template>
          
          <div v-if="currentAccount" class="tx-list">
            <el-table 
              :data="transactions" 
              style="width: 100%"
              height="400"
              @row-click="openTxDetail"
            >
              <el-table-column label="方向" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.direction === 'in' ? 'success' : 'warning'" size="small">
                    {{ row.direction === 'in' ? '↙️' : '↗️' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="80">
                <template #default="{ row }">
                  <span style="font-size: 12px;">{{ row.type }}</span>
                </template>
              </el-table-column>
              <el-table-column label="金额" width="150">
                <template #default="{ row }">
                  <span style="font-weight: bold;">{{ row.val_sym }}</span>
                </template>
              </el-table-column>
              <el-table-column label="链" width="80">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.chain }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="From → To">
                <template #default="{ row }">
                  <span class="mono-text" style="font-size: 12px;">
                    {{ row.from_s }} → {{ row.to_s }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="时间" width="160">
                <template #default="{ row }">
                  <span style="font-size: 12px; color: #909399;">{{ row.time_str }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          
          <el-empty v-else description="请从左侧选择钱包地址" />
        </el-card>
        
        <!-- 配置编辑器 -->
        <el-card class="config-card">
          <template #header>账户配置</template>
          <el-form :model="configForm" label-width="100px" size="small">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-form-item label="类型">
                  <el-select v-model="configForm.type" style="width: 100%">
                    <el-option label="EVM" value="EVM" />
                    <el-option label="BTC" value="BTC" />
                    <el-option label="SOL" value="SOL" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="名称">
                  <el-input v-model="configForm.name" placeholder="My_Wallet" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="地址">
                  <el-input v-model="configForm.addr" placeholder="0x..." />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="API Key">
                  <el-input v-model="configForm.key" type="password" placeholder="Etherscan API Key" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="自定义接口">
                  <el-input v-model="configForm.custom_url" placeholder="Custom RPC/API URL" />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="监控链" v-if="configForm.type === 'EVM'">
              <el-checkbox-group v-model="configForm.chains">
                <el-checkbox label="ETH" />
                <el-checkbox label="BSC" />
                <el-checkbox label="Base" />
                <el-checkbox label="Polygon" />
                <el-checkbox label="Arbitrum" />
                <el-checkbox label="OP" />
                <el-checkbox label="AVAX" />
                <el-checkbox label="Linea" />
                <el-checkbox label="Scroll" />
                <el-checkbox label="Custom" />
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveConfig">
                <el-icon><Check /></el-icon> 保存并应用
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 交易详情对话框 -->
    <el-dialog v-model="txDialogVisible" title="交易详情" width="700px">
      <div v-if="currentTx" class="tx-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="交易哈希">
            <el-link :href="getExplorerLink(currentTx.hash, currentTx.chain)" target="_blank">
              {{ currentTx.hash }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="方向">
            <el-tag :type="currentTx.direction === 'in' ? 'success' : 'warning'">
              {{ currentTx.direction === 'in' ? '转入' : '转出' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="金额">{{ currentTx.val_sym }}</el-descriptions-item>
          <el-descriptions-item label="链">{{ currentTx.chain }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ currentTx.time_str }}</el-descriptions-item>
          <el-descriptions-item label="From">
            <span class="mono-text">{{ currentTx.from }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="To">
            <span class="mono-text">{{ currentTx.to }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const accounts = ref([
  { 
    name: '主钱包', 
    addr: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb', 
    type: 'EVM',
    chains: ['ETH', 'BSC'],
    key: '',
    custom_url: ''
  }
])

const currentAccount = ref(null)
const transactions = ref([])
const txDialogVisible = ref(false)
const currentTx = ref(null)
const refreshing = ref(false)

const configForm = ref({
  name: '',
  addr: '',
  key: '',
  custom_url: '',
  type: 'EVM',
  chains: []
})

const shortenAddress = (addr) => {
  if (!addr) return ''
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

const addAccount = () => {
  const newAcc = {
    name: `Wallet_${accounts.value.length + 1}`,
    addr: '',
    key: '',
    custom_url: '',
    type: 'EVM',
    chains: ['ETH']
  }
  accounts.value.push(newAcc)
  currentAccount.value = newAcc
  configForm.value = { ...newAcc }
}

const deleteAccount = () => {
  if (!currentAccount.value) {
    ElMessage.warning('请先选择要删除的账户')
    return
  }
  accounts.value = accounts.value.filter(a => a.addr !== currentAccount.value.addr)
  currentAccount.value = null
  transactions.value = []
  ElMessage.success('删除成功')
}

const handleAccountSelect = (account) => {
  currentAccount.value = account
  configForm.value = { ...account }
  // TODO: 调用 API 获取交易记录
  transactions.value = [
    { 
      direction: 'in', 
      type: '转账', 
      val_sym: '1.5 ETH', 
      chain: 'ETH',
      hash: '0x1234567890abcdef...',
      time_str: '2026-03-03 10:30:00',
      from: '0xabc...123',
      to: '0xdef...456',
      from_s: '0xabc...123',
      to_s: '0xdef...456'
    }
  ]
}

const refreshAll = async () => {
  refreshing.value = true
  // TODO: 调用 API 刷新所有账户
  setTimeout(() => {
    refreshing.value = false
    ElMessage.success('深度同步完成')
  }, 3000)
}

const saveConfig = () => {
  if (!currentAccount.value) return
  const idx = accounts.value.findIndex(a => a.addr === currentAccount.value.addr)
  if (idx >= 0) {
    accounts.value[idx] = { ...configForm.value }
    ElMessage.success('配置已保存')
  }
}

const openTxDetail = (tx) => {
  currentTx.value = tx
  txDialogVisible.value = true
}

const getExplorerLink = (hash, chain) => {
  const explorers = {
    'ETH': 'https://etherscan.io/tx/',
    'BSC': 'https://bscscan.com/tx/',
    'Base': 'https://basescan.org/tx/',
    'Polygon': 'https://polygonscan.com/tx/',
    'Arbitrum': 'https://arbiscan.io/tx/',
    'OP': 'https://optimistic.etherscan.io/tx/'
  }
  return (explorers[chain] || explorers['ETH']) + hash
}
</script>

<style scoped>
.web3-page {
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

.header-actions {
  display: flex;
  gap: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chain-tags {
  display: flex;
  align-items: center;
}

.addr-card {
  height: calc(100vh - 300px);
  overflow: hidden;
}

.tx-card {
  overflow: hidden;
}

.config-card {
  overflow: hidden;
}

.total-card {
  overflow: hidden;
}

.total-value {
  display: flex;
  align-items: center;
  gap: 12px;
}

.value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.change {
  font-size: 16px;
  font-weight: bold;
}

.change.positive {
  color: #67c23a;
}

.mono-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.tx-list {
  height: 100%;
}

.tx-detail {
  line-height: 1.8;
}
</style>
