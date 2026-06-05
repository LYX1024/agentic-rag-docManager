<template>
  <el-dialog
    v-model="dialogVisible"
    title="创建知识库"
    width="520px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="right"
    >
      <el-form-item label="知识库名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入知识库名称" maxlength="50" show-word-limit />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="请输入知识库描述（选填）"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
      <el-form-item label="向量库类型" prop="vsType">
        <el-select v-model="form.vsType" placeholder="请选择向量库类型" style="width: 100%">
          <el-option label="FAISS" value="FAISS" />
          <el-option label="Chroma" value="CHROMA" />
        </el-select>
      </el-form-item>
      <el-form-item label="嵌入模型" prop="embedModel">
        <el-select v-model="form.embedModel" placeholder="请选择嵌入模型" style="width: 100%">
          <el-option label="bge-m3" value="bge-m3" />
          <el-option label="bge-large" value="bge-large" />
          <el-option label="text-embedding-3-small" value="text-embedding-3-small" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :loading="loading">创建</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { CreateKBParams } from '@/api/knowledgeBase'

const emit = defineEmits<{
  (e: 'confirm', data: CreateKBParams): void
}>()

const dialogVisible = defineModel<boolean>('visible', { required: true })
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive<CreateKBParams>({
  name: '',
  description: '',
  vsType: 'FAISS',
  embedModel: 'bge-m3'
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 1, max: 50, message: '名称长度在 1 到 50 个字符之间', trigger: 'blur' }
  ],
  vsType: [
    { required: true, message: '请选择向量库类型', trigger: 'change' }
  ],
  embedModel: [
    { required: true, message: '请选择嵌入模型', trigger: 'change' }
  ]
}

async function handleConfirm() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    emit('confirm', { ...form })
  } catch {
    // validation failed
  }
}

function handleClose() {
  formRef.value?.resetFields()
  form.name = ''
  form.description = ''
  form.vsType = 'FAISS'
  form.embedModel = 'bge-m3'
  dialogVisible.value = false
}
</script>

<style scoped lang="scss">
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
