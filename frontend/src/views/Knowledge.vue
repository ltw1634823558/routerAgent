<template>
  <div class="page-container">
    <el-row :gutter="20">
      <!-- 统计区域 -->
      <el-col :span="24">
        <el-card class="stats-card">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="知识总数" :value="stats.total || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="官方文档" :value="stats.by_type?.official || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="CSDN" :value="stats.by_type?.csdn || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="手动导入" :value="stats.by_type?.manual || 0" />
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <!-- 操作区域 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <h3>📚 知识库管理</h3>
              <div>
                <el-button type="primary" @click="showImport = true">
                  <el-icon><Upload /></el-icon>
                  手动导入
                </el-button>
                <el-button @click="triggerCrawl">
                  <el-icon><Refresh /></el-icon>
                  自动爬取
                </el-button>
              </div>
            </div>
          </template>

          <!-- 筛选 -->
          <el-form :inline="true" class="filter-form">
            <el-form-item label="来源类型">
              <el-select v-model="filter.sourceType" @change="loadKnowledge" clearable>
                <el-option label="官方文档" value="official" />
                <el-option label="CSDN" value="csdn" />
                <el-option label="arXiv" value="arxiv" />
                <el-option label="GitHub" value="github" />
                <el-option label="手动导入" value="manual" />
              </el-select>
            </el-form-item>
            <el-form-item label="分类">
              <el-select v-model="filter.category" @change="loadKnowledge" clearable>
                <el-option
                  v-for="cat in Object.keys(stats.by_category || {})"
                  :key="cat"
                  :label="cat"
                  :value="cat"
                />
              </el-select>
            </el-form-item>
          </el-form>

          <!-- 列表 -->
          <el-table :data="knowledge" v-loading="loading" stripe>
            <el-table-column prop="title" label="标题" show-overflow-tooltip />
            <el-table-column prop="source_type" label="来源" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ getSourceLabel(row.source_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column prop="created_at" label="添加时间" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button link type="primary" @click="viewDetail(row)">查看</el-button>
                <el-button link type="danger" @click="deleteKnowledge(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 导入弹窗 -->
    <el-dialog v-model="showImport" title="手动导入知识" width="600px">
      <el-form :model="importForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="importForm.title" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="importForm.content" type="textarea" :rows="10" />
        </el-form-item>
        <el-form-item label="来源URL">
          <el-input v-model="importForm.source" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="importForm.category" placeholder="如：大模型算法、智能体开发" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="importForm.tags" multiple filterable allow-create style="width: 100%">
            <el-option label="Python" value="Python" />
            <el-option label="PyTorch" value="PyTorch" />
            <el-option label="Transformer" value="Transformer" />
            <el-option label="RAG" value="RAG" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showImport = false">取消</el-button>
        <el-button type="primary" @click="doImport" :loading="importing">导入</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="showDetail" title="知识详情" width="700px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="标题">{{ detailData.title }}</el-descriptions-item>
        <el-descriptions-item label="来源">{{ detailData.source }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ detailData.category }}</el-descriptions-item>
        <el-descriptions-item label="标签">
          <el-tag v-for="tag in detailData.tags" :key="tag" style="margin-right: 5px">{{ tag }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="内容">
          <div class="content-box">{{ detailData.content }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledgeApi } from '@/api/request'

const loading = ref(false)
const importing = ref(false)
const showImport = ref(false)
const showDetail = ref(false)
const knowledge = ref<any[]>([])
const stats = ref<any>({})
const detailData = ref<any>({})

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

const sourceLabels: Record<string, string> = {
  official: '官方文档',
  csdn: 'CSDN',
  arxiv: 'arXiv',
  github: 'GitHub',
  manual: '手动导入',
}

const getSourceLabel = (type: string) => sourceLabels[type] || type

const loadStats = async () => {
  try {
    stats.value = await knowledgeApi.getStats()
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
.stats-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
}

.filter-form {
  margin-bottom: 20px;
}

.content-box {
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
}
</style>
