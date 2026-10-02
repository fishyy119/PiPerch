<script setup lang="ts">
import { writeToClipboard } from '@/shared/lib/clipboard'

const props = defineProps<{
  userId: number
}>()

function copyUserId() {
  void writeToClipboard(String(props.userId))
}
</script>

<template>
  <button
    type="button"
    class="cursor-pointer text-xs text-muted-foreground transition-colors hover:text-primary"
    title="复制作者 ID"
    @click="copyUserId"
  >
    ID: {{ userId }}
  </button>
</template>
