<template>
  <div class="page-container">
    <!-- 统计卡片区域 -->
    <div class="stats-section">
      <div class="stat-card stat-total">
        <div class="stat-icon">
          <span>📚</span>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ animatedStats.total }}</span>
          <span class="stat-label">知识总数</span>
        </div>
        <div class="stat-trend up">
          <el-icon><TrendCharts /></el-icon>
        </div>
      </div>

      <div class="stat-card stat-official">
        <div class="stat-icon">
          <span>📖</span>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ animatedStats.official }}</span>
          <span class="stat-label">官方文档</span>
        </div>
      </div>

      <div class="stat-card stat-csdn">
        <div class="stat-icon">
          <span>💻</span>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ animatedStats.csdn }}</span>
          <span class="stat-label">CSDN</span>
        </div>
      </div>

      <div class="stat-card stat-manual">
        <div class="stat-icon">
          <span>✏️</span>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ animatedStats.manual }}</span>
          <span class="stat-label">手动导入</span>
        </div>
      </div>

      <div class="stat-card stat-arxiv">
        <div class="stat-icon">
          <span>📄</span>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ animatedStats.arxiv }}</span>
          <span class="stat-label">arXiv</span>
        </div>
      </div>

      <div class="stat-card stat-github">
        <div class="stat-icon">
          <span>🐙</span>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ animatedStats.github }}</span>
          <span class="stat-label">GitHub</span>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <div class="header-icon">📚</div>
            <div class="header-info">
              <h3>知识库管理</h3>
              <p>管理和维护您的知识数据</p>
            </div>
          </div>
          <div class="header-actions">
            <el-button type="primary" class="import-btn" @click="showImport = true">
              <el-icon><Upload /></el-icon>
              手动导入
            </el-button>
            <el-button class="crawl-btn" @click="triggerCrawl">
              <el-icon><Refresh /></el-icon>
              自动爬取
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选区域 -->
      <div class="filter-section">
        <div class="filter-item">
          <span class="filter-label">来源类型</span>
          <el-select v-model="filter.sourceType" @change="loadKnowledge" clearable placeholder="全部来源" class="filter-select">
            <el-option label="官方文档" value="official">
              <div class="filter-option">
                <span class="source-dot official"></span>
                官方文档
              </div>
            </el-option>
            <el-option label="CSDN" value="csdn">
              <div class="filter-option">
                <span class="source-dot csdn"></span>
                CSDN
              </div>
            </el-option>
            <el-option label="arXiv" value="arxiv">
              <div class="filter-option">
                <span class="source-dot arxiv"></span>
                arXiv
              </div>
            </el-option>
            <el-option label="GitHub" value="github">
              <div class="filter-option">
                <span class="source-dot github"></span>
                GitHub
              </div>
            </el-option>
            <el-option label="手动导入" value="manual">
              <div class="filter-option">
                <span class="source-dot manual"></span>
                手动导入
              </div>
            </el-option>
          </el-select>
        </div>

        <div class="filter-item">
          <span class="filter-label">分类</span>
          <el-select v-model="filter.category" @change="loadKnowledge" clearable placeholder="全部分类" class="filter-select">
            <el-option
              v-for="cat in Object.keys(stats.by_category || {})"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </div>

        <div class="filter-item search">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索知识标题..."
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 知识列表 -->
      <el-table :data="filteredKnowledge" v-loading="loading" class="knowledge-table">
        <el-table-column prop="title" label="标题" min-width="250">
          <template #default="{ row }">
            <div class="title-cell">
              <span class="source-indicator" :class="row.source_type"></span>
              <span class="title-text">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="source_type" label="来源" width="120">
          <template #default="{ row }">
            <div class="source-badge" :class="row.source_type">
              {{ getSourceLabel(row.source_type) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="140">
          <template #default="{ row }">
            <el-tag class="category-tag">{{ row.category || '未分类' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" width="200">
          <template #default="{ row }">
            <div class="tags-cell">
              <el-tag
                v-for="tag in (row.tags || []).slice(0, 3)"
                :key="tag"
                size="small"
                class="tag-item"
              >
                {{ tag }}
              </el-tag>
              <span v-if="(row.tags || []).length > 3" class="tag-more">
                +{{ row.tags.length - 3 }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="添加时间" width="160">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button class="action-btn view" @click="viewDetail(row)">
                <el-icon><View /></el-icon>
              </el-button>
              <el-button class="action-btn delete" @click="deleteKnowledge(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 导入弹窗 -->
    <el-dialog
      v-model="showImport"
      title="手动导入知识"
      width="650px"
      class="import-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="importForm" label-width="80px" class="import-form">
        <el-form-item label="标题" required>
          <el-input v-model="importForm.title" placeholder="请输入知识标题">
            <template #prefix>
              <el-icon><EditPen /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="importForm.content"
            type="textarea"
            :rows="10"
            placeholder="请输入知识内容，支持 Markdown 格式..."
            class="content-input"
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="来源URL">
              <el-input v-model="importForm.source" placeholder="https://...">
                <template #prefix>
                  <el-icon><Link /></el-icon>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input v-model="importForm.category" placeholder="如：大模型算法">
                <template #prefix>
                  <el-icon><Folder /></el-icon>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="标签">
          <el-select
            v-model="importForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入标签"
            style="width: 100%"
          >
            <el-option label="Python" value="Python" />
            <el-option label="PyTorch" value="PyTorch" />
            <el-option label="Transformer" value="Transformer" />
            <el-option label="RAG" value="RAG" />
            <el-option label="LLM" value="LLM" />
            <el-option label="Agent" value="Agent" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showImport = false">取消</el-button>
          <el-button type="primary" @click="doImport" :loading="importing" class="submit-btn">
            <el-icon><Check /></el-icon>
            导入知识
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="showDetail"
      title="知识详情"
      width="750px"
      class="detail-dialog"
    >
      <div class="detail-content" v-if="detailData.id">
        <div class="detail-header">
          <div class="detail-source" :class="detailData.source_type">
            {{ getSourceLabel(detailData.source_type) }}
          </div>
          <h3 class="detail-title">{{ detailData.title }}</h3>
          <div class="detail-meta">
            <span class="meta-item">
              <el-icon><Folder /></el-icon>
              {{ detailData.category || '未分类' }}
            </span>
            <span class="meta-item">
              <el-icon><Clock /></el-icon>
              {{ formatTime(detailData.created_at) }}
            </span>
          </div>
        </div>

        <div class="detail-tags" v-if="detailData.tags?.length">
          <el-tag
            v-for="tag in detailData.tags"
            :key="tag"
            class="detail-tag"
          >
            {{ tag }}
          </el-tag>
        </div>

        <div class="detail-source-url" v-if="detailData.source">
          <el-icon><Link /></el-icon>
          <a :href="detailData.source" target="_blank">{{ detailData.source }}</a>
        </div>

        <div class="detail-body">
          <div class="content-label">知识内容</div>
          <div class="content-box">{{ detailData.content }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledgeApi } from '@/api/request'

const loading = ref(false)
const importing = ref(false)
const showImport = ref(false)
const showDetail = ref(false)
const knowledge = ref<any[]>([])
const stats = ref<any>({})
const detailData = ref<any>({})
const searchKeyword = ref('')

const filter = ref({
  sourceType: '',
  category: '',
})

const importForm = ref({
  title: '',
  content: '',
  source: '',
  category: '',
  tags: [] as string[],
})

const animatedStats = reactive({
  total: 0,
  official: 0,
  csdn: 0,
  manual: 0,
  arxiv: 0,
  github: 0,
})

const sourceLabels: Record<string, string> = {
  official: '官方文档',
  csdn: 'CSDN',
  arxiv: 'arXiv',
  github: 'GitHub',
  manual: '手动导入',
}

const getSourceLabel = (type: string) => sourceLabels[type] || type

const filteredKnowledge = computed(() => {
  if (!searchKeyword.value) return knowledge.value
  const keyword = searchKeyword.value.toLowerCase()
  return knowledge.value.filter(item =>
    item.title?.toLowerCase().includes(keyword) ||
    item.content?.toLowerCase().includes(keyword)
  )
})

const formatTime = (time: string) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const animateStats = () => {
  const targetStats = {
    total: stats.value.total || 0,
    official: stats.value.by_type?.official || 0,
    csdn: stats.value.by_type?.csdn || 0,
    manual: stats.value.by_type?.manual || 0,
    arxiv: stats.value.by_type?.arxiv || 0,
    github: stats.value.by_type?.github || 0,
  }

  const duration = 1000
  const steps = 30
  const interval = duration / steps

  let step = 0
  const timer = setInterval(() => {
    step++
    const progress = step / steps
    const easeProgress = 1 - Math.pow(1 - progress, 3)

    animatedStats.total = Math.round(targetStats.total * easeProgress)
    animatedStats.official = Math.round(targetStats.official * easeProgress)
    animatedStats.csdn = Math.round(targetStats.csdn * easeProgress)
    animatedStats.manual = Math.round(targetStats.manual * easeProgress)
    animatedStats.arxiv = Math.round(targetStats.arxiv * easeProgress)
    animatedStats.github = Math.round(targetStats.github * easeProgress)

    if (step >= steps) {
      clearInterval(timer)
      Object.assign(animatedStats, targetStats)
    }
  }, interval)
}

const loadStats = async () => {
  try {
    stats.value = await knowledgeApi.getStats()
    animateStats()
  } catch (e) {
    console.error(e)
  }
}

const loadKnowledge = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (filter.value.sourceType) params.source_type = filter.value.sourceType
    if (filter.value.category) params.category = filter.value.category
    knowledge.value = await knowledgeApi.getAll(params)
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

const viewDetail = (row: any) => {
  detailData.value = row
  showDetail.value = true
}

const deleteKnowledge = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定删除该知识条目？', '提示', { type: 'warning' })
    await knowledgeApi.delete(row.id)
    ElMessage.success('删除成功')
    loadKnowledge()
    loadStats()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message)
    }
  }
}

const doImport = async () => {
  if (!importForm.value.title || !importForm.value.content) {
    ElMessage.warning('请填写标题和内容')
    return
  }

  importing.value = true
  try {
    await knowledgeApi.create({
      ...importForm.value,
      source_type: 'manual',
    })
    ElMessage.success('导入成功')
    showImport.value = false
    loadKnowledge()
    loadStats()
    resetImportForm()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    importing.value = false
  }
}

const triggerCrawl = () => {
  ElMessage.info('爬虫功能开发中...')
}

const resetImportForm = () => {
  importForm.value = {
    title: '',
    content: '',
    source: '',
    category: '',
    tags: [],
  }
}

onMounted(() => {
  loadStats()
  loadKnowledge()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  position: relative;
  z-index: 1;
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.stat-card.stat-total::before { background: linear-gradient(90deg, #667eea, #764ba2); }
.stat-card.stat-official::before { background: linear-gradient(90deg, #10b981, #059669); }
.stat-card.stat-csdn::before { background: linear-gradient(90deg, #f97316, #ea580c); }
.stat-card.stat-manual::before { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.stat-card.stat-arxiv::before { background: linear-gradient(90deg, #8b5cf6, #7c3aed); }
.stat-card.stat-github::before { background: linear-gradient(90deg, #6b7280, #4b5563); }

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-total .stat-icon { background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%); }
.stat-official .stat-icon { background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); }
.stat-csdn .stat-icon { background: linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%); }
.stat-manual .stat-icon { background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); }
.stat-arxiv .stat-icon { background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%); }
.stat-github .stat-icon { background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); }

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.stat-trend {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 14px;
}

.stat-trend.up {
  color: #10b981;
}

/* 主卡片 */
.main-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.main-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  font-size: 28px;
}

.header-info h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.header-info p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #9ca3af;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.import-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 10px;
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.import-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.35);
}

.crawl-btn {
  background: #f3f4f6;
  border: none;
  border-radius: 10px;
  color: #6b7280;
  padding: 10px 20px;
}

.crawl-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

/* 筛选区域 */
.filter-section {
  display: flex;
  gap: 20px;
  padding: 20px 24px;
  background: #f9fafb;
  border-radius: 12px;
  margin: 20px 24px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;
}

.filter-select {
  width: 140px;
}

.filter-item.search {
  margin-left: auto;
}

.search-input {
  width: 240px;
}

.filter-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.source-dot.official { background: #10b981; }
.source-dot.csdn { background: #f97316; }
.source-dot.arxiv { background: #8b5cf6; }
.source-dot.github { background: #6b7280; }
.source-dot.manual { background: #3b82f6; }

/* 表格样式 */
.knowledge-table {
  --el-table-header-bg-color: #f9fafb;
  --el-table-row-hover-bg-color: #fafafa;
}

.knowledge-table :deep(.el-table__header th) {
  font-weight: 600;
  font-size: 13px;
  color: #6b7280;
  padding: 14px 0;
}

.knowledge-table :deep(.el-table__body td) {
  padding: 14px 0;
  vertical-align: middle;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-indicator {
  width: 4px;
  height: 24px;
  border-radius: 2px;
  flex-shrink: 0;
}

.source-indicator.official { background: #10b981; }
.source-indicator.csdn { background: #f97316; }
.source-indicator.arxiv { background: #8b5cf6; }
.source-indicator.github { background: #6b7280; }
.source-indicator.manual { background: #3b82f6; }

.title-text {
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.source-badge.official {
  background: #d1fae5;
  color: #059669;
}

.source-badge.csdn {
  background: #ffedd5;
  color: #ea580c;
}

.source-badge.arxiv {
  background: #ede9fe;
  color: #7c3aed;
}

.source-badge.github {
  background: #f3f4f6;
  color: #4b5563;
}

.source-badge.manual {
  background: #dbeafe;
  color: #2563eb;
}

.category-tag {
  background: #f3f4f6;
  border: none;
  color: #6b7280;
  border-radius: 6px;
}

.tags-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.tag-item {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: none;
  color: #0369a1;
  border-radius: 4px;
  font-size: 11px;
}

.tag-more {
  font-size: 11px;
  color: #9ca3af;
}

.time-text {
  font-size: 13px;
  color: #9ca3af;
}

.action-btns {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.action-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  border: none;
}

.action-btn.view {
  background: #eff6ff;
  color: #3b82f6;
}

.action-btn.view:hover {
  background: #dbeafe;
}

.action-btn.delete {
  background: #fef2f2;
  color: #ef4444;
}

.action-btn.delete:hover {
  background: #fee2e2;
}

/* 导入弹窗 */
.import-dialog :deep(.el-dialog) {
  border-radius: 16px;
}

.import-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.import-dialog :deep(.el-dialog__title) {
  font-weight: 600;
  color: #1f2937;
}

.import-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.content-input :deep(.el-textarea__inner) {
  border-radius: 10px;
  font-family: inherit;
  line-height: 1.6;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.submit-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 10px;
  padding: 10px 24px;
}

/* 详情弹窗 */
.detail-dialog :deep(.el-dialog) {
  border-radius: 16px;
}

.detail-dialog :deep(.el-dialog__header) {
  display: none;
}

.detail-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.detail-content {
  padding: 24px;
}

.detail-header {
  margin-bottom: 20px;
}

.detail-source {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 12px;
}

.detail-source.official { background: #d1fae5; color: #059669; }
.detail-source.csdn { background: #ffedd5; color: #ea580c; }
.detail-source.arxiv { background: #ede9fe; color: #7c3aed; }
.detail-source.github { background: #f3f4f6; color: #4b5563; }
.detail-source.manual { background: #dbeafe; color: #2563eb; }

.detail-title {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.detail-meta {
  display: flex;
  gap: 20px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.detail-tag {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: none;
  color: #0369a1;
  border-radius: 6px;
}

.detail-source-url {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 13px;
}

.detail-source-url a {
  color: #3b82f6;
  text-decoration: none;
}

.detail-source-url a:hover {
  text-decoration: underline;
}

.detail-body {
  border-top: 1px solid #f3f4f6;
  padding-top: 20px;
}

.content-label {
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 12px;
}

.content-box {
  background: #f9fafb;
  border-radius: 12px;
  padding: 20px;
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
}
</style>
