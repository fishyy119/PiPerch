<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

import { analyzeSmartCrop } from '@/shared/lib/smart-crop'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    src: string
    alt?: string
    cropWidth?: number
    cropHeight?: number
  }>(),
  {
    alt: '',
    cropWidth: 1,
    cropHeight: 1,
  },
)

const emit = defineEmits<{
  load: [event: Event]
  error: [event: Event]
}>()

const objectPosition = ref('50% 50%')
let requestId = 0

async function handleLoad(event: Event) {
  emit('load', event)
  const image = event.currentTarget
  if (!(image instanceof HTMLImageElement)) return
  if (
    image.naturalWidth <= 0 ||
    image.naturalHeight <= 0 ||
    !Number.isFinite(props.cropWidth) ||
    !Number.isFinite(props.cropHeight) ||
    props.cropWidth <= 0 ||
    props.cropHeight <= 0
  ) {
    return
  }

  const currentRequest = ++requestId
  try {
    const position = await analyzeSmartCrop(image, props.src, props.cropWidth, props.cropHeight)
    if (currentRequest !== requestId) return
    objectPosition.value = `${String(position.x)}% ${String(position.y)}%`
  } catch {
    if (currentRequest === requestId) objectPosition.value = '50% 50%'
  }
}

function handleError(event: Event) {
  requestId += 1
  objectPosition.value = '50% 50%'
  emit('error', event)
}

watch(
  () => props.src,
  () => {
    requestId += 1
    objectPosition.value = '50% 50%'
  },
)

onBeforeUnmount(() => {
  requestId += 1
})
</script>

<template>
  <img
    v-bind="$attrs"
    :src="src"
    :alt="alt"
    :style="{ objectPosition }"
    @load="handleLoad"
    @error="handleError"
  />
</template>
