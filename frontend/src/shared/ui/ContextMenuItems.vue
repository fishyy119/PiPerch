<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import {
  ContextMenuItem,
  ContextMenuPortal,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
} from 'reka-ui'

import type { ContextMenuOption } from '@ui/ContextMenu.vue'

defineOptions({ name: 'ContextMenuItems' })
defineProps<{ items: readonly ContextMenuOption[] }>()
const emit = defineEmits<{ select: [value: string] }>()
</script>

<template>
  <template v-for="item in items" :key="item.value">
    <ContextMenuSeparator v-if="item.separatorBefore" class="my-1 h-px bg-border" />
    <ContextMenuSub v-if="item.children?.length">
      <ContextMenuSubTrigger
        :class="[
          'flex min-h-9 cursor-pointer items-center gap-3 rounded-lg px-3 py-1.5 text-sm outline-none',
          'data-highlighted:bg-accent data-highlighted:text-accent-foreground',
          'data-disabled:pointer-events-none data-disabled:opacity-50',
        ]"
        :disabled="item.disabled === true"
      >
        <span class="min-w-0 flex-1">{{ item.label }}</span>
        <ChevronRight :size="15" />
      </ContextMenuSubTrigger>
      <ContextMenuPortal>
        <ContextMenuSubContent
          class="z-50 min-w-44 origin-(--reka-context-menu-content-transform-origin) rounded-xl border border-border bg-popover p-1 text-popover-foreground shadow-xl"
          data-app-floating-content
          :side-offset="4"
        >
          <ContextMenuItems :items="item.children" @select="emit('select', $event)" />
        </ContextMenuSubContent>
      </ContextMenuPortal>
    </ContextMenuSub>
    <ContextMenuItem
      v-else
      :class="[
        'flex min-h-9 cursor-pointer items-center rounded-lg px-3 py-1.5 text-sm outline-none',
        'data-highlighted:bg-accent data-highlighted:text-accent-foreground',
        'data-disabled:pointer-events-none data-disabled:opacity-50',
        item.danger ? 'text-destructive' : '',
      ]"
      :disabled="item.disabled === true"
      @select="emit('select', item.value)"
    >
      {{ item.label }}
    </ContextMenuItem>
  </template>
</template>
