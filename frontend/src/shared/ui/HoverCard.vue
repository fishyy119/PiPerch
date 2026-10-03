<script setup lang="ts">
import { HoverCardContent, HoverCardPortal, HoverCardRoot, HoverCardTrigger } from 'reka-ui'

withDefaults(
  defineProps<{
    side?: 'top' | 'right' | 'bottom' | 'left'
    align?: 'start' | 'center' | 'end'
    openDelay?: number
    closeDelay?: number
    sideOffset?: number
    collisionPadding?: number
    enableTouch?: boolean
    contentClass?: string
  }>(),
  {
    side: 'right',
    align: 'start',
    openDelay: 200,
    closeDelay: 150,
    sideOffset: 8,
    collisionPadding: 16,
    enableTouch: false,
    contentClass: '',
  },
)

const open = defineModel<boolean>('open', { default: false })
</script>

<template>
  <HoverCardRoot
    v-slot="{ open: currentOpen }"
    v-model:open="open"
    :open-delay="openDelay"
    :close-delay="closeDelay"
    :enable-touch="enableTouch"
  >
    <HoverCardTrigger as-child>
      <slot name="trigger" :open="currentOpen" />
    </HoverCardTrigger>
    <HoverCardPortal>
      <HoverCardContent
        :class="[
          'z-60 origin-(--reka-hover-card-content-transform-origin) rounded-xl',
          'border border-border bg-popover text-popover-foreground shadow-2xl',
          contentClass,
        ]"
        data-app-floating-content
        data-app-hover-card-content
        :side="side"
        :align="align"
        :side-offset="sideOffset"
        :collision-padding="collisionPadding"
      >
        <slot :open="currentOpen" />
      </HoverCardContent>
    </HoverCardPortal>
  </HoverCardRoot>
</template>
