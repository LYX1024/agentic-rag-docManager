<template>
  <AppDialog
    :model-value="visible"
    title="创建知识库"
    width="520px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-4">
      <!-- Name -->
      <div>
        <label class="block font-mono text-sm mb-1">知识库名称 *</label>
        <AppInput
          v-model="form.name"
          placeholder="请输入知识库名称"
        />
        <p v-if="errors.name" class="font-mono text-xs text-[#5a7a6b] mt-1">{{ errors.name }}</p>
      </div>

      <!-- Description -->
      <div>
        <label class="block font-mono text-sm mb-1">描述</label>
        <textarea
          v-model="form.description"
          placeholder="请输入知识库描述（选填）"
          maxlength="200"
          rows="3"
          class="bg-transparent focus:outline-none border-b-2 border-[#3d3d3d] px-3 py-2 w-full font-mono resize-none placeholder:text-gray-400 text-sm"
        />
        <p class="font-mono text-xs text-gray-400 mt-1">{{ form.description?.length ?? 0 }}/200</p>
      </div>

      <!-- VS Type -->
      <div>
        <label class="block font-mono text-sm mb-1">向量库类型 *</label>
        <AppSelect
          v-model="form.vsType"
          :options="vsTypeOptions"
          placeholder="请选择向量库类型"
        />
        <p v-if="errors.vsType" class="font-mono text-xs text-[#5a7a6b] mt-1">{{ errors.vsType }}</p>
      </div>

      <!-- Embed Model -->
      <div>
        <label class="block font-mono text-sm mb-1">嵌入模型 *</label>
        <AppSelect
          v-model="form.embedModel"
          :options="embedModelOptions"
          placeholder="请选择嵌入模型"
        />
        <p v-if="errors.embedModel" class="font-mono text-xs text-[#5a7a6b] mt-1">{{ errors.embedModel }}</p>
      </div>
    </div>

    <template #footer>
      <AppButton variant="secondary" @click="handleCancel">取消</AppButton>
      <AppButton variant="primary" @click="handleConfirm" :disabled="loading">
        {{ loading ? '创建中...' : '创建' }}
      </AppButton>
    </template>
  </AppDialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { CreateKBParams } from '@/api/knowledgeBase'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import AppButton from '@/components/ui/AppButton.vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'confirm', data: CreateKBParams): void
}>()

const loading = ref(false)

const vsTypeOptions = [
  { label: 'FAISS', value: 'FAISS' },
  { label: 'Chroma', value: 'CHROMA' }
]

const embedModelOptions = [
  { label: 'bge-m3', value: 'bge-m3' },
  { label: 'text-embedding-3-small', value: 'text-embedding-3-small' }
]

const form = reactive<CreateKBParams>({
  name: '',
  description: '',
  vsType: 'FAISS',
  embedModel: 'bge-m3'
})

const errors = reactive<Record<string, string>>({})

function validate(): boolean {
  errors.name = ''
  errors.vsType = ''
  errors.embedModel = ''

  if (!form.name.trim()) {
    errors.name = '请输入知识库名称'
  } else if (form.name.length > 50) {
    errors.name = '名称长度不能超过 50 个字符'
  }
  if (!form.vsType) {
    errors.vsType = '请选择向量库类型'
  }
  if (!form.embedModel) {
    errors.embedModel = '请选择嵌入模型'
  }
  return !errors.name && !errors.vsType && !errors.embedModel
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.vsType = 'FAISS'
  form.embedModel = 'bge-m3'
  errors.name = ''
  errors.vsType = ''
  errors.embedModel = ''
}

watch(() => props.visible, (val) => {
  if (!val) {
    resetForm()
  }
})

function handleCancel() {
  emit('update:visible', false)
}

function handleConfirm() {
  if (!validate()) return
  emit('confirm', { ...form })
}
</script>
