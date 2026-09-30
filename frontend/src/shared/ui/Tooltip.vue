<script setup lang="ts">
import { TooltipArrow, TooltipContent, TooltipPortal, TooltipRoot, TooltipTrigger } from 'reka-ui'

withDefaults(
  defineProps<{
    content?: string
    side?: 'top' | 'right' | 'bottom' | 'left'
    align?: 'start' | 'center' | 'end'
    disabled?: boolean
    delay?: number
  }>(),
  { content: '', side: 'top', align: 'center', disabled: false, delay: 400 },
)
</script>

<template>
  <TooltipRoot :disabled="disabled" :delay-duration="delay">
    <TooltipTrigger as-child>
      <slot />
    </TooltipTrigger>
    <TooltipPortal>
      <TooltipContent
        class="z-70 max-w-72 rounded-lg bg-overlay px-2.5 py-1.5 text-xs text-overlay-foreground shadow-lg"
        :side="side"
        :align="align"
        :side-offset="6"
      >
        <slot name="content">{{ content }}</slot>
        <TooltipArrow class="fill-overlay" :width="8" :height="4" />
      </TooltipContent>
    </TooltipPortal>
  </TooltipRoot>
</template>
