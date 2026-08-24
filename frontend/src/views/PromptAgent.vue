<template>
  <div class="page-container">
    <el-row :gutter="24" class="main-row">
      <!-- 左侧输入区域 -->
      <el-col :span="10">
        <el-card class="form-card">
          <template #header>
            <div class="card-header">
              <div class="header-icon prompt-icon">✨</div>
              <div class="header-info">
                <h3>提示词优化 Agent</h3>
                <p>智能优化您的 AI 提示词</p>
              </div>
            </div>
          </template>

          <el-form :model="form" label-width="90px" class="prompt-form">
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

            <el-form-item label="需求描述">
              <el-input
                v-model="form.userInput"
                type="textarea"
                :rows="8"
                placeholder="描述您想要 AI 帮您完成的任务..."
                class="input-area"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                class="generate-btn"
                @click="generate"
                :loading="loading"
                :disabled="!form.userInput"
              >
                <el-icon v-if="!loading"><MagicStick /></el-icon>
                {{ loading ? '正在生成...' : '智能优化提示词' }}
              </el-button>
            </el-form-item>
          </el-form>

          <!-- 快捷提示 -->
          <div class="quick-tips">
            <div class="tips-header">
              <el-icon><Opportunity /></el-icon>
              <span>快捷提示</span>
            </div>
            <div class="tips-list">
              <div
                v-for="tip in quickTips"
                :key="tip"
                class="tip-item"
                @click="form.userInput = tip"
              >
                {{ tip }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧结果区域 -->
      <el-col :span="14">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <div class="header-icon result-icon">📝</div>
              <div class="header-info">
                <h3>优化后的提示词</h3>
                <p>AI 为您生成的专业提示词</p>
              </div>
              <div class="header-actions" v-if="result">
                <el-button class="action-btn copy" @click="copyResult">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button class="action-btn export" @click="exportResult">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>

          <!-- 加载状态 -->
          <div v-if="loading" class="loading-container">
            <div class="loading-animation">
              <div class="loading-ring"></div>
              <div class="loading-ring"></div>
              <div class="loading-ring"></div>
            </div>
            <p class="loading-text">AI 正在优化您的提示词...</p>
          </div>

          <!-- 结果展示 -->
          <div v-else-if="result" class="result-content" v-html="resultHtml" />

          <!-- 空状态 -->
          <div v-else class="empty-container">
            <div class="empty-illustration">
              <span class="empty-icon">💡</span>
            </div>
            <h4>开始优化您的提示词</h4>
            <p>描述您的需求，AI 将帮您生成专业、清晰的提示词</p>
            <div class="feature-list">
              <div class="feature-item">
                <el-icon><Check /></el-icon>
                <span>结构化提示词</span>
              </div>
              <div class="feature-item">
                <el-icon><Check /></el-icon>
                <span>明确输出格式</span>
              </div>
              <div class="feature-item">
                <el-icon><Check /></el-icon>
                <span>添加示例说明</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { modelApi } from '@/api/request'
import { marked } from 'marked'
import { WebSocketClient } from '@/api/websocket'

const loading = ref(false)
const models = ref<any[]>([])
const result = ref('')

const form = ref({
  modelId: null as number | null,
  userInput: '',
})

const quickTips = [
  '帮我写一段数据分析的 Python 代码',
  '帮我生成一份产品需求文档',
  '帮我设计一个用户注册流程',
  '帮我写一封商务邮件',
]

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

const ws = ref<WebSocketClient | null>(null)

const resultHtml = computed(() => {
  return result.value ? marked(result.value) as string : ''
})

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

const generate = async () => {
  if (!form.value.modelId) {
    ElMessage.warning('请选择模型')
    return
  }

  loading.value = true
  result.value = ''

  ws.value = new WebSocketClient(
    'prompt',
    (data) => {
      const parsed = JSON.parse(data)
      if (parsed.type === 'chunk') {
        result.value += parsed.content
      } else if (parsed.type === 'done') {
        loading.value = false
        ElMessage.success('生成完成')
      } else if (parsed.type === 'error') {
        ElMessage.error(parsed.message)
        loading.value = false
      }
    },
    (error) => {
      ElMessage.error('WebSocket 连接失败')
      loading.value = false
    }
  )

  try {
    await ws.value.connect()
    ws.value.send({
      user_input: form.value.userInput,
      model_id: form.value.modelId,
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
  const blob = new Blob([result.value], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `prompt-${Date.now()}.md`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 100)
  ElMessage.success('导出成功')
}

onMounted(loadModels)
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

/* 卡片样式 */
.form-card,
.result-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  height: 100%;
}

.form-card :deep(.el-card__header),
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

.prompt-icon {
  background: linear-gradient(135deg, #fae8ff 0%, #e9d5ff 100%);
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
  display: flex;
  gap: 8px;
}

.action-btn {
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  color: #6b7280;
  transition: all 0.2s ease;
}

.action-btn.copy:hover {
  background: #dbeafe;
  color: #3b82f6;
}

.action-btn.export:hover {
  background: #d1fae5;
  color: #10b981;
}

/* 表单样式 */
.prompt-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.input-area :deep(.el-textarea__inner) {
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  padding: 16px;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.generate-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(168, 85, 247, 0.35);
}

.generate-btn:disabled {
  background: #e5e7eb;
  color: #9ca3af;
}

/* 快捷提示 */
.quick-tips {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #f3f4f6;
}

.tips-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
}

.tips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tip-item {
  padding: 8px 14px;
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-radius: 20px;
  font-size: 12px;
  color: #7c3aed;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tip-item:hover {
  background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
  transform: translateY(-1px);
}

/* 结果区域 */
.result-card :deep(.el-card__body) {
  height: calc(100% - 80px);
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

/* 加载动画 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.loading-animation {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 24px;
}

.loading-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #a855f7;
  animation: spin 1.2s linear infinite;
}

.loading-ring:nth-child(2) {
  width: 70%;
  height: 70%;
  top: 15%;
  left: 15%;
  border-top-color: #c084fc;
  animation-delay: -0.4s;
}

.loading-ring:nth-child(3) {
  width: 40%;
  height: 40%;
  top: 30%;
  left: 30%;
  border-top-color: #e9d5ff;
  animation-delay: -0.8s;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
  padding: 40px 0;
}

.empty-illustration {
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.empty-icon {
  font-size: 40px;
}

.empty-container h4 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #374151;
}

.empty-container p {
  margin: 0 0 24px;
  font-size: 14px;
  color: #9ca3af;
  text-align: center;
}

.feature-list {
  display: flex;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #f9fafb;
  border-radius: 20px;
  font-size: 13px;
  color: #6b7280;
}

.feature-item .el-icon {
  color: #10b981;
}
</style>
