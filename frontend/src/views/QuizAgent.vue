<template>
  <div class="page-container">
    <!-- 配置区域 -->
    <el-card v-if="!inQuiz">
      <template #header>
        <h3>📝 问答 Agent - AI 岗位试题</h3>
      </template>
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="技能分类">
              <el-select v-model="form.category" style="width: 100%">
                <el-option label="全部" value="" />
                <el-option
                  v-for="cat in categories"
                  :key="cat"
                  :label="cat"
                  :value="cat"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="难度">
              <el-select v-model="form.difficulty" style="width: 100%">
                <el-option label="基础" value="basic" />
                <el-option label="进阶" value="intermediate" />
                <el-option label="精通" value="advanced" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="题数">
              <el-input-number v-model="form.count" :min="1" :max="50" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="使用模型">
          <el-select v-model="form.modelId" style="width: 300px">
            <el-option
              v-for="m in models"
              :key="m.id"
              :label="m.name"
              :value="m.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="startQuiz"
            :loading="generating"
          >
            开始生成试题
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 答题区域 -->
    <el-card v-if="inQuiz && currentQuestion">
      <template #header>
        <div class="quiz-header">
          <h3>题目 {{ currentIndex + 1 }} / {{ questions.length }}</h3>
          <el-progress
            :percentage="((currentIndex + 1) / questions.length) * 100"
            :show-text="false"
            style="width: 200px"
          />
        </div>
      </template>

      <div class="question-content">
        <el-tag :type="getDifficultyType(currentQuestion.difficulty)">
          {{ getDifficultyLabel(currentQuestion.difficulty) }}
        </el-tag>
        <el-tag type="info">{{ currentQuestion.category }}</el-tag>
        <p class="question-text">{{ currentQuestion.question }}</p>

        <!-- 选择题 -->
        <el-radio-group v-if="currentQuestion.question_type === 'choice'" v-model="userAnswer">
          <el-radio
            v-for="(option, idx) in currentQuestion.options"
            :key="idx"
            :label="idx"
            class="option-item"
          >
            {{ String.fromCharCode(65 + idx) }}. {{ option }}
          </el-radio>
        </el-radio-group>

        <!-- 巫空题 -->
        <el-input
          v-if="currentQuestion.question_type === 'fill'"
          v-model="userAnswer"
          placeholder="请输入答案"
        />

        <!-- 代码题 -->
        <el-input
          v-if="currentQuestion.question_type === 'code'"
          v-model="userAnswer"
          type="textarea"
          :rows="10"
          placeholder="请输入代码..."
        />
      </div>

      <div class="quiz-actions">
        <el-button @click="prevQuestion" :disabled="currentIndex === 0">上一题</el-button>
        <el-button @click="nextQuestion" v-if="currentIndex < questions.length - 1">
          下一题
        </el-button>
        <el-button type="primary" @click="submitQuiz" v-if="currentIndex === questions.length - 1">
          提交答案
        </el-button>
      </div>
    </el-card>

    <!-- 结果区域 -->
    <el-card v-if="showResult">
      <template #header>
        <h3>🎯 独题结果</h3>
      </template>
      <el-result
        :icon="score >= 60 ? 'success' : 'warning'"
        :title="`得分：{{ score }} 分`"
        :sub-title="`共 {{ questions.length }} 题，正确 {{ correctCount }} 题`"
      />
      <div v-for="(r, results" :key="r.question_id" class="result-item">
        <p><strong>{{ r.question }}</strong></p>
        <p>你的答案: {{ r.user_answer || '未作答' }}</p>
        <p class="correct-answer"> 正确答案: {{ r.correct_answer }}</p>
        <p class="explanation">{{ r.explanation }}</p>
        <el-tag :type="r.is_correct ? 'success' : 'danger'">
          {{ r.is_correct ? '正确' : '错误' }}
        </el-tag>
      </div>
      <el-button type="primary" @click="resetQuiz">重新开始</el-button>
    </el-card>

    <!-- 答题历史 -->
    <el-card class="history-card" v-if="!inQuiz">
      <template #header>
        <h3>📊 答题历史</h3>
      </template>
      <el-table :data="history" stripe>
        <el-table-column prop="category" label="分类" />
        <el-table-column prop="difficulty" label="难度">
          <template #default="{ row }">
            {{ getDifficultyLabel(row.difficulty) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_questions" label="题数" />
        <el-table-column prop="score" label="得分" />
        <el-table-column prop="started_at" label="时间" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { modelApi, quizApi } from '@/api/request'
import { WebSocketClient } from '@/api/websocket'

const generating = ref(false)
const inQuiz = ref(false)
const showResult = ref(false)
const models = ref<any[]>([])
const categories = ref<string[]>([])
const history = ref<any[]>([])
const questions = ref<any[]>([])
const currentIndex = ref(0)
const userAnswers = ref<any[]>([])
const userAnswer = ref<any>(null)
const score = ref(0)
const correctCount = ref(0)
const results = ref<any[]>([])

 const ws = ref<WebSocketClient | null>(null)

const form = reactive({
  category: '',
  difficulty: 'basic',
  count: 5,
  modelId: null as number | null,
})
 const currentQuestion = computed(() => {
  return questions.value[currentIndex.value]
 })

 const difficultyLabels: Record<string, string> = {
  basic: '基础',
  intermediate: '进阶',
  advanced: '精通',
 }
 const getDifficultyLabel = (d: string) => difficultyLabels[d] || d
 const getDifficultyType = (d: string) => {
  const types: Record<string, string> = {
    basic: 'success',
    intermediate: 'warning',
    advanced: 'danger',
  }
  return types[d] || 'info'
 }
 const loadModels = async () => {
  try {
    models.value = await modelApi.getAll()
    const defaultModel = models.value.find((m) => m.is_default)
    if (defaultModel) {
      form.modelId = defaultModel.id
    }
  } catch (e: any) {
    ElMessage.error(e.message)
  }
 }
 const loadCategories = async () => {
  try {
    const res = await quizApi.getCategories()
    categories.value = res.categories || []
  } catch (e) {
    console.error(e)
  }
 }
 const loadHistory = async () => {
  try {
    history.value = await quizApi.getHistory(20)
  } catch (e) {
    console.error(e)
  }
 }
 const startQuiz = async () => {
  if (!form.modelId) {
    ElMessage.warning('请选择模型')
    return
  }
  generating.value = true
  // 创建 WebSocket 连接
  ws.value = new WebSocketClient(
    'quiz',
    (data) => {
      const parsed = JSON.parse(data)
      if (parsed.type === 'info') {
        ElMessage.info(parsed.message)
      } else if (parsed.type === 'done') {
        questions.value = parsed.questions
        userAnswers.value = new Array(parsed.questions.length).fill(null)
        inQuiz.value = true
        generating.value = false
        currentQuestion.value = questions.value[0]
      } else if (parsed.type === 'error') {
        ElMessage.error(parsed.message)
        generating.value = false
      }
    },
    (error) => {
      ElMessage.error('WebSocket 连接失败')
      generating.value = false
    }
  )
  try {
    await ws.value.connect()
    // 发送生成请求
    ws.value.send({
      action: 'generate',
      category: form.category,
      difficulty: form.difficulty,
      count: form.count,
      model_id: form.modelId,
    })
  } catch (error) {
    ElMessage.error('连接失败')
    generating.value = false
  }
 }
 const prevQuestion = () => {
  if (currentIndex.value > 0) {
    userAnswers.value[currentIndex.value] = userAnswer.value
    currentIndex.value--
    currentQuestion.value = questions.value[currentIndex.value]
    userAnswer.value = userAnswers.value[currentIndex.value]
  }
 }
 const nextQuestion = () => {
  userAnswers.value[currentIndex.value] = userAnswer.value
  currentIndex.value++
  currentQuestion.value = questions.value[currentIndex.value]
  userAnswer.value = userAnswers.value[currentIndex.value]
 }
 const submitQuiz = async () => {
  userAnswers.value[currentIndex.value] = userAnswer.value
  // 发送答案
  ws.value?.send({
    action: 'submit',
    session_id: 1, // TODO: 从生成响应中获取
    answers: questions.value.map((q, idx) => ({
      question_id: q.id,
      user_answer: userAnswers.value[idx],
    })),
  })
  // 等待结果
  // ws 的 onMessage 会处理 result 类型
 }
 const resetQuiz = () => {
  inQuiz.value = false
  showResult.value = false
  questions.value = []
  userAnswers.value = []
  currentIndex.value = 0
  userAnswer.value = null
  score.value = 0
  correctCount.value = 0
  results.value = []
  loadHistory()
 }
 onMounted(() => {
  loadModels()
  loadCategories()
  loadHistory()
  })
</script>

<style scoped>
.quiz-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
 .question-content {
  padding: 20px 0;
}
 .question-text {
  font-size: 16px;
  margin: 16px 0;
}
 .option-item {
  display: block;
  margin: 12px 0;
}
 .quiz-actions {
  margin-top: 30px;
  text-align: center;
}
 .history-card {
  margin-top: 20px;
}
 .result-item {
  margin-bottom: 20px;
  padding: 15px;
  border-radius: 8px;
  background: #f5f7fa;
}
</style>
