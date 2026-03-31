<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <h2>模型配置</h2>
          <el-button type="primary" @click="showDialog = true">
            <el-icon><Plus /></el-icon>
            添加模型
          </el-button>
        </div>
      </template>

      <el-table :data="models" v-loading="loading" stripe>
        <el-table-column prop="name" label="配置名称" />
        <el-table-column prop="provider" label="提供商">
          <template #default="{ row }">
            <el-tag>{{ getProviderLabel(row.provider) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型名称" />
        <el-table-column prop="api_url" label="API 地址" show-overflow-tooltip />
        <el-table-column prop="is_default" label="默认" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="editModel(row)">编辑</el-button>
            <el-button link type="warning" @click="setDefault(row)" v-if="!row.is_default">
              设为默认
            </el-button>
            <el-button link type="danger" @click="deleteModel(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑模型' : '添加模型'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="配置名称">
          <el-input v-model="form.name" placeholder="如：智谱 GLM-4" />
        </el-form-item>
        <el-form-item label="提供商">
          <el-select v-model="form.provider" placeholder="选择提供商" style="width: 100%">
            <el-option label="智谱 AI" value="zhipu" />
            <el-option label="阿里通义" value="alibaba" />
            <el-option label="百度文心" value="baidu" />
            <el-option label="讯飞星火" value="xunfei" />
            <el-option label="腾讯混元" value="tencent" />
            <el-option label="月之暗面" value="moonshot" />
            <el-option label="MiniMax" value="minimax" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="form.model_name" placeholder="如：glm-4" />
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input v-model="form.api_url" placeholder="如：https://open.bigmodel.cn/api/paas/v4" />
        </el-form-item>
        <el-form-item label="API KEY">
          <el-input
            v-model="form.api_key_env"
            placeholder="环境变量名，如：ZHIPU_API_KEY"
          />
          <div class="form-tip">
            请在 .env 文件中配置对应的环境变量值
          </div>
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveModel" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

const getProviderLabel = (provider: string) => providerLabels[provider] || provider

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
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
