<script setup lang="ts">
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from 'reka-ui'

export interface DropdownMenuOption {
  value: string
  label: string
  disabled?: boolean
  danger?: boolean
  separatorBefore?: boolean
}

withDefaults(
  defineProps<{
    items: readonly DropdownMenuOption[]
    align?: 'start' | 'center' | 'end'
  }>(),
  { align: 'end' },
)

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ select: [value: string] }>()
</script>

<template>
  <DropdownMenuRoot v-model:open="open">
    <DropdownMenuTrigger as-child>
      <slot name="trigger" />
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent
        class="z-50 min-w-44 origin-(--reka-dropdown-menu-content-transform-origin) rounded-xl border border-border bg-popover p-1 text-popover-foreground shadow-xl"
        data-app-floating-content
        :align="align"
        :side-offset="6"
      >
        <template v-for="item in items" :key="item.value">
          <DropdownMenuSeparator v-if="item.separatorBefore" class="my-1 h-px bg-border" />
          <DropdownMenuItem
            :class="[
              'flex min-h-9 items-center rounded-lg px-3 py-1.5',
              'cursor-pointer text-sm outline-none',
              'data-highlighted:bg-accent data-highlighted:text-accent-foreground',
              'data-disabled:pointer-events-none data-disabled:opacity-50',
              item.danger ? 'text-destructive' : '',
            ]"
            :disabled="item.disabled === true"
            @select="emit('select', item.value)"
          >
            <slot name="item" :item="item">{{ item.label }}</slot>
          </DropdownMenuItem>
        </template>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
