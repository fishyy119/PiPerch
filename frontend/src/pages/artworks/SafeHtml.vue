<script setup lang="ts">
import DOMPurify from 'dompurify'
import { computed } from 'vue'

const props = defineProps<{ html: string }>()
const clean = computed(() => DOMPurify.sanitize(props.html))
</script>

<template>
  <!-- Pixiv 简介经 DOMPurify 清理后才允许渲染。 -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="safe-html" v-html="clean" />
</template>

<style scoped>
.safe-html :deep(a) {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 0.15rem;
}

.safe-html :deep(p) {
  margin-block: 0.5rem;
}
</style>
