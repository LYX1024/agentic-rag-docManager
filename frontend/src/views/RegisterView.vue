<template>
  <div class="min-h-screen bg-[#F9F6F3] flex items-center justify-center py-20 px-6">
    <div class="w-full max-w-[420px] bg-[#F9F6F3] border border-[#d4cdc5]/40 rounded-sm shadow-sm p-8 md:p-10">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="font-light tracking-wide text-3xl mb-2">MyKB</h1>
        <p class="font-light text-sm text-gray-500">注册一个新的知识库平台账号</p>
      </div>

      <!-- Form -->
      <form class="flex flex-col gap-5" @submit.prevent="handleRegister">
        <div>
          <AppInput
            v-model="form.username"
            placeholder="请输入用户名"
          />
          <p v-if="errors.username" class="font-light text-xs text-[#5a7a6b] mt-1">{{ errors.username }}</p>
        </div>

        <div>
          <AppInput
            v-model="form.email"
            placeholder="请输入邮箱"
          />
          <p v-if="errors.email" class="font-light text-xs text-[#5a7a6b] mt-1">{{ errors.email }}</p>
        </div>

        <div>
          <AppInput
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
          />
          <p v-if="errors.password" class="font-light text-xs text-[#5a7a6b] mt-1">{{ errors.password }}</p>
        </div>

        <div>
          <AppInput
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
          />
          <p v-if="errors.confirmPassword" class="font-light text-xs text-[#5a7a6b] mt-1">{{ errors.confirmPassword }}</p>
        </div>

        <AppButton variant="primary" size="lg" :disabled="loading" class="w-full mt-2">
          {{ loading ? '注册中...' : '注册' }}
        </AppButton>
      </form>

      <!-- Footer -->
      <div class="text-center mt-5 font-light text-xs text-gray-500">
        <span>已有账号？</span>
        <router-link to="/login" class="text-[#3d3d3d] underline hover:text-[#5a7a6b] transition-colors duration-700 ease-in-out ml-1">
          立即登录
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Toast } from '@/utils/toast'
import AppInput from '@/components/ui/AppInput.vue'
import AppButton from '@/components/ui/AppButton.vue'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const errors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

function validate(): boolean {
  errors.username = ''
  errors.email = ''
  errors.password = ''
  errors.confirmPassword = ''
  let valid = true

  if (!form.username.trim()) {
    errors.username = '请输入用户名'
    valid = false
  } else if (form.username.length < 2 || form.username.length > 30) {
    errors.username = '用户名长度在 2 到 30 个字符之间'
    valid = false
  }

  if (!form.email.trim()) {
    errors.email = '请输入邮箱'
    valid = false
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = '请输入正确的邮箱格式'
    valid = false
  }

  if (!form.password) {
    errors.password = '请输入密码'
    valid = false
  } else if (form.password.length < 6 || form.password.length > 30) {
    errors.password = '密码长度在 6 到 30 个字符之间'
    valid = false
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = '请再次输入密码'
    valid = false
  } else if (form.confirmPassword !== form.password) {
    errors.confirmPassword = '两次输入的密码不一致'
    valid = false
  }

  return valid
}

async function handleRegister() {
  if (!validate()) return

  loading.value = true
  try {
    await authStore.register(form.username, form.password, form.email)
    Toast.success('注册成功，请登录')
    router.push('/login')
  } catch (error: any) {
    Toast.error(error.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>
