<script setup lang="ts">
import DownloadDiscoveryWorkspace from '@/pages/downloads/DownloadDiscoveryWorkspace.vue'
import DownloadJobsSidebar from '@/pages/downloads/DownloadJobsSidebar.vue'
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(24rem,0.65fr)]">
    <DownloadDiscoveryWorkspace />
    <DownloadJobsSidebar />
  </div>
</template>
