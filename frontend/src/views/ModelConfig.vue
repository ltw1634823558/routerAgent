<template>
  <div class="page-container">
    <header class="page-header">
      <div class="page-heading">
        <div class="page-icon">
          <el-icon><Setting /></el-icon>
        </div>
        <div>
          <h1>模型配置</h1>
          <p>统一管理 Agent 使用的模型服务与 API 配置</p>
        </div>
      </div>
      <el-button type="primary" class="add-btn" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        添加模型
      </el-button>
    </header>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon total-icon">
          <el-icon><Collection /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ models.length }}</span>
          <span class="stat-label">模型配置</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon provider-icon">
          <el-icon><Connection /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ providerCount }}</span>
          <span class="stat-label">服务提供商</span>
        </div>
      </div>
      <div class="stat-card default-stat">
        <div class="stat-icon default-icon">
          <el-icon><Star /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ defaultModel?.name || '未设置' }}</span>
          <span class="stat-label">默认模型</span>
        </div>
      </div>
    </div>

    <section class="model-panel">
      <div class="panel-toolbar">
        <div class="panel-title">
          <h2>模型列表</h2>
          <span>{{ filteredModels.length }} 项</span>
        </div>
        <div class="filters">
          <el-input
            v-model="keyword"
            clearable
            class="search-input"
            placeholder="搜索配置或模型名称"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="providerFilter" clearable class="provider-filter" placeholder="全部提供商">
            <el-option
              v-for="provider in providers"
              :key="provider.value"
              :label="provider.label"
              :value="provider.value"
            />
          </el-select>
        </div>
      </div>

      <el-table :data="filteredModels" v-loading="loading" class="model-table" empty-text="暂无匹配的模型配置">
        <el-table-column prop="name" label="配置名称" min-width="190">
          <template #default="{ row }">
            <div class="model-name">
              <span class="model-mark" :style="{ color: getProviderColor(row.provider), backgroundColor: `${getProviderColor(row.provider)}14` }">
                <el-icon><Cpu /></el-icon>
              </span>
              <div class="model-name-text">
                <strong>{{ row.name }}</strong>
                <span v-if="row.is_default">默认使用</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="provider" label="提供商" min-width="130">
          <template #default="{ row }">
            <el-tag class="provider-tag" :style="{ color: getProviderColor(row.provider), backgroundColor: `${getProviderColor(row.provider)}12`, borderColor: `${getProviderColor(row.provider)}32` }">
              {{ getProviderLabel(row.provider) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型标识" min-width="160">
          <template #default="{ row }">
            <code class="model-code">{{ row.model_name }}</code>
          </template>
        </el-table-column>
        <el-table-column label="能力" min-width="170">
          <template #default="{ row }">
            <div class="capability-tags">
              <el-tag v-for="capability in getCapabilities(row)" :key="capability" size="small" effect="plain">
                {{ capabilityLabels[capability] || capability }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="连接状态" width="112">
          <template #default="{ row }">
            <span v-if="testStatus[row.id]" class="connection-status" :class="testStatus[row.id].success ? 'success' : 'failed'">
              <el-icon><CircleCheck v-if="testStatus[row.id].success" /><CircleClose v-else /></el-icon>
              {{ testStatus[row.id].success ? `${testStatus[row.id].latency_ms} ms` : '失败' }}
            </span>
            <span v-else class="connection-status unknown"><el-icon><QuestionFilled /></el-icon>未测试</span>
          </template>
        </el-table-column>
        <el-table-column prop="api_url" label="API 地址" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="api-url"><el-icon><Link /></el-icon><span>{{ row.api_url }}</span></div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="188" align="right" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-tooltip content="测试连接" placement="top">
                <el-button class="action-btn test" aria-label="测试连接" :loading="testingId === row.id" @click="testConnection(row)"><el-icon><Connection /></el-icon></el-button>
              </el-tooltip>
              <el-tooltip content="编辑配置" placement="top">
                <el-button class="action-btn" aria-label="编辑配置" @click="editModel(row)"><el-icon><Edit /></el-icon></el-button>
              </el-tooltip>
              <el-tooltip v-if="!row.is_default" content="设为默认模型" placement="top">
                <el-button class="action-btn default" aria-label="设为默认模型" @click="setDefault(row)"><el-icon><Star /></el-icon></el-button>
              </el-tooltip>
              <el-tooltip content="删除配置" placement="top">
                <el-button class="action-btn delete" aria-label="删除配置" @click="deleteModel(row)"><el-icon><Delete /></el-icon></el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="showDialog"
      :title="isEdit ? '编辑模型配置' : '添加模型配置'"
      width="640px"
      class="model-dialog"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <p class="dialog-desc">填写模型服务信息，API Key 的实际值由后端环境变量读取。</p>
      <el-form :model="form" label-position="top" class="model-form">
        <div class="form-grid">
          <el-form-item label="配置名称" required>
            <el-input v-model="form.name" placeholder="如：生产环境 GLM-4" />
          </el-form-item>
          <el-form-item label="提供商" required>
          <el-select v-model="form.provider" placeholder="选择提供商" style="width: 100%">
            <el-option v-for="provider in providers" :key="provider.value" :label="provider.label" :value="provider.value">
              <div class="provider-option">
                <span class="provider-dot" :style="{ background: provider.color }"></span>
                {{ provider.label }}
              </div>
            </el-option>
          </el-select>
          </el-form-item>
          <el-form-item label="模型名称" required>
            <el-input v-model="form.model_name" placeholder="如：glm-4" />
          </el-form-item>
          <el-form-item label="API Key 环境变量名" required>
            <el-input v-model="form.api_key_env" placeholder="如：ZHIPU_API_KEY" />
          </el-form-item>
        </div>
        <el-form-item label="API 地址" required>
          <el-input v-model="form.api_url" placeholder="如：https://open.bigmodel.cn/api/paas/v4" />
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            请在 .env 文件中配置对应的环境变量值
          </div>
        </el-form-item>
        <div class="form-grid advanced-fields">
          <el-form-item label="模型能力">
            <el-select v-model="form.capabilities" multiple clearable filterable placeholder="选择该模型支持的能力" style="width: 100%">
              <el-option v-for="capability in capabilityOptions" :key="capability.value" :label="capability.label" :value="capability.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="故障切换优先级">
            <el-input-number v-model="form.priority" :min="0" :max="10000" controls-position="right" style="width: 100%" />
            <div class="form-tip">数字越小，自动切换时越优先</div>
          </el-form-item>
          <el-form-item label="备用模型">
            <el-select v-model="form.fallback_model_ids" multiple clearable filterable placeholder="可选，失败时依次尝试" style="width: 100%">
              <el-option v-for="model in fallbackCandidates" :key="model.id" :label="`${model.name} (${model.model_name})`" :value="model.id" />
            </el-select>
          </el-form-item>
        </div>
        <div class="default-setting">
          <div><strong>启用模型</strong><span>停用后不会被 Agent 或故障切换使用</span></div>
          <el-switch v-model="form.enabled" />
        </div>
        <div class="default-setting">
          <div><strong>设为默认模型</strong><span>新建 Agent 任务时优先使用此配置</span></div>
          <el-switch v-model="form.is_default" />
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showDialog = false">取消</el-button>
          <el-button type="primary" @click="saveModel" :loading="saving" class="save-btn">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { modelApi } from '@/api/request'

const loading = ref(false)
const saving = ref(false)
const models = ref<any[]>([])
const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const keyword = ref('')
const providerFilter = ref('')
const testingId = ref<number | null>(null)
const testStatus = ref<Record<number, { success: boolean; latency_ms?: number; message?: string }>>({})

const form = ref({
  name: '',
  provider: '',
  model_name: '',
  api_url: '',
  api_key_env: '',
  is_default: false,
  capabilities: [] as string[],
  priority: 100,
  enabled: true,
  fallback_model_ids: [] as number[],
})

const providerCount = computed(() => new Set(models.value.map(m => m.provider)).size)
const defaultModel = computed(() => models.value.find(m => m.is_default))

const providerLabels: Record<string, string> = {
  zhipu: '智谱 AI',
  alibaba: '阿里通义',
  baidu: '百度文心',
  xunfei: '讯飞星火',
  tencent: '腾讯混元',
  moonshot: '月之暗面',
  minimax: 'MiniMax',
  deepseek: 'DeepSeek',
  custom: '自定义',
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

const providers = Object.entries(providerLabels).map(([value, label]) => ({
  value,
  label,
  color: providerColors[value],
}))

const filteredModels = computed(() => {
  const search = keyword.value.trim().toLowerCase()
  return models.value.filter((model) => {
    const matchesProvider = !providerFilter.value || model.provider === providerFilter.value
    const matchesSearch = !search || [model.name, model.model_name, model.api_url].some((value) => String(value || '').toLowerCase().includes(search))
    return matchesProvider && matchesSearch
  })
})

const fallbackCandidates = computed(() => models.value.filter((model) => model.id !== editId.value && model.enabled !== false))

const capabilityLabels: Record<string, string> = {
  chat: '对话',
  stream: '流式',
  vision: '视觉',
  reasoning: '推理',
  tools: '工具调用',
  function_calling: '函数调用',
}

const capabilityOptions = Object.entries(capabilityLabels).map(([value, label]) => ({ value, label }))

const providerCapabilities: Record<string, string[]> = {
  zhipu: ['chat', 'stream', 'vision'],
  alibaba: ['chat', 'stream', 'vision'],
  baidu: ['chat', 'stream'],
  xunfei: ['chat', 'stream'],
  tencent: ['chat', 'stream'],
  moonshot: ['chat', 'stream'],
  minimax: ['chat', 'stream', 'vision'],
  deepseek: ['chat', 'stream', 'reasoning'],
  custom: ['chat', 'stream'],
}

const getCapabilities = (model: any): string[] => {
  const values = Array.isArray(model.capabilities) ? model.capabilities.filter(Boolean) : []
  return values.length ? values : (providerCapabilities[model.provider] || ['chat'])
}

const getProviderLabel = (provider: string) => providerLabels[provider] || provider
const getProviderColor = (provider: string) => providerColors[provider] || '#6b7280'

const loadModels = async () => {
  loading.value = true
  try {
    models.value = await modelApi.getAll()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

const editModel = (row: any) => {
  isEdit.value = true
  editId.value = row.id
  form.value = { ...row }
  showDialog.value = true
}

const openCreateDialog = () => {
  resetForm()
  showDialog.value = true
}

const saveModel = async () => {
  if (!form.value.name || !form.value.provider || !form.value.model_name) {
    ElMessage.warning('请填写必填项')
    return
  }

  saving.value = true
  try {
    if (isEdit.value && editId.value) {
      await modelApi.update(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await modelApi.create(form.value)
      ElMessage.success('添加成功')
    }
    showDialog.value = false
    loadModels()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

const deleteModel = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定删除该模型配置？', '提示', { type: 'warning' })
    await modelApi.delete(row.id)
    ElMessage.success('删除成功')
    loadModels()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message)
    }
  }
}

const setDefault = async (row: any) => {
  try {
    await modelApi.setDefault(row.id)
    ElMessage.success('设置成功')
    loadModels()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

const testConnection = async (row: any) => {
  testingId.value = row.id
  try {
    const result: any = await modelApi.testConnection(row.id)
    testStatus.value[row.id] = result
    if (result.success) {
      ElMessage.success(`连接成功${result.latency_ms ? `，耗时 ${result.latency_ms} ms` : ''}`)
    } else {
      ElMessage.error(result.message || '连接失败')
    }
  } catch (e: any) {
    testStatus.value[row.id] = { success: false, message: e.message }
    ElMessage.error(e.message)
  } finally {
    testingId.value = null
  }
}

const resetForm = () => {
  form.value = {
    name: '',
    provider: '',
    model_name: '',
    api_url: '',
    api_key_env: '',
    is_default: false,
    capabilities: [],
    priority: 100,
    enabled: true,
    fallback_model_ids: [],
  }
  isEdit.value = false
  editId.value = null
}

onMounted(loadModels)
</script>

<style scoped>
.page-container {
  height: 100%;
  position: relative;
  z-index: 1;
}

/* 统计卡片 */
.stats-row {
  display: flex;
  flex-direction: row;
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  flex: 1;
  min-width: 0;
  max-width: 100%;
}

.stat-card:last-child {
  flex: 1.2;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #fff;
  flex-shrink: 0;
}

.stat-total .stat-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-active .stat-icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.stat-default .stat-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  flex: 1;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat-label {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

/* 模型卡片 */
.model-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.model-card :deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.model-card :deep(.el-card__body) {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.header-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #9ca3af;
}

.add-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 10px;
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

/* 表格样式 */
.model-table {
  --el-table-header-bg-color: #f9fafb;
  --el-table-header-text-color: #6b7280;
  --el-table-row-hover-bg-color: #f9fafb;
}

.model-table :deep(.el-table__header th) {
  font-weight: 600;
  font-size: 13px;
  padding: 16px 0;
}

.model-table :deep(.el-table__body td) {
  padding: 16px 0;
  vertical-align: middle;
}

.model-name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 500;
  color: #1f2937;
}

.model-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.provider-tag {
  color: #fff;
  border-radius: 6px;
  font-size: 12px;
}

.model-code {
  background: #f3f4f6;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #4b5563;
}

.api-url {
  color: #6b7280;
  font-size: 13px;
}

.default-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-normal {
  color: #d1d5db;
}

/* 操作按钮 */
.action-btns {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.action-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.edit {
  background: #eff6ff;
  color: #3b82f6;
}

.action-btn.edit:hover {
  background: #dbeafe;
}

.action-btn.default {
  background: #fef3c7;
  color: #d97706;
}

.action-btn.default:hover {
  background: #fde68a;
}

.action-btn.test {
  background: #eef4ff;
  color: #356ae6;
}

.action-btn.test:hover {
  background: #dbe8ff;
}

.action-btn.delete {
  background: #fee2e2;
  color: #ef4444;
}

.action-btn.delete:hover {
  background: #fecaca;
}

/* 弹窗样式 */
.model-dialog :deep(.el-dialog) {
  border-radius: 16px;
}

.model-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.model-dialog :deep(.el-dialog__title) {
  font-weight: 600;
  color: #1f2937;
}

.model-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.model-form :deep(.el-input__wrapper) {
  border-radius: 8px;
}

.provider-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.provider-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 6px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.save-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  padding: 10px 24px;
}

.save-btn:hover {
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

/* 模型配置页布局优化 */
.page-container { min-height: 100%; }
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:22px; }
.page-heading { display:flex; align-items:center; gap:14px; }
.page-icon { width:44px; height:44px; display:grid; place-items:center; border-radius:12px; background:#eaf2ff; color:#356ae6; font-size:21px; }
.page-heading h1 { margin:0; color:#172033; font-size:24px; }
.page-heading p { margin:5px 0 0; color:#7b8496; font-size:13px; }
.stats-row { gap:14px; margin-bottom:18px; }
.stat-card { border:1px solid #e9edf4; box-shadow:0 2px 8px rgba(29,42,68,.035); padding:15px 18px; }
.default-stat { flex:1.3; }
.total-icon { background:#eaf2ff !important; color:#356ae6; }
.provider-icon { background:#eaf8f2 !important; color:#15966b; }
.default-icon { background:#fff5dc !important; color:#c98308; }
.model-panel { overflow:hidden; border:1px solid #e9edf4; border-radius:14px; background:#fff; box-shadow:0 5px 22px rgba(29,42,68,.045); }
.panel-toolbar { display:flex; justify-content:space-between; align-items:center; gap:20px; padding:17px 20px; border-bottom:1px solid #eef1f5; }
.panel-title { display:flex; align-items:baseline; gap:9px; }
.panel-title h2 { margin:0; color:#202a3b; font-size:16px; }
.panel-title span { color:#98a1b2; font-size:12px; }
.filters { display:flex; gap:10px; }
.search-input { width:230px; }
.provider-filter { width:135px; }
.add-btn { background:#356ae6; border:none; border-radius:8px; padding:9px 16px; }
.add-btn:hover { background:#2857c7; }
.model-table :deep(.el-table__inner-wrapper::before) { display:none; }
.model-table :deep(.el-table__header th) { padding:13px 0; }
.model-table :deep(.el-table__body td) { padding:14px 0; }
.model-mark { width:32px; height:32px; display:grid; place-items:center; border-radius:8px; font-size:16px; }
.model-name-text { display:flex; flex-direction:column; gap:3px; }
.model-name-text strong { font-size:13px; font-weight:600; }
.model-name-text span { color:#15966b; font-size:11px; }
.provider-tag { border-radius:5px; }
.api-url { display:flex; align-items:center; gap:6px; }
.api-url .el-icon { color:#a7afbd; }
.capability-tags { display:flex; flex-wrap:wrap; gap:4px; }
.capability-tags :deep(.el-tag) { border-radius:4px; font-size:11px; }
.connection-status { display:inline-flex; align-items:center; gap:4px; font-size:12px; white-space:nowrap; }
.connection-status.success { color:#15966b; }
.connection-status.failed { color:#e14b4b; }
.connection-status.unknown { color:#98a1b2; }
.action-btns { gap:4px; }
.action-btn { width:30px; height:30px; padding:0; border:1px solid transparent; }
.action-btn:hover { border-color:currentColor; }
.dialog-desc { margin:-8px 0 20px; color:#7b8496; font-size:13px; }
.model-form :deep(.el-form-item) { margin-bottom:18px; }
.model-form :deep(.el-form-item__label) { padding-bottom:6px; color:#4b5567; font-size:13px; font-weight:600; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; column-gap:18px; }
.default-setting { display:flex; justify-content:space-between; align-items:center; margin-top:4px; padding:13px 14px; border:1px solid #e9edf4; border-radius:9px; background:#fafbfc; }
.default-setting div { display:flex; flex-direction:column; gap:3px; }
.default-setting strong { color:#2b3445; font-size:13px; }
.default-setting span { color:#9099aa; font-size:12px; }
.advanced-fields { margin-top:2px; }
@media (max-width:900px) {
  .stats-row { flex-wrap:wrap; }
  .stat-card, .default-stat { flex:1 1 calc(50% - 8px); }
  .panel-toolbar { align-items:flex-start; flex-direction:column; }
  .filters { width:100%; }
  .search-input, .provider-filter { flex:1; width:auto; }
}
@media (max-width:600px) {
  .page-header { align-items:stretch; flex-direction:column; gap:16px; }
  .add-btn { width:100%; }
  .stat-card, .default-stat { flex-basis:100%; }
  .filters { flex-direction:column; }
  .search-input, .provider-filter { width:100%; }
  .form-grid { grid-template-columns:1fr; }
}
</style>
