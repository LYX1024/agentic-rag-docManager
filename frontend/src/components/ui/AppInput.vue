<template>
  <input
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :class="inputClasses"
    @input="onInput"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  type?: string
}>(), {
  placeholder: '',
  type: 'text'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

function onInput(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}

const inputClasses = computed(() => [
  'bg-white border border-[#d4cdc5]/40 rounded-sm text-[#3d3d3d]',
  'placeholder:text-[#a89279] focus:outline-none',
  'transition-colors duration-700 ease-in-out',
  'px-3 py-2 w-full font-light'
])
</script>
