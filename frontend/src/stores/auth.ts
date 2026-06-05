import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as authApi from '@/api/auth'
import type { UserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter()

  const token = ref<string>(localStorage.getItem('sa-token') || '')
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password })
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('sa-token', res.data.token)
    return res.data
  }

  async function register(username: string, password: string, email: string) {
    const res = await authApi.register({ username, password, email })
    return res
  }

  async function fetchUser() {
    try {
      const res = await authApi.getMe()
      user.value = res.data
    } catch {
      // If fetching user fails, do nothing (might be a network issue)
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('sa-token')
    router.push('/login')
  }

  return {
    token,
    user,
    isLoggedIn,
    login,
    register,
    fetchUser,
    logout
  }
})
