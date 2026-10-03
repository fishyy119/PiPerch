<script setup lang="ts">
import { ContextMenuContent, ContextMenuPortal, ContextMenuRoot, ContextMenuTrigger } from 'reka-ui'

import ContextMenuItems from '@ui/ContextMenuItems.vue'

export interface ContextMenuOption {
  value: string
  label: string
  disabled?: boolean
  danger?: boolean
  separatorBefore?: boolean
  children?: readonly ContextMenuOption[]
}

defineProps<{ items: readonly ContextMenuOption[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ select: [value: string] }>()
</script>

<template>
  <ContextMenuRoot v-model:open="open">
    <ContextMenuTrigger as-child>
      <slot />
    </ContextMenuTrigger>
    <ContextMenuPortal>
      <ContextMenuContent
        class="z-50 min-w-48 rounded-xl border border-border bg-popover p-1 text-popover-foreground shadow-xl"
      >
        <ContextMenuItems :items="items" @select="emit('select', $event)" />
      </ContextMenuContent>
    </ContextMenuPortal>
  </ContextMenuRoot>
</template>
