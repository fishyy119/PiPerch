<script setup lang="ts">
import { ConfigProvider, TooltipProvider } from 'reka-ui'

import { ToastHost } from '@ui/toast'
</script>

<template>
  <ConfigProvider>
    <TooltipProvider :delay-duration="400" :skip-delay-duration="150">
      <slot />
      <ToastHost />
    </TooltipProvider>
  </ConfigProvider>
</template>
