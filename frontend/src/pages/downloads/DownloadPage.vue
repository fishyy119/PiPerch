<script setup lang="ts">
import { ref } from 'vue'

import DownloadDiscoveryWorkspace from '@/pages/downloads/DownloadDiscoveryWorkspace.vue'
import DownloadJobsSidebar from '@/pages/downloads/DownloadJobsSidebar.vue'

const sourceLabel = ref('作品')
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(24rem,0.65fr)]">
    <DownloadDiscoveryWorkspace v-model:source-label="sourceLabel" />
    <DownloadJobsSidebar :source-label="sourceLabel" />
  </div>
</template>
