<template>
  <div class="relative font-mono" ref="containerRef">
    <button
      type="button"
      class="w-full bg-transparent border-b-2 border-[#3d3d3d] px-3 py-2 text-left flex items-center justify-between cursor-pointer"
      @click="toggleOpen"
    >
      <span :class="{ 'text-gray-400': !selectedLabel }">
        {{ selectedLabel || placeholder }}
      </span>
      <span class="ml-2 transition-transform" :class="{ 'rotate-180': isOpen }">
        ▼
      </span>
    </button>
    <ul
      v-if="isOpen"
      class="absolute left-0 right-0 top-full mt-1 bg-white border-2 border-[#3d3d3d] shadow-[4px_4px_0px_0px_rgba(0,0,0,0.10)] z-10 max-h-48 overflow-y-auto rounded-sm"
    >
      <li
        v-for="option in options"
        :key="option.value"
        class="px-3 py-2 cursor-pointer hover:bg-[#3d3d3d] hover:text-white transition-colors text-sm"
        :class="{ 'bg-[#3d3d3d] text-white': modelValue === option.value }"
        @click="select(option)"
      >
        {{ option.label }}
      </li>
      <li v-if="options.length === 0" class="px-3 py-2 text-gray-400 text-sm">
        无选项
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

interface SelectOption {
  label: string
  value: string | number
}

const props = withDefaults(defineProps<{
  modelValue: string | number | null
  options: SelectOption[]
  placeholder?: string
}>(), {
  options: () => [],
  placeholder: '请选择'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
}>()

const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)

function toggleOpen() {
  isOpen.value = !isOpen.value
}

function select(option: SelectOption) {
  emit('update:modelValue', option.value)
  isOpen.value = false
}

function handleClickOutside(event: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

const selectedLabel = computed(() => {
  const found = props.options.find(o => o.value === props.modelValue)
  return found ? found.label : ''
})

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
