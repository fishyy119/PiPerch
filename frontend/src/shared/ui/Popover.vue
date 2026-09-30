<script setup lang="ts">
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'

withDefaults(
  defineProps<{
    side?: 'top' | 'right' | 'bottom' | 'left'
    align?: 'start' | 'center' | 'end'
    modal?: boolean
    contentClass?: string
  }>(),
  { side: 'bottom', align: 'center', modal: false, contentClass: '' },
)

const open = defineModel<boolean>('open', { default: false })
</script>

<template>
  <PopoverRoot v-model:open="open" :modal="modal">
    <PopoverTrigger as-child>
      <slot name="trigger" />
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        class="z-50 w-72 rounded-xl border border-border bg-popover p-4 text-popover-foreground shadow-xl"
        :class="contentClass"
        :side="side"
        :align="align"
        :side-offset="6"
      >
        <slot :close="() => (open = false)" />
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
