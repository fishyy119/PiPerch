<script setup lang="ts">
import { ChevronDown, ChevronUp } from '@lucide/vue'
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const TWO_ROWS_HEIGHT_PX = 72

const content = ref<HTMLElement>()
const expanded = ref(false)
const overflowing = ref(false)
let resizeObserver: ResizeObserver | undefined

function measureOverflow() {
  const nextOverflowing = (content.value?.scrollHeight ?? 0) > TWO_ROWS_HEIGHT_PX + 1
  overflowing.value = nextOverflowing
  if (!nextOverflowing) expanded.value = false
}

onMounted(() => {
  resizeObserver = new ResizeObserver(measureOverflow)
  if (content.value) resizeObserver.observe(content.value)
  void nextTick(measureOverflow)
})

onBeforeUnmount(() => resizeObserver?.disconnect())
</script>

<template>
  <div class="relative" :class="expanded && overflowing ? 'pb-9' : ''">
    <div :class="expanded ? '' : 'max-h-28 overflow-hidden'">
      <div ref="content" class="flex flex-wrap gap-2">
        <slot />
      </div>
    </div>
    <button
      v-if="overflowing"
      type="button"
      :class="[
        'group absolute inset-x-0 bottom-0 z-10 flex cursor-pointer items-end justify-center pb-1',
        'border-0 text-xs font-medium text-primary',
        'focus-visible:outline-2 focus-visible:outline-offset-2',
        expanded
          ? 'h-9 bg-linear-to-b from-transparent via-popover/85 to-popover'
          : 'h-10 bg-linear-to-b from-transparent via-popover/85 to-popover backdrop-blur-[1.5px]',
      ]"
      @click="expanded = !expanded"
    >
      <span
        class="pointer-events-none absolute inset-0 bg-linear-to-b from-transparent via-primary/10 to-primary/15 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
      />
      <span class="relative inline-flex items-center gap-1 px-2 py-0.5">
        {{ expanded ? '收起' : '展开' }}
        <ChevronUp v-if="expanded" :size="14" />
        <ChevronDown v-else :size="14" />
      </span>
    </button>
  </div>
</template>
