<script setup lang="ts">
import { RouterView } from 'vue-router'

import { UiProvider } from '@ui/ui-provider'
</script>

<template>
  <UiProvider>
    <RouterView />
  </UiProvider>
</template>
