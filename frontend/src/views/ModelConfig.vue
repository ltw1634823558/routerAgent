<template>
  <div class="page-container">
    <!-- 顶部统计卡片 -->
    <div class="stats-row">
      <div class="stat-card stat-total">
        <div class="stat-icon">
          <el-icon><Collection /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ models.length }}</span>
          <span class="stat-label">模型总数</span>
        </div>
      </div>
      <div class="stat-card stat-active">
        <div class="stat-icon">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ activeCount }}</span>
          <span class="stat-label">已配置</span>
        </div>
      </div>
      <div class="stat-card stat-default">
        <div class="stat-icon">
          <el-icon><Star /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ defaultModel?.name || '未设置' }}</span>
          <span class="stat-label">默认模型</span>
        </div>
      </div>
    </div>

    <!-- 模型列表 -->
    <el-card class="model-card">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <h2>🤖 模型配置管理</h2>
            <p class="header-desc">配置和管理您的 AI 模型 API</p>
          </div>
          <el-button type="primary" class="add-btn" @click="showDialog = true">
            <el-icon><Plus /></el-icon>
            添加模型
          </el-button>
        </div>
      </template>

      <el-table :data="models" v-loading="loading" class="model-table">
        <el-table-column prop="name" label="配置名称" min-width="150">
          <template #default="{ row }">
            <div class="model-name">
              <span class="model-dot" :style="{ background: getProviderColor(row.provider) }"></span>
              {{ row.name }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="provider" label="提供商" min-width="120">
          <template #default="{ row }">
            <el-tag class="provider-tag" :style="{ background: getProviderColor(row.provider), borderColor: getProviderColor(row.provider) }">
              {{ getProviderLabel(row.provider) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型名称" min-width="140">
          <template #default="{ row }">
            <code class="model-code">{{ row.model_name }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="api_url" label="API 地址" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="api-url">{{ row.api_url }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_default" label="状态" width="120" align="center">
          <template #default="{ row }">
            <div v-if="row.is_default" class="default-badge">
              <el-icon><Star /></el-icon>
              <span>默认</span>
            </div>
            <span v-else class="status-normal">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button class="action-btn edit" @click="editModel(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button
                v-if="!row.is_default"
                class="action-btn default"
                @click="setDefault(row)"
              >
                <el-icon><Star /></el-icon>
                设为默认
              </el-button>
              <el-button class="action-btn delete" @click="deleteModel(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑弹窗 -->
    <el-dialog
      v-model="showDialog"
      :title="isEdit ? '✏️ 编辑模型' : '➕ 添加模型'"
      width="550px"
      class="model-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-width="100px" class="model-form">
        <el-form-item label="配置名称" required>
          <el-input v-model="form.name" placeholder="如：智谱 GLM-4">
            <template #prefix>
              <el-icon><Document /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="提供商" required>
          <el-select v-model="form.provider" placeholder="选择提供商" style="width: 100%">
            <el-option label="智谱 AI" value="zhipu">
              <div class="provider-option">
                <span class="provider-dot" style="background: #10b981"></span>
                智谱 AI
              </div>
            </el-option>
            <el-option label="阿里通义" value="alibaba">
              <div class="provider-option">
                <span class="provider-dot" style="background: #f97316"></span>
                阿里通义
              </div>
            </el-option>
            <el-option label="百度文心" value="baidu">
              <div class="provider-option">
                <span class="provider-dot" style="background: #3b82f6"></span>
                百度文心
              </div>
            </el-option>
            <el-option label="讯飞星火" value="xunfei">
              <div class="provider-option">
                <span class="provider-dot" style="background: #ec4899"></span>
                讯飞星火
              </div>
            </el-option>
            <el-option label="腾讯混元" value="tencent">
              <div class="provider-option">
                <span class="provider-dot" style="background: #06b6d4"></span>
                腾讯混元
              </div>
            </el-option>
            <el-option label="月之暗面" value="moonshot">
              <div class="provider-option">
                <span class="provider-dot" style="background: #8b5cf6"></span>
                月之暗面
              </div>
            </el-option>
            <el-option label="MiniMax" value="minimax">
              <div class="provider-option">
                <span class="provider-dot" style="background: #f59e0b"></span>
                MiniMax
              </div>
            </el-option>
            <el-option label="DeepSeek" value="deepseek">
              <div class="provider-option">
                <span class="provider-dot" style="background: #ef4444"></span>
                DeepSeek
              </div>
            </el-option>
            <el-option label="自定义" value="custom">
              <div class="provider-option">
                <span class="provider-dot" style="background: #6b7280"></span>
                自定义
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" required>
          <el-input v-model="form.model_name" placeholder="如：glm-4">
            <template #prefix>
              <el-icon><Cpu /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="API 地址" required>
          <el-input v-model="form.api_url" placeholder="如：https://open.bigmodel.cn/api/paas/v4">
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="API KEY" required>
          <el-input
            v-model="form.api_key_env"
            placeholder="环境变量名，如：ZHIPU_API_KEY"
          >
            <template #prefix>
              <el-icon><Key /></el-icon>
            </template>
          </el-input>
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            请在 .env 文件中配置对应的环境变量值
          </div>
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" active-color="#667eea" />
        </el-form-item>
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

const form = ref({
  name: '',
  provider: '',
  model_name: '',
  api_url: '',
  api_key_env: '',
  is_default: false,
})

const activeCount = computed(() => models.value.filter(m => m.api_key_env).length)
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
    resetForm()
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

const resetForm = () => {
  form.value = {
    name: '',
    provider: '',
    model_name: '',
    api_url: '',
    api_key_env: '',
    is_default: false,
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
</style>
