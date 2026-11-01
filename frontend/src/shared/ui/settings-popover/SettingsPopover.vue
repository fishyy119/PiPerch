<script setup lang="ts">
import { Settings } from '@lucide/vue'

import { Button, type ButtonVariants } from '@ui/button'
import { Popover } from '@ui/popover'

withDefaults(
  defineProps<{
    title?: string
    variant?: Exclude<NonNullable<ButtonVariants['variant']>, 'blank'>
  }>(),
  { title: '显示设置', variant: 'secondary' },
)
</script>

<template>
  <Popover align="end">
    <template #trigger>
      <Button :variant="variant" size="icon" :title="title">
        <Settings :size="18" />
      </Button>
    </template>
    <slot />
  </Popover>
</template>
