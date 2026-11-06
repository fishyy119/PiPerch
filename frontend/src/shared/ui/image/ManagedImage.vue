<script setup lang="ts">
import { useTemplateRef } from 'vue'

import { useImageSource } from '@/shared/lib/image-loading'

const props = defineProps<{
  src: string
  alt?: string
  loading?: 'eager' | 'lazy'
}>()

const emit = defineEmits<{
  load: [event: Event]
  error: [event: Event]
}>()

const image = useTemplateRef<HTMLImageElement>('image')
const source = useImageSource(
  image,
  () => props.src,
  () => props.loading,
)
</script>

<template>
  <!-- 无来源时只隐藏内容，保留布局以供懒加载观测。 -->
  <img
    ref="image"
    :class="{ invisible: !source }"
    :src="source"
    :alt="alt"
    :loading="loading"
    @load="emit('load', $event)"
    @error="emit('error', $event)"
  />
</template>
