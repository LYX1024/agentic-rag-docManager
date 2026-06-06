<template>
  <button
    :class="buttonClasses"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'danger'
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
}>(), {
  variant: 'primary',
  disabled: false,
  size: 'md'
})

defineEmits<{
  (e: 'click'): void
}>()

const sizeClasses: Record<string, string> = {
  sm: 'px-6 py-2 text-xs',
  md: 'px-10 py-3.5 text-sm',
  lg: 'px-14 py-4 text-base'
}

const baseClasses = [
  'font-light tracking-wide rounded-sm',
  'transition-all duration-700 ease-in-out',
  'disabled:opacity-40 disabled:cursor-not-allowed'
]

const variantClasses: Record<string, string[]> = {
  primary: [
    'bg-[#3d3d3d] text-[#f5f0eb]',
    'hover:bg-[#5a7a6b] hover:brightness-95',
    'active:bg-[#4a6358]'
  ],
  secondary: [
    'bg-white/60 text-[#3d3d3d] border border-[#d4cdc5]/30',
    'hover:border-[#d4cdc5]/80 hover:bg-[#fcfaf8]'
  ],
  danger: [
    'bg-[#607683] text-[#f5f0eb]',
    'hover:bg-[#4a5d6a] hover:brightness-95',
    'active:bg-[#3d4d58]'
  ]
}

const buttonClasses = computed(() => [
  ...baseClasses,
  sizeClasses[props.size],
  ...variantClasses[props.variant]
])
</script>
