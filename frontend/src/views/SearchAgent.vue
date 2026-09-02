<template>
  <div class="page-container">
    <el-row :gutter="24" class="main-row">
      <!-- 左侧输入区域 -->
      <el-col :span="10">
        <!-- 搜索表单卡片 -->
        <el-card class="form-card">
          <template #header>
            <div class="card-header">
              <div class="header-icon search-icon">🔍</div>
              <div class="header-info">
                <h3>智能搜索 Agent</h3>
                <p>多引擎聚合智能搜索</p>
              </div>
            </div>
          </template>

          <el-form :model="form" label-width="90px" class="search-form">
            <el-form-item label="搜索引擎">
              <div class="engine-grid">
                <div
                  v-for="engine in engines"
                  :key="engine.value"
                  class="engine-item"
                  :class="{ active: form.engine === engine.value }"
                  @click="form.engine = engine.value"
                >
                  <span class="engine-icon">{{ engine.icon }}</span>
                  <span class="engine-name">{{ engine.label }}</span>
                  <span v-if="engine.free" class="engine-badge">免费</span>
                </div>
              </div>
            </el-form-item>

            <el-form-item label="API KEY" v-if="!engines.find(e => e.value === form.engine)?.free">
              <el-input
                v-model="form.apiKey"
                type="password"
                show-password
                :placeholder="'请输入 ' + (engines.find(e => e.value === form.engine)?.label || '') + ' API Key'"
              >
                <template #prefix>
                  <el-icon><Key /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item label="使用模型">
              <el-select v-model="form.modelId" style="width: 100%" placeholder="选择 AI 模型">
                <el-option
                  v-for="m in models"
                  :key="m.id"
                  :label="m.name"
                  :value="m.id"
                >
                  <div class="model-option">
                    <span class="model-dot" :style="{ background: getProviderColor(m.provider) }"></span>
                    {{ m.name }}
                  </div>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="搜索内容">
              <el-input
                v-model="form.query"
                type="textarea"
                :rows="4"
                placeholder="输入您想要搜索的问题或关键词..."
                class="query-input"
              />
            </el-form-item>

            <el-form-item label="搜索模式">
              <el-switch
                v-model="form.deepSearch"
                active-text="深度研究"
                inactive-text="快速搜索"
              />
              <el-tooltip
                content="深度研究会从多个角度检索、去重并要求答案标注来源"
                placement="top"
              >
                <el-icon class="mode-help"><QuestionFilled /></el-icon>
              </el-tooltip>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                class="search-btn"
                @click="doSearch"
                :loading="loading"
                :disabled="!form.query"
              >
                <el-icon v-if="!loading"><Search /></el-icon>
                {{ loading ? '搜索中...' : '开始智能搜索' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 搜索历史卡片 -->
        <el-card class="history-card">
          <template #header>
            <div class="card-header">
              <div class="header-icon history-icon">📜</div>
              <div class="header-info">
                <h3>搜索历史</h3>
                <p>最近搜索记录</p>
              </div>
            </div>
          </template>

          <div class="history-list" v-if="history.length">
            <div
              v-for="record in history"
              :key="record.id"
              class="history-item"
            >
              <div class="history-time">{{ formatTime(record.created_at) }}</div>
              <div class="history-content">
                <span class="history-query">{{ record.query }}</span>
                <el-tag size="small" class="engine-tag">{{ getEngineLabel(record.engine) }}</el-tag>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无搜索历史" :image-size="80" />
        </el-card>
      </el-col>

      <!-- 右侧结果区域 -->
      <el-col :span="14">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <div class="header-icon result-icon">📝</div>
              <div class="header-info">
                <h3>搜索结果</h3>
                <p>AI 智能总结与答案</p>
              </div>
              <div class="header-actions" v-if="result && !loading">
                <el-button class="copy-btn" @click="copyResult">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button class="export-btn" @click="exportResult">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="loading" class="loading-container">
            <div class="loading-animation">
              <div class="loading-dot"></div>
              <div class="loading-dot"></div>
              <div class="loading-dot"></div>
            </div>
            <p class="loading-text">正在搜索并分析结果...</p>
          </div>

          <div v-else-if="result" class="result-content" v-html="resultHtml" />

          <div v-else class="empty-container">
            <div class="empty-illustration">
              <span class="empty-icon">🔎</span>
            </div>
            <h4>开始您的智能搜索</h4>
            <p>输入问题，AI 将聚合多个搜索引擎为您找到最佳答案</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { modelApi, searchApi } from '@/api/request'
import { marked } from 'marked'
import { WebSocketClient } from '@/api/websocket'

const loading = ref(false)
const models = ref<any[]>([])
const history = ref<any[]>([])
const result = ref('')
const resultQuery = ref('')

const form = ref({
  engine: 'bocha',  // 默认使用 Bocha（国内可用）
  apiKey: '',
  modelId: null as number | null,
  query: '',
  deepSearch: false,
})

const engines = [
  { label: 'Bocha 波查', value: 'bocha', icon: '🌊', free: false, recommended: true, desc: '国内可用' },
  { label: 'Tavily', value: 'tavily', icon: '🎯', free: false, recommended: true, desc: 'AI搜索' },
  { label: 'DuckDuckGo', value: 'duckduckgo', icon: '🦆', free: true, recommended: false, desc: '需代理' },
  { label: 'SerpAPI', value: 'serpapi', icon: '🔍', free: false, recommended: false, desc: 'Google' },
  { label: 'Bing', value: 'bing', icon: '📘', free: false, recommended: false, desc: '微软' },
]

const engineLabels: Record<string, string> = {
  bocha: 'Bocha 波查',
  tavily: 'Tavily',
  duckduckgo: 'DuckDuckGo',
  serpapi: 'SerpAPI',
  bing: 'Bing',
}

const providerColors: Record<string, string> = {
  zhipu: '#10b981',
  alibaba: '#f97316',
  baidu: '#3b82f6',
  xunfei: '#ec4899',
  tencent: '#06b6d4',
  moonshot: '#8b5cf6',
  minimax: '#f59e0b',
  deepseek: '#ef4444',
  custom: '#6b7280',
}

const getProviderColor = (provider: string) => providerColors[provider] || '#6b7280'
const getEngineLabel = (engine: string) => engineLabels[engine] || engine

const resultHtml = computed(() => {
  return result.value ? marked(result.value) as string : ''
})

const ws = ref<WebSocketClient | null>(null)

const formatTime = (time: string) => {
  if (!time) return '-'
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`

  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const loadModels = async () => {
  try {
    models.value = await modelApi.getAll()
    const defaultModel = models.value.find((m) => m.is_default)
    if (defaultModel) {
      form.value.modelId = defaultModel.id
    }
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

const loadHistory = async () => {
  try {
    history.value = await searchApi.getRecords(10)
  } catch (e) {
    console.error(e)
  }
}

const doSearch = async () => {
  if (!form.value.modelId) {
    ElMessage.warning('请选择模型')
    return
  }

  loading.value = true
  result.value = ''
  resultQuery.value = form.value.query

  ws.value = new WebSocketClient(
    'search',
    (data) => {
      const parsed = JSON.parse(data)
      if (parsed.type === 'chunk') {
        result.value += parsed.content
      } else if (parsed.type === 'done') {
        loading.value = false
        loadHistory()
        ElMessage.success('搜索完成')
      } else if (parsed.type === 'error') {
        ElMessage.error(parsed.message)
        loading.value = false
      }
    },
    () => {
      ElMessage.error('WebSocket 连接失败')
      loading.value = false
    }
  )

  try {
    await ws.value.connect()
    ws.value.send({
      query: form.value.query,
      engine: form.value.engine,
      api_key: form.value.apiKey,
      model_id: form.value.modelId,
      deep_search: form.value.deepSearch,
      max_subqueries: form.value.deepSearch ? 3 : 1,
    })
  } catch (error) {
    ElMessage.error('连接失败')
    loading.value = false
  }
}

const copyResult = async () => {
  try {
    await navigator.clipboard.writeText(result.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

const exportResult = () => {
  const safeQuery = resultQuery.value
    .trim()
    .replace(/[\\/:*?"<>|]/g, '-')
    .replace(/\s+/g, '-')
    .slice(0, 50) || '搜索结果'
  const blob = new Blob([result.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = `${safeQuery}.md`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 100)
  ElMessage.success('导出成功')
}

onMounted(() => {
  loadModels()
  loadHistory()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  position: relative;
  z-index: 1;
}

.main-row {
  height: 100%;
}

/* 卡片通用样式 */
.form-card,
.history-card,
.result-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.form-card :deep(.el-card__header),
.history-card :deep(.el-card__header),
.result-card :deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #f3f4f6;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.search-icon {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
}

.history-icon {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
}

.result-icon {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.header-info h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.header-info p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #9ca3af;
}

.header-actions {
  margin-left: auto;
}

.copy-btn {
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  color: #6b7280;
}

.export-btn {
  border: none;
  border-radius: 8px;
}

.copy-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

/* 搜索引擎选择 */
.engine-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  width: 100%;
}

.engine-item {
  position: relative;
  padding: 12px 10px;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}

.engine-item:hover {
  border-color: #93c5fd;
  background: #f0f9ff;
}

.engine-item.active {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
}

.engine-icon {
  display: block;
  font-size: 24px;
  margin-bottom: 4px;
}

.engine-name {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

.engine-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
}

/* 表单样式 */
.search-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.search-form :deep(.el-input__wrapper),
.search-form :deep(.el-textarea__inner) {
  border-radius: 10px;
}

.query-input :deep(.el-textarea__inner) {
  font-size: 14px;
  line-height: 1.6;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-help {
  margin-left: 8px;
  color: #9ca3af;
  cursor: help;
}

.model-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.search-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.search-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.35);
}

.search-btn:disabled {
  background: #e5e7eb;
  color: #9ca3af;
}

/* 历史记录 */
.history-list {
  max-height: 300px;
  overflow-y: auto;
}

.history-item {
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}

.history-item:last-child {
  border-bottom: none;
}

.history-time {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 4px;
}

.history-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.history-query {
  flex: 1;
  font-size: 13px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.engine-tag {
  background: #f3f4f6;
  border: none;
  color: #6b7280;
  font-size: 11px;
}

/* 结果区域 */
.result-card {
  height: calc(100% - 20px);
  display: flex;
  flex-direction: column;
}

.result-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.result-content {
  line-height: 1.8;
  font-size: 14px;
  color: #374151;
}

.result-content :deep(h1),
.result-content :deep(h2),
.result-content :deep(h3) {
  color: #1f2937;
  margin: 20px 0 12px;
}

.result-content :deep(h1) { font-size: 20px; }
.result-content :deep(h2) { font-size: 18px; }
.result-content :deep(h3) { font-size: 16px; }

.result-content :deep(p) {
  margin: 12px 0;
}

.result-content :deep(ul),
.result-content :deep(ol) {
  padding-left: 24px;
  margin: 12px 0;
}

.result-content :deep(li) {
  margin: 6px 0;
}

.result-content :deep(code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}

.result-content :deep(pre) {
  background: #1f2937;
  color: #e5e7eb;
  padding: 16px;
  border-radius: 12px;
  overflow-x: auto;
  margin: 16px 0;
}

.result-content :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.result-content :deep(a) {
  color: #3b82f6;
  text-decoration: none;
}

.result-content :deep(a:hover) {
  text-decoration: underline;
}

/* 加载动画 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}

.loading-animation {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.loading-dot {
  width: 12px;
  height: 12px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite both;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.loading-text {
  color: #6b7280;
  font-size: 14px;
}

/* 空状态 */
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}

.empty-illustration {
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.empty-icon {
  font-size: 48px;
}

.empty-container h4 {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}

.empty-container p {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
}
</style>
