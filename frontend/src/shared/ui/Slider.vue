<script setup lang="ts">
import { SliderRange, SliderRoot, SliderThumb, SliderTrack } from 'reka-ui'
import { computed, ref, useAttrs, watch } from 'vue'

defineOptions({ inheritAttrs: false })

defineSlots<{
  value?: (props: { value: number }) => unknown
}>()

const props = withDefaults(
  defineProps<{
    min?: number
    max?: number
    step?: number
    disabled?: boolean
  }>(),
  { min: 0, max: 100, step: 1, disabled: false },
)

const [model, modelModifiers] = defineModel<number, 'lazy'>({ default: 0 })
const emit = defineEmits<{ commit: [value: number] }>()
const attrs = useAttrs()
const draftValue = ref(model.value)

watch(model, (nextValue) => {
  draftValue.value = nextValue
})

const currentValue = computed(() => (modelModifiers.lazy ? draftValue.value : model.value))
const values = computed<number[]>({
  get: () => [currentValue.value],
  set: (nextValues) => {
    const nextValue = nextValues[0]
    if (nextValue === undefined) return
    draftValue.value = nextValue
    if (!modelModifiers.lazy) model.value = nextValue
  },
})

function commitValue(nextValues: number[] | undefined) {
  const nextValue = nextValues?.[0]
  if (nextValue === undefined) return
  if (modelModifiers.lazy) model.value = nextValue
  emit('commit', nextValue)
}
</script>

<template>
  <SliderRoot
    v-bind="attrs"
    v-model="values"
    class="relative flex h-5 touch-none items-center select-none data-disabled:cursor-not-allowed data-disabled:opacity-50"
    :min="props.min"
    :max="props.max"
    :step="props.step"
    :disabled="props.disabled"
    @value-commit="commitValue"
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
  <slot name="value" :value="currentValue" />
</template>
