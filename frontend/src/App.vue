<script setup lang="ts">
import { useDark } from '@vueuse/core'
import { RouterView } from 'vue-router'

import { UiProvider } from '@ui/ui-provider'

useDark({ storageKey: null })
</script>

<template>
  <UiProvider>
    <RouterView />
  </UiProvider>
</template>
