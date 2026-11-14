<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, watch } from 'vue'

import { Button } from '@ui/button'
import { cn } from '@ui/cn'
import { Input } from '@ui/input'

const props = withDefaults(
  defineProps<{
    page: number
    nextPage: number | null
    totalPages: number | null
    pending: boolean
    compact?: boolean
  }>(),
  { compact: false },
)
const pageInput = defineModel<string>({ default: '1' })
const emit = defineEmits<{ loadPage: [page: number] }>()
const targetPage = computed(() => Number(pageInput.value))
const canJump = computed(
  () =>
    !props.pending &&
    props.totalPages !== null &&
    /^\d+$/u.test(pageInput.value) &&
    Number.isSafeInteger(targetPage.value) &&
    targetPage.value >= 1 &&
    targetPage.value <= props.totalPages &&
    targetPage.value !== props.page + 1,
)

watch(
  () => [props.page, props.totalPages, props.pending],
  () => {
    pageInput.value = String(props.page + 1)
  },
  { immediate: true },
)

function jump() {
  if (canJump.value) emit('loadPage', targetPage.value - 1)
}
</script>

<template>
  <div
    :class="cn('flex flex-wrap items-center gap-2', compact ? 'justify-center' : 'justify-between')"
  >
    <Button
      variant="secondary"
      :size="compact ? 'icon' : 'default'"
      title="上一页"
      :disabled="page === 0 || pending"
      @pointerdown.prevent
      @click="emit('loadPage', page - 1)"
    >
      <ChevronLeft :size="17" /><template v-if="!compact">上一页</template>
    </Button>
    <form
      v-if="totalPages !== null"
      class="flex items-center gap-2 text-sm text-muted-foreground tabular-nums"
      @submit.prevent="jump"
    >
      <label class="flex items-center gap-2">
        第
        <Input
          v-model="pageInput"
          class="w-12! px-1! text-center"
          inputmode="numeric"
          pattern="[0-9]+"
          :disabled="pending || totalPages <= 1"
          @blur="jump"
        />
        / {{ Math.max(1, totalPages) }} 页
      </label>
    </form>
    <span v-else class="text-center text-sm text-muted-foreground tabular-nums">
      第 {{ page + 1 }} 页
    </span>
    <Button
      variant="secondary"
      :size="compact ? 'icon' : 'default'"
      title="下一页"
      :disabled="nextPage === null || pending"
      @pointerdown.prevent
      @click="nextPage !== null && emit('loadPage', nextPage)"
    >
      <template v-if="!compact">下一页</template><ChevronRight :size="17" />
    </Button>
  </div>
</template>
