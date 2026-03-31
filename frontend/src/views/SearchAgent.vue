<template>
  <div class="page-container">
    <el-row :gutter="20">
      <!-- 搜索区域 -->
      <el-col :span="12">
        <el-card class="search-card">
          <template #header>
            <h3>🔍 搜集 Agent</h3>
          </template>

          <el-form :model="form" label-width="100px">
            <el-form-item label="搜索引擎">
              <el-select v-model="form.engine" style="width: 100%">
                <el-option label="DuckDuckGo (免费)" value="duckduckgo" />
                <el-option label="Tavily" value="tavily" />
                <el-option label="SerpAPI (Google)" value="serpapi" />
                <el-option label="Google" value="google" />
                <el-option label="Bing" value="bing" />
              </el-select>
            </el-form-item>
            <el-form-item label="API KEY" v-if="form.engine !== 'duckduckgo'">
              <el-input v-model="form.apiKey" type="password" show-password />
            </el-form-item>
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
            <el-form-item label="搜索内容">
              <el-input
                v-model="form.query"
                type="textarea"
                :rows="3"
                placeholder="输入要搜索的内容..."
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="doSearch"
                :loading="loading"
                :disabled="!form.query"
              >
                开始搜索
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 搜索历史 -->
        <el-card class="history-card">
          <template #header>
            <h3>📜 搜索历史</h3>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="record in history"
              :key="record.id"
              :timestamp="record.created_at"
            >
              <div class="history-item">
                <strong>{{ record.query }}</strong>
                <el-tag size="small">{{ record.engine }}</el-tag>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>

      <!-- 结果区域 -->
      <el-col :span="12">
        <el-card class="result-card">
          <template #header>
            <h3>📝 搜索结果</h3>
          </template>
          <div class="result-content" v-html="resultHtml" v-if="resultHtml" />
          <el-empty v-else description="暂无结果" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { modelApi, searchApi } from '@/api/request'
import { marked } from 'marked'
import { WebSocketClient } from '@/api/websocket'

const loading = ref(false)
const models = ref<any[]>([])
const history = ref<any[]>([])
const result = ref('')

const form = ref({
  engine: 'duckduckgo',
  apiKey: '',
  modelId: null as number | null,
  query: '',
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

 const loadHistory = async () => {
  try {
    history.value = await searchApi.getRecords(20)
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

    // 创建 WebSocket 连接
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
      (error) => {
        ElMessage.error('WebSocket 连接失败')
        loading.value = false
      }
    )

    try {
      await ws.value.connect()
      
      // 发送搜索请求
      ws.value.send({
        query: form.value.query,
        engine: form.value.engine,
        api_key: form.value.apiKey,
        model_id: form.value.modelId,
      })
    } catch (error) {
      ElMessage.error('连接失败')
      loading.value = false
    }
  }

  onMounted(() => {
    loadModels()
    loadHistory()
  })
</script>

<style scoped>
.search-card,
.history-card,
.result-card {
  margin-bottom: 20px;
}

 .result-content {
  line-height: 1.8;
}
 .history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
