<script setup lang="ts">
import { SliderRange, SliderRoot, SliderThumb, SliderTrack } from 'reka-ui'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    min?: number
    max?: number
    step?: number
    disabled?: boolean
  }>(),
  { min: 0, max: 100, step: 1, disabled: false },
)

const model = defineModel<number>({ default: 0 })
const values = computed<number[]>({
  get: () => [model.value],
  set: (nextValues) => {
    const nextValue = nextValues[0]
    if (nextValue !== undefined) model.value = nextValue
  },
})
</script>

<template>
  <SliderRoot
    v-model="values"
    class="relative flex h-5 touch-none items-center select-none data-disabled:cursor-not-allowed data-disabled:opacity-50"
    :min="props.min"
    :max="props.max"
    :step="props.step"
    :disabled="props.disabled"
  >
    <SliderTrack class="relative h-1.5 grow overflow-hidden rounded-full bg-muted">
      <SliderRange class="absolute h-full bg-primary" />
    </SliderTrack>
    <SliderThumb
      :class="[
        'block size-4 cursor-grab rounded-full active:cursor-grabbing',
        'border-2 border-primary bg-background shadow-sm ring-ring transition',
        'focus-visible:ring-2 focus-visible:outline-none',
      ]"
    />
  </SliderRoot>
</template>
