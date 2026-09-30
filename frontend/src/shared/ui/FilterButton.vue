<script setup lang="ts">
import { SlidersHorizontal, X } from '@lucide/vue'

import Button from '@ui/Button.vue'

withDefaults(
  defineProps<{
    activeCount: number
    hideLabelUntilLarge?: boolean
  }>(),
  { hideLabelUntilLarge: false },
)

const emit = defineEmits<{
  toggle: []
  clear: []
}>()
</script>

<template>
  <div class="relative shrink-0">
    <Button variant="secondary" @click="emit('toggle')">
      <span class="relative inline-grid shrink-0 place-items-center">
        <SlidersHorizontal :size="17" />
        <span
          v-if="activeCount > 0"
          :class="[
            'absolute right-0 bottom-0 min-h-3.5 min-w-3.5 translate-x-1/2 translate-y-1/2',
            'grid place-items-center rounded-full px-0.5',
            'bg-primary text-[0.55rem] leading-none font-semibold text-primary-foreground ring-2 ring-card',
          ]"
        >
          {{ activeCount }}
        </span>
      </span>
      <span :class="{ 'hidden lg:inline': hideLabelUntilLarge }">筛选</span>
    </Button>

    <button
      v-if="activeCount > 0"
      type="button"
      :class="[
        'absolute top-0 right-0 z-10 size-5 translate-x-1/3 -translate-y-1/3',
        'grid cursor-pointer place-items-center rounded-full',
        'border bg-card text-muted-foreground shadow-sm transition',
        'hover:border-destructive/40 hover:bg-destructive/10 hover:text-destructive',
      ]"
      @click.stop="emit('clear')"
    >
      <X :size="12" :stroke-width="2.5" />
    </button>
  </div>
</template>
