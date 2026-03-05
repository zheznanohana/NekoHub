<template>
  <div class="rss-page">
    <div class="page-header">
      <h2>📰 RSS 订阅中心</h2>
      <div class="header-actions">
        <el-button @click="loadData" :loading="loading">
          <el-icon><Refresh /></el-icon> {{ loading ? '加载中...' : '刷新' }}
        </el-button>
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon> 新增订阅
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" style="flex: 1; overflow: hidden;">
      <el-col :span="6">
        <el-card class="source-card">
          <template #header>订阅源 ({{ sources.length }})</template>
          <el-table :data="sources" style="width: 100%" height="500" highlight-current-row @current-change="onSourceSelect">
            <el-table-column prop="name" label="名称" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card class="article-card">
          <template #header><div class="card-header"><span>{{ selectedSourceName }}</span></div></template>

          <div class="article-list">
            <el-table :data="displayArticles" style="width: 100%" height="600" @row-click="openArticle">
              <el-table-column label="标题" width="500">
                <template #default="{ row }">
                  <el-link :href="row.link" target="_blank" type="primary" :underline="false">{{ row.title }}</el-link>
                </template>
              </el-table-column>
              <el-table-column label="来源" width="100">
                <template #default="{ row }"><el-tag size="small">{{ row.source }}</el-tag></template>
              </el-table-column>
              <el-table-column label="时间" width="160">
                <template #default="{ row }"><span style="font-size: 12px; color: #909399;">{{ formatDate(row.published) }}</span></template>
              </el-table-column>
              <el-table-column label="摘要">
                <template #default="{ row }"><span style="font-size: 13px; color: #606266;">{{ stripHtml(row.summary).substring(0, 80) }}...</span></template>
              </el-table-column>
            </el-table>
          </div>
          
          <div v-if="loading && articles.length === 0" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载文章中...</span>
          </div>
          <el-empty v-else-if="articles.length === 0" description="暂无文章" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" title="新增 RSS 订阅" width="500px">
      <el-form :model="newFeed" label-width="80px">
        <el-form-item label="名称"><el-input v-model="newFeed.name" placeholder="少数派" /></el-form-item>
        <el-form-item label="URL"><el-input v-model="newFeed.url" placeholder="https://sspai.com/feed" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addFeed" :loading="adding">{{ adding ? '添加中...' : '添加' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="articleDialogVisible" title="文章详情" width="800px" top="5vh">
      <div v-if="currentArticle" class="article-detail">
        <h3>{{ currentArticle.title }}</h3>
        <div class="article-meta">
          <el-tag size="small">{{ currentArticle.source }}</el-tag>
          <span style="margin-left: 12px; color: #909399;">{{ formatDate(currentArticle.published) }}</span>
        </div>
        <el-divider />
        <div class="article-summary" v-html="currentArticle.summary"></div>
        <el-button type="primary" @click="openLink" style="margin-top: 20px;">打开原文</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'RSSPage',
  data() {
    return {
      sources: [],
      articles: [],
      selectedSource: null,
      currentArticle: null,
      dialogVisible: false,
      articleDialogVisible: false,
      loading: false,
      adding: false,
      newFeed: { name: '', url: '' }
    }
  },
  computed: {
    selectedSourceName() {
      return this.selectedSource ? this.selectedSource.name : '全部文章'
    },
    displayArticles() {
      if (!this.selectedSource) return this.articles
      return this.articles.filter(a => a.source === this.selectedSource.name)
    }
  },
  methods: {
    async loadSources() {
      try {
        const token = localStorage.getItem('token')
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 8000)
        
        const res = await fetch('/api/settings', {
          headers: { 'Authorization': 'Bearer ' + token },
          signal: controller.signal
        })
        clearTimeout(timeoutId)
        
        if (res.ok) {
          const data = await res.json()
          this.sources = JSON.parse(data.rss_feeds || '[]')
        }
        if (this.sources.length === 0) {
          this.sources = [
            { name: '少数派', url: 'https://sspai.com/feed' },
            { name: '36Kr', url: 'https://36kr.com/feed' }
          ]
        }
      } catch (e) {
        console.error('加载订阅源失败:', e)
        this.sources = [{ name: '少数派', url: 'https://sspai.com/feed' }]
      }
    },
    
    async loadArticles() {
      try {
        const token = localStorage.getItem('token')
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 15000) // RSS 抓取需要更长时间
        
        const res = await fetch('/api/rss', {
          headers: { 'Authorization': 'Bearer ' + token },
          signal: controller.signal
        })
        clearTimeout(timeoutId)
        
        if (res.ok) {
          this.articles = await res.json()
          console.log('✅ RSS 文章:', this.articles.length, '条')
        } else {
          console.error('❌ RSS API 错误:', res.status)
          this.$message.error('获取 RSS 失败')
          this.articles = []
        }
      } catch (e) {
        console.error('❌ 获取 RSS 错误:', e)
        this.$message.error(e.name === 'AbortError' ? 'RSS 抓取超时' : '网络错误')
        this.articles = []
      }
    },
    
    async loadData() {
      if (this.loading) return
      this.loading = true
      try {
        await Promise.all([this.loadSources(), this.loadArticles()])
        this.$message.success('刷新完成')
      } catch (e) {
        console.error('刷新失败:', e)
      } finally {
        this.loading = false
      }
    },
    
    onSourceSelect(source) {
      this.selectedSource = source
    },
    
    showAddDialog() {
      this.newFeed = { name: '', url: '' }
      this.dialogVisible = true
    },
    
    async addFeed() {
      if (!this.newFeed.name || !this.newFeed.url) {
        this.$message.warning('请填写完整信息')
        return
      }
      
      this.adding = true
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000)
      
      try {
        const token = localStorage.getItem('token')
        const updated = [...this.sources, this.newFeed]
        
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: { 
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ rss_feeds: JSON.stringify(updated) }),
          signal: controller.signal
        })
        clearTimeout(timeoutId)
        
        if (res.ok) {
          this.sources = updated
          this.dialogVisible = false
          this.newFeed = { name: '', url: '' }
          this.$message.success('添加成功')
          this.loadArticles()
        } else {
          this.$message.error('添加失败')
        }
      } catch (e) {
        clearTimeout(timeoutId)
        console.error('添加失败:', e)
        this.$message.error(e.name === 'AbortError' ? '请求超时' : '网络错误')
      } finally {
        this.adding = false
      }
    },
    
    openArticle(article) {
      this.currentArticle = article
      this.articleDialogVisible = true
    },
    
    openLink() {
      if (this.currentArticle && this.currentArticle.link) {
        window.open(this.currentArticle.link, '_blank')
      }
    },
    
    formatDate(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      const now = new Date()
      const diff = now - date
      if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
      if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
      return date.toLocaleString('zh-CN')
    },
    
    stripHtml(html) {
      const tmp = document.createElement('div')
      tmp.innerHTML = html || ''
      return tmp.textContent || ''
    }
  },
  mounted() {
    this.loadData()
  }
}
</script>

<style scoped>
.rss-page { height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.header-actions { display: flex; gap: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.source-card, .article-card { height: calc(100vh - 180px); overflow: hidden; }
.article-list { height: 100%; }
.loading-state { display: flex; justify-content: center; align-items: center; height: 300px; flex-direction: column; gap: 16px; color: #909399; }
.article-detail h3 { margin: 0 0 12px 0; font-size: 20px; }
.article-meta { display: flex; align-items: center; margin-bottom: 16px; }
.article-summary { line-height: 1.8; font-size: 15px; color: #606266; }
</style>
