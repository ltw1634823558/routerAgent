<template>
  <div class="page-container">
    <!-- 配置区域 -->
    <div v-if="!inQuiz && !showResult" class="config-section">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon quiz-icon">📝</div>
            <div class="header-info">
              <h3>问答 Agent - AI 岗位试题</h3>
              <p>智能生成个性化测试题目</p>
            </div>
          </div>
        </template>

        <el-form :model="form" label-width="100px" class="quiz-form">
          <el-row :gutter="24">
            <el-col :span="8">
              <el-form-item label="技能分类">
                <el-select v-model="form.category" style="width: 100%" placeholder="选择分类">
                  <el-option label="全部技能" value="" />
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
              <el-form-item label="难度等级">
                <div class="difficulty-options">
                  <div
                    v-for="diff in difficulties"
                    :key="diff.value"
                    class="difficulty-item"
                    :class="{ active: form.difficulty === diff.value }"
                    @click="form.difficulty = diff.value"
                  >
                    <span class="diff-icon">{{ diff.icon }}</span>
                    <span class="diff-label">{{ diff.label }}</span>
                  </div>
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="题目数量">
                <div class="count-selector">
                  <el-button-group>
                    <el-button
                      v-for="c in [5, 10, 15, 20]"
                      :key="c"
                      :type="form.count === c ? 'primary' : 'default'"
                      @click="form.count = c"
                    >
                      {{ c }}题
                    </el-button>
                  </el-button-group>
                </div>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="使用模型">
            <el-select v-model="form.modelId" style="width: 300px" placeholder="选择 AI 模型">
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

          <el-form-item>
            <el-button
              type="primary"
              class="start-btn"
              @click="startQuiz"
              :loading="generating"
            >
              <el-icon v-if="!generating"><VideoPlay /></el-icon>
              {{ generating ? '正在生成试题...' : '开始生成试题' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 答题历史 -->
      <el-card class="history-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon history-icon">📊</div>
            <div class="header-info">
              <h3>答题历史</h3>
              <p>查看您的答题记录</p>
            </div>
          </div>
        </template>

        <el-table :data="history" stripe class="history-table">
          <el-table-column prop="category" label="分类" min-width="120">
            <template #default="{ row }">
              <el-tag class="category-tag">{{ row.category || '全部' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="difficulty" label="难度" width="100">
            <template #default="{ row }">
              <span class="difficulty-badge" :class="row.difficulty">
                {{ getDifficultyLabel(row.difficulty) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="total_questions" label="题数" width="80" align="center" />
          <el-table-column prop="score" label="得分" width="120" align="center">
            <template #default="{ row }">
              <span class="score-value" :class="getScoreClass(row.score)">
                {{ row.score }}分
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="started_at" label="时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.started_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 错题本与薄弱点 -->
      <el-card class="insights-card">
        <template #header>
          <div class="card-header insights-header">
            <div class="header-info">
              <h3>错题本与薄弱点</h3>
              <p>根据历史作答记录安排复习</p>
            </div>
            <el-button size="small" :loading="loadingInsights" @click="loadLearningInsights">
              <el-icon><RefreshRight /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        <el-row :gutter="24">
          <el-col :span="14">
            <div class="insight-title">最近错题</div>
            <el-table v-if="wrongAnswers.length" :data="wrongAnswers.slice(0, 8)" stripe size="small">
              <el-table-column prop="question" label="题目" min-width="220" show-overflow-tooltip />
              <el-table-column prop="category" label="分类" width="110">
                <template #default="{ row }">{{ row.category || '未分类' }}</template>
              </el-table-column>
              <el-table-column label="来源" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">
                  <span>{{ row.source_title || row.source || 'AI 生成' }}</span>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无错题记录" :image-size="60" />
          </el-col>
          <el-col :span="10">
            <div class="insight-title">分类薄弱点</div>
            <el-table v-if="weaknessStats.categories?.length" :data="weaknessStats.categories.slice(0, 6)" stripe size="small">
              <el-table-column prop="name" label="分类" min-width="100" />
              <el-table-column label="正确率" width="100" align="right">
                <template #default="{ row }">
                  <el-progress :percentage="row.accuracy" :status="row.accuracy < 60 ? 'exception' : row.accuracy < 80 ? 'warning' : 'success'" :stroke-width="8" />
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="完成答题后生成薄弱点" :image-size="60" />
          </el-col>
        </el-row>
      </el-card>
    </div>

    <!-- 答题区域 -->
    <div v-if="inQuiz && currentQuestion" class="quiz-section">
      <el-card class="quiz-card">
        <template #header>
          <div class="quiz-header">
            <div class="progress-info">
              <h3>题目 {{ currentIndex + 1 }} / {{ questions.length }}</h3>
              <el-progress
                :percentage="((currentIndex + 1) / questions.length) * 100"
                :show-text="false"
                class="progress-bar"
              />
            </div>
            <div class="question-meta">
              <el-tag :type="getDifficultyType(currentQuestion.difficulty)" class="diff-tag">
                {{ getDifficultyLabel(currentQuestion.difficulty) }}
              </el-tag>
              <el-tag type="info" class="category-tag">{{ currentQuestion.category }}</el-tag>
            </div>
          </div>
        </template>

        <div class="question-content">
          <p class="question-text">{{ currentQuestion.question }}</p>

          <!-- 选择题 -->
          <div v-if="isChoiceQuestion(currentQuestion)" class="choice-options">
            <div
              v-for="(option, idx) in currentQuestion.options"
              :key="idx"
              class="choice-item"
              :class="{ selected: isOptionSelected(Number(idx)) }"
              @click="toggleOption(Number(idx))"
            >
              <span class="choice-letter" :class="{ checkbox: isMultipleChoice(currentQuestion) }">
                <el-icon v-if="isMultipleChoice(currentQuestion) && isOptionSelected(Number(idx))"><Check /></el-icon>
                <span v-else>{{ String.fromCharCode(65 + Number(idx)) }}</span>
              </span>
              <span class="choice-text">{{ option }}</span>
            </div>
          </div>

          <!-- 填空题 -->
          <el-input
            v-if="currentQuestion.question_type === 'fill'"
            v-model="userAnswer"
            placeholder="请输入答案"
            class="fill-input"
          />

          <!-- 代码题 -->
          <el-input
            v-if="isCodeQuestion(currentQuestion)"
            v-model="userAnswer"
            type="textarea"
            :rows="12"
            placeholder="请输入代码..."
            class="code-input"
          />
        </div>

        <div class="quiz-actions">
          <el-button
            class="nav-btn prev"
            @click="prevQuestion"
            :disabled="currentIndex === 0"
          >
            <el-icon><ArrowLeft /></el-icon>
            上一题
          </el-button>
          <div class="question-dots">
            <span
              v-for="(_, idx) in questions"
              :key="idx"
              class="dot"
              :class="{
                active: idx === currentIndex,
                answered: hasAnswer(userAnswers[idx], questions[idx]) && idx !== currentIndex
              }"
              @click="goToQuestion(idx)"
            />
          </div>
          <el-button
            v-if="currentIndex < questions.length - 1"
            class="nav-btn next"
            @click="nextQuestion"
          >
            下一题
            <el-icon><ArrowRight /></el-icon>
          </el-button>
          <el-button
            v-else
            type="primary"
            class="submit-btn"
            @click="submitQuiz"
          >
            <el-icon><Check /></el-icon>
            提交答案
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 结果区域 -->
    <div v-if="showResult" class="result-section">
      <el-card class="result-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon result-icon">🎯</div>
            <div class="header-info">
              <h3>答题结果</h3>
              <p>查看您的答题表现</p>
            </div>
          </div>
        </template>

        <div class="score-display">
          <div class="score-circle" :class="getScoreClass(score)">
            <span class="score-number">{{ score }}</span>
            <span class="score-unit">分</span>
          </div>
          <div class="score-details">
            <div class="detail-item">
              <span class="detail-label">总题数</span>
              <span class="detail-value">{{ questions.length }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">正确数</span>
              <span class="detail-value correct">{{ correctCount }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">正确率</span>
              <span class="detail-value">{{ Math.round((correctCount / questions.length) * 100) }}%</span>
            </div>
          </div>
        </div>

        <div class="result-list">
          <div
            v-for="(r, idx) in results"
            :key="r.question_id"
            class="result-item"
            :class="{ correct: r.is_correct, wrong: !r.is_correct }"
          >
            <div class="result-header">
              <span class="result-number">第 {{ idx + 1 }} 题</span>
              <el-tag :type="r.is_correct ? 'success' : 'danger'" size="small">
                {{ r.is_correct ? '正确' : '错误' }}
              </el-tag>
            </div>
            <p class="result-question">{{ r.question }}</p>
            <div class="result-answers">
              <div class="answer-row">
                <span class="answer-label">你的答案：</span>
                <div
                  v-if="isCodeAnswer(r.question_type, r.user_answer)"
                  class="answer-code-block"
                >
                  <pre class="code-pre"><code class="hljs" v-html="highlightCode(r.user_answer || '未作答', r.question_type)"></code></pre>
                </div>
                <span v-else class="answer-value">{{ r.user_answer || '未作答' }}</span>
              </div>
              <div class="answer-row correct-answer">
                <span class="answer-label">正确答案：</span>
                <div
                  v-if="isCodeAnswer(r.question_type, r.correct_answer)"
                  class="answer-code-block"
                >
                  <pre class="code-pre"><code class="hljs" v-html="highlightCode(r.correct_answer, r.question_type)"></code></pre>
                </div>
                <span v-else class="answer-value">{{ r.correct_answer }}</span>
              </div>
            </div>
            <p class="result-explanation" v-if="r.explanation">
              <el-icon><InfoFilled /></el-icon>
              {{ r.explanation }}
            </p>
            <p class="result-source" v-if="r.source_title || r.source">
              来源：{{ r.source_title || r.source }}
              <a v-if="r.source" :href="r.source" target="_blank" rel="noopener noreferrer">查看原文</a>
            </p>
          </div>
        </div>

        <div class="result-actions">
          <el-button type="primary" class="retry-btn" @click="resetQuiz">
            <el-icon><RefreshRight /></el-icon>
            重新开始
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { modelApi, quizApi } from '@/api/request'
import { WebSocketClient } from '@/api/websocket'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import sql from 'highlight.js/lib/languages/sql'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import 'highlight.js/styles/atom-one-dark.css'

// 注册需要的高亮语言
hljs.registerLanguage('python', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)

// 判断是否为代码类型答案
const isCodeAnswer = (questionType: string, answer: unknown): boolean => {
  const normalizedType = String(questionType || '').toLowerCase().replace('-', '_')
  if (normalizedType === 'code' || normalizedType.includes('python') || normalizedType.includes('coding')) return true
  // 检测答案是否包含多行或代码特征
  if (answer && typeof answer === 'string') {
    const codeIndicators = ['\n', 'def ', 'function ', 'class ', 'import ', 'const ', 'let ', 'var ', 'SELECT ', 'return ', '    ', '\t']
    return codeIndicators.some(indicator => answer.includes(indicator))
  }
  return false
}

// 检测代码语言
const detectLanguage = (code: string): string => {
  if (!code) return ''
  const patterns: Record<string, RegExp> = {
    python: /(?:^|\n)\s*(?:class|def)\s+\w+\s*[(:]|import\s+\w+|from\s+\w+\s+import|print\s*\(/,
    javascript: /function\s+\w+\s*\(|const\s+\w+\s*=|let\s+\w+\s*=|=>\s*\{|console\./,
    typescript: /:\s*(string|number|boolean|any)\b|interface\s+\w+|<\w+>/,
    sql: /SELECT\s+.+FROM|INSERT\s+INTO|UPDATE\s+.+SET|CREATE\s+TABLE/i,
    json: /^\s*[\[{]/,
    bash: /#!\/bin\/bash|sudo\s+|apt\s+|npm\s+|pip\s+|cd\s+/
  }
  for (const [lang, pattern] of Object.entries(patterns)) {
    if (pattern.test(code)) return lang
  }
  return ''
}

// 代码高亮处理
const highlightCode = (code: string, _questionType: string): string => {
  if (!code) return ''
  const source = (typeof code === 'string' ? code : String(code))
    .replace(/^\s*```(?:[\w+#.-]+)?\s*\n?/i, '')
    .replace(/\n?\s*```\s*$/i, '')
  const language = detectLanguage(source)
  try {
    if (language && hljs.getLanguage(language)) {
      return hljs.highlight(source, { language }).value
    }
    // 自动检测语言
    return hljs.highlightAuto(source).value
  } catch {
    return source.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char] || char))
  }
}

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
const sessionId = ref<number | null>(null)
const wrongAnswers = ref<any[]>([])
const weaknessStats = ref<any>({ categories: [], difficulties: [] })
const loadingInsights = ref(false)

const ws = ref<WebSocketClient | null>(null)

const form = reactive({
  category: '',
  difficulty: 'basic',
  count: 5,
  modelId: null as number | null,
})

const difficulties = [
  { label: '基础', value: 'basic', icon: '🌱' },
  { label: '进阶', value: 'intermediate', icon: '🌿' },
  { label: '精通', value: 'advanced', icon: '🌳' },
]

const currentQuestion = computed(() => {
  return questions.value[currentIndex.value]
})

const isMultipleChoice = (question: any) => ['multiple_choice', 'multi_choice', 'multiple'].includes(question?.question_type)
const isChoiceQuestion = (question: any) => question?.question_type === 'choice' || isMultipleChoice(question)
const isCodeQuestion = (question: any) => {
  const type = String(question?.question_type || question?.type || '').toLowerCase().replace(/[-\s]+/g, '_')
  return type === 'code' || type === 'coding' || type === 'programming' || type.includes('python')
}
const isOptionSelected = (idx: number) => isMultipleChoice(currentQuestion.value)
  ? Array.isArray(userAnswer.value) && userAnswer.value.includes(idx)
  : userAnswer.value === idx
const hasAnswer = (answer: any, question: any) => isMultipleChoice(question)
  ? Array.isArray(answer) && answer.length > 0
  : answer !== null && answer !== undefined && answer !== ''

const toggleOption = (idx: number) => {
  if (!isMultipleChoice(currentQuestion.value)) {
    userAnswer.value = idx
    return
  }
  const selected = Array.isArray(userAnswer.value) ? [...userAnswer.value] : []
  const position = selected.indexOf(idx)
  if (position >= 0) selected.splice(position, 1)
  else selected.push(idx)
  userAnswer.value = selected.sort((a, b) => a - b)
}

const difficultyLabels: Record<string, string> = {
  basic: '基础',
  intermediate: '进阶',
  advanced: '精通',
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
const getDifficultyLabel = (d: string) => difficultyLabels[d] || d

const getDifficultyType = (d: string) => {
  const types: Record<string, string> = {
    basic: 'success',
    intermediate: 'warning',
    advanced: 'danger',
  }
  return types[d] || 'info'
}

const getScoreClass = (s: number) => {
  if (s >= 80) return 'excellent'
  if (s >= 60) return 'good'
  return 'need-improve'
}

const formatTime = (time: string) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
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

const loadLearningInsights = async () => {
  loadingInsights.value = true
  try {
    const [wrong, stats] = await Promise.all([
      quizApi.getWrongAnswers({ limit: 20 }),
      quizApi.getWeaknessStats(),
    ])
    wrongAnswers.value = wrong || []
    weaknessStats.value = stats || { categories: [], difficulties: [] }
  } catch (e) {
    console.error(e)
  } finally {
    loadingInsights.value = false
  }
}

const startQuiz = async () => {
  if (!form.modelId) {
    ElMessage.warning('请选择模型')
    return
  }

  generating.value = true

  ws.value = new WebSocketClient(
    'quiz',
    (data) => {
      const parsed = JSON.parse(data)
      if (parsed.type === 'info') {
        ElMessage.info(parsed.message)
      } else if (parsed.type === 'done') {
        questions.value = parsed.questions
        sessionId.value = parsed.session_id
        userAnswers.value = parsed.questions.map((question: any) => isMultipleChoice(question) ? [] : null)
        inQuiz.value = true
        userAnswer.value = userAnswers.value[0]
        generating.value = false
      } else if (parsed.type === 'error') {
        ElMessage.error(parsed.message)
        generating.value = false
      } else if (parsed.type === 'result') {
        score.value = parsed.score
        correctCount.value = parsed.correct_count
        results.value = parsed.results
        inQuiz.value = false
        showResult.value = true
      }
    },
    () => {
      ElMessage.error('WebSocket 连接失败')
      generating.value = false
    }
  )

  try {
    await ws.value.connect()
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
    userAnswer.value = userAnswers.value[currentIndex.value]
  }
}

const nextQuestion = () => {
  userAnswers.value[currentIndex.value] = userAnswer.value
  currentIndex.value++
  userAnswer.value = userAnswers.value[currentIndex.value]
}

const goToQuestion = (idx: number) => {
  userAnswers.value[currentIndex.value] = userAnswer.value
  currentIndex.value = idx
  userAnswer.value = userAnswers.value[idx]
}

const submitQuiz = async () => {
  userAnswers.value[currentIndex.value] = userAnswer.value
  ws.value?.send({
    action: 'submit',
    session_id: sessionId.value,
    answers: questions.value.map((q, idx) => {
      const rawAnswer = userAnswers.value[idx]
      // 对于选择题，将索引转换为选项文本
      let userAnswerText = rawAnswer
      if (isChoiceQuestion(q) && rawAnswer !== null && q.options) {
        userAnswerText = Array.isArray(rawAnswer)
          ? rawAnswer.map((index) => q.options[index]).filter(Boolean)
          : q.options[rawAnswer] || rawAnswer
      }
      return {
        question_id: q.id,
        user_answer: userAnswerText,
        user_answer_index: isChoiceQuestion(q) ? rawAnswer : null,
      }
    }),
  })
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
  sessionId.value = null
  loadHistory()
  loadLearningInsights()
}

onMounted(() => {
  loadModels()
  loadCategories()
  loadHistory()
  loadLearningInsights()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  position: relative;
  z-index: 1;
}

/* 卡片通用样式 */
.config-card,
.history-card,
.insights-card,
.quiz-card,
.result-card {
  border-radius: 16px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.config-card :deep(.el-card__header),
.history-card :deep(.el-card__header),
.insights-card :deep(.el-card__header),
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

.quiz-icon {
  background: linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%);
}

.history-icon {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
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

/* 难度选择 */
.difficulty-options {
  display: flex;
  gap: 8px;
  width: 100%;
}

.difficulty-item {
  flex: 1;
  padding: 10px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}

.difficulty-item:hover {
  border-color: #f97316;
  background: #fff7ed;
}

.difficulty-item.active {
  border-color: #f97316;
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
}

.diff-icon {
  display: block;
  font-size: 20px;
  margin-bottom: 4px;
}

.diff-label {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

/* 数量选择 */
.count-selector :deep(.el-button) {
  border-radius: 8px;
}

/* 模型选择 */
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

/* 开始按钮 */
.start-btn {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  border: none;
  border-radius: 12px;
  padding: 12px 32px;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.start-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(249, 115, 22, 0.35);
}

/* 历史表格 */
.history-table {
  --el-table-header-bg-color: #f9fafb;
  --el-table-row-hover-bg-color: #fafafa;
}

.category-tag {
  background: #f3f4f6;
  border: none;
  color: #6b7280;
}

.difficulty-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.difficulty-badge.basic {
  background: #d1fae5;
  color: #059669;
}

.difficulty-badge.intermediate {
  background: #fef3c7;
  color: #d97706;
}

.difficulty-badge.advanced {
  background: #fee2e2;
  color: #dc2626;
}

.score-value {
  font-weight: 600;
  font-size: 15px;
}

.score-value.excellent {
  color: #10b981;
}

.score-value.good {
  color: #f59e0b;
}

.score-value.need-improve {
  color: #ef4444;
}

/* 答题区域 */
.quiz-card {
  min-height: 500px;
}

.quiz-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-info h3 {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.progress-bar {
  width: 200px;
}

.question-meta {
  display: flex;
  gap: 8px;
}

.question-content {
  padding: 30px 0;
}

.question-text {
  font-size: 18px;
  font-weight: 500;
  color: #1f2937;
  margin: 0 0 30px;
  line-height: 1.6;
}

/* 选择题选项 */
.choice-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.choice-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}

.choice-item:hover {
  border-color: #f97316;
  background: #fff7ed;
}

.choice-item.selected {
  border-color: #f97316;
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
}

.choice-letter {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: #6b7280;
  transition: all 0.2s ease;
}

.choice-item.selected .choice-letter {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: #fff;
}

.insights-header {
  justify-content: space-between;
}

.insight-title {
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}

.insights-card :deep(.el-progress) {
  min-width: 92px;
}

.choice-letter.checkbox {
  border-radius: 7px;
  font-size: 16px;
}

.choice-text {
  flex: 1;
  font-size: 15px;
  color: #374151;
}

.fill-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  padding: 12px 16px;
}

.code-input :deep(.el-textarea__inner) {
  border-radius: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #1f2937;
  color: #e5e7eb;
  border: none;
}

/* 答题操作 */
.quiz-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 20px;
  border-top: 1px solid #f3f4f6;
}

.nav-btn {
  border-radius: 10px;
  padding: 10px 20px;
}

.nav-btn.prev,
.nav-btn.next {
  background: #f3f4f6;
  border: none;
  color: #6b7280;
}

.question-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e5e7eb;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dot.active {
  background: #f97316;
  transform: scale(1.3);
}

.dot.answered {
  background: #10b981;
}

.submit-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 10px;
  padding: 10px 24px;
}

/* 结果展示 */
.score-display {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 30px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-radius: 16px;
  margin-bottom: 24px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}

.score-circle.excellent {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.score-circle.good {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.score-circle.need-improve {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.score-number {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
}

.score-unit {
  font-size: 14px;
  opacity: 0.9;
}

.score-details {
  display: flex;
  gap: 32px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 13px;
  color: #6b7280;
}

.detail-value {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.detail-value.correct {
  color: #10b981;
}

/* 结果列表 */
.result-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.result-item {
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid;
}

.result-item.correct {
  background: #f0fdf4;
  border-color: #10b981;
}

.result-item.wrong {
  background: #fef2f2;
  border-color: #ef4444;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.result-number {
  font-weight: 600;
  color: #374151;
}

.result-question {
  font-size: 15px;
  color: #1f2937;
  margin: 0 0 12px;
  line-height: 1.6;
}

.result-answers {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.answer-row {
  display: flex;
  gap: 8px;
  font-size: 14px;
}

.answer-label {
  color: #6b7280;
}

.answer-value {
  color: #374151;
}

.correct-answer .answer-value {
  color: #10b981;
  font-weight: 500;
}

.result-explanation {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  padding: 12px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
}

.result-source {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.result-source a {
  color: #2563eb;
  text-decoration: none;
}

.result-actions {
  text-align: center;
}

.retry-btn {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  border: none;
  border-radius: 12px;
  padding: 12px 32px;
  font-size: 15px;
}

/* 代码块样式 */
.answer-code-block {
  flex: 1;
  margin-top: 8px;
  margin-bottom: 8px;
  overflow: hidden;
}

.answer-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}

.answer-row:has(.answer-code-block) {
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
}

.answer-row:has(.answer-code-block) .answer-label {
  flex-shrink: 0;
  padding-top: 10px;
}

.code-pre {
  margin: 0;
  padding: 16px;
  background: #282c34;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}

.code-pre code {
  font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
  white-space: pre;
  word-wrap: normal;
  display: block;
}

.code-pre code.hljs {
  background: transparent;
  padding: 0;
}

/* highlight.js 主题增强 */
.hljs {
  color: #abb2bf;
  background: #282c34;
}

.hljs-comment,
.hljs-quote {
  color: #5c6370;
  font-style: italic;
}

.hljs-keyword,
.hljs-selector-tag,
.hljs-addition {
  color: #c678dd;
}

.hljs-number,
.hljs-string,
.hljs-meta .hljs-meta-string,
.hljs-literal,
.hljs-doctag,
.hljs-regexp {
  color: #98c379;
}

.hljs-title,
.hljs-section,
.hljs-name,
.hljs-selector-id,
.hljs-selector-class {
  color: #e06c75;
}

.hljs-attribute,
.hljs-attr,
.hljs-variable,
.hljs-template-variable,
.hljs-class .hljs-title,
.hljs-type {
  color: #d19a66;
}

.hljs-symbol,
.hljs-bullet,
.hljs-subst,
.hljs-meta,
.hljs-meta .hljs-keyword,
.hljs-selector-attr,
.hljs-selector-pseudo,
.hljs-link {
  color: #61afef;
}

.hljs-built_in,
.hljs-deletion {
  color: #e06c75;
}

.hljs-formula {
  background: #3e4451;
}

.hljs-emphasis {
  font-style: italic;
}

.hljs-strong {
  font-weight: bold;
}
</style>
