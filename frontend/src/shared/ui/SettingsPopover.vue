<script setup lang="ts">
import { Settings } from '@lucide/vue'

import Button from '@ui/Button.vue'
import Popover from '@ui/Popover.vue'

withDefaults(
  defineProps<{
    title?: string
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
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
