<script setup lang="ts">
import DOMPurify from 'dompurify'
import { computed } from 'vue'

const props = defineProps<{ html: string }>()
const clean = computed(() => DOMPurify.sanitize(props.html))
</script>

<template>
  <!-- Pixiv 简介经 DOMPurify 清理后才允许渲染。 -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div v-html="clean" />
</template>
