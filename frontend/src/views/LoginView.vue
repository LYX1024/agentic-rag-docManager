<template>
  <div class="min-h-screen bg-[#F9F6F3] flex items-center justify-center py-20 px-6">
    <div class="w-full max-w-[420px] bg-[#F9F6F3] border border-[#d4cdc5]/40 rounded-sm shadow-sm p-8 md:p-10">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="font-light tracking-wide text-3xl mb-2">MyKB</h1>
        <p class="font-light text-sm text-gray-500">登录您的账号</p>
      </div>

      <!-- Form -->
      <form class="flex flex-col gap-5" @submit.prevent="handleLogin" @keyup.enter="handleLogin">
        <div>
          <AppInput
            v-model="form.username"
            placeholder="请输入用户名"
          />
          <p v-if="errors.username" class="font-light text-xs text-[#5a7a6b] mt-1">{{ errors.username }}</p>
        </div>

        <div>
          <AppInput
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
          />
          <p v-if="errors.password" class="font-light text-xs text-[#5a7a6b] mt-1">{{ errors.password }}</p>
        </div>

        <AppButton variant="primary" size="lg" :disabled="loading" class="w-full mt-2">
          {{ loading ? '登录中...' : '登录' }}
        </AppButton>
      </form>

      <!-- Footer -->
      <div class="text-center mt-5 font-light text-xs text-gray-500">
        <span>还没有账号？</span>
        <router-link to="/register" class="text-[#3d3d3d] underline hover:text-[#5a7a6b] transition-colors duration-700 ease-in-out ml-1">
          立即注册
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
  password: ''
})

const errors = reactive({
  username: '',
  password: ''
})

function validate(): boolean {
  errors.username = ''
  errors.password = ''
  let valid = true
  if (!form.username.trim()) {
    errors.username = '请输入用户名'
    valid = false
  } else if (form.username.length < 2 || form.username.length > 30) {
    errors.username = '用户名长度在 2 到 30 个字符之间'
    valid = false
  }
  if (!form.password) {
    errors.password = '请输入密码'
    valid = false
  } else if (form.password.length < 6 || form.password.length > 30) {
    errors.password = '密码长度在 6 到 30 个字符之间'
    valid = false
  }
  return valid
}

async function handleLogin() {
  if (!validate()) return

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    Toast.success('登录成功')
    router.push('/dashboard')
  } catch (error: any) {
    Toast.error(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
