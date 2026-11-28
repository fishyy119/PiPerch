<script setup lang="ts">
import DownloadDiscoveryWorkspace from './DownloadDiscoveryWorkspace.vue'
import DownloadJobsSidebar from './DownloadJobsSidebar.vue'
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(24rem,0.65fr)]">
    <DownloadDiscoveryWorkspace />
    <DownloadJobsSidebar />
  </div>
</template>
