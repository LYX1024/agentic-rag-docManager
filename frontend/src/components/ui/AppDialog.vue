<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="close"
    >
      <!-- Overlay -->
      <div class="absolute inset-0 bg-[#3d3d3d]/50" />
      <!-- Card -->
      <div
        :class="dialogClasses"
        :style="{ maxWidth: width }"
        @click.stop
      >
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-light tracking-wide text-lg">{{ title }}</h2>
          <button
            class="font-light text-xl leading-none hover:text-[#5a7a6b] transition-colors duration-700 ease-in-out cursor-pointer"
            @click="close"
          >
            ×
          </button>
        </div>
        <slot />
        <div v-if="$slots.footer" class="mt-6 flex justify-end gap-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title?: string
  width?: string
}>(), {
  title: '',
  width: '520px'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const visible = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function close() {
  visible.value = false
}

const dialogClasses = computed(() => [
  'relative bg-[#f5f0eb] border border-[#d4cdc5]/40',
  'shadow-sm',
  'p-4 md:p-6 rounded-sm w-full mx-4'
])
</script>
