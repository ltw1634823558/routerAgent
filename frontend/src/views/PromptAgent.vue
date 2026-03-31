<template>
  <div class="page-container">
    <el-row :gutter="20">
      <!-- 输入区域 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <h3>✨ 提示词优化 Agent</h3>
          </template>
          <el-form :model="form" label-width="100px">
            <el-form-item label="使用模型">
              <el-select v-model="form.modelId" style="width: 100%">
                <el-option
                  v-for="m in models"
                  :key="m.id"
                  :label="m.name"
                  :value="m.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="描述需求">
              <el-input
                v-model="form.userInput"
                type="textarea"
                :rows="6"
                placeholder="描述你想要 AI 帮你完成的任务，Agent 会帮你生成优化的提示词..."
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="generate"
                :loading="loading"
                :disabled="!form.userInput"
              >
                生成提示词
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 结果区域 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="result-header">
              <h3>📝 生成的提示词</h3>
              <div>
                <el-button @click="copyResult" :disabled="!result">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button @click="exportResult" :disabled="!result">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>
          <div class="result-content" v-html="resultHtml" v-if="result" />
          <el-empty v-else description="生成的提示词将显示在这里" />
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

const resultHtml = computed(() => {
  return result.value ? marked(result.value) : ''
  })
 const ws = ref<WebSocketClient | null>(null)

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

  // 创建 WebSocket 连接
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
    
    // 发送生成请求
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
    a.download = url
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
  })
 onMounted(loadModels)
</script>

<style scoped>
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
 .result-header h3 {
  margin: 0;
}
 .result-content {
  line-height: 1.8;
}
</style>
