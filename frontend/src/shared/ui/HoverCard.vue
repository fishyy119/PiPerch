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
          $style.content,
          'z-60 origin-(--reka-hover-card-content-transform-origin) rounded-xl',
          'border border-border bg-popover text-popover-foreground shadow-2xl',
          contentClass,
        ]"
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

<style module>
.content[data-state='open'] {
  animation: hover-card-in 100ms ease-out;
}

.content[data-state='closed'] {
  animation: hover-card-out 75ms ease-in;
}

@keyframes hover-card-in {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes hover-card-out {
  from {
    opacity: 1;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(0.98);
  }
}

@media (prefers-reduced-motion: reduce) {
  .content {
    animation: none;
  }
}
</style>
