<script setup lang="ts">
defineProps<{ active: boolean }>()
</script>

<template>
  <button
    type="button"
    class="inline-flex min-h-8 cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1 text-[0.8125rem] transition"
    :class="
      active
        ? 'border-primary bg-primary/10 text-primary'
        : 'border-border bg-card hover:border-primary hover:text-primary'
    "
  >
    <slot />
  </button>
</template>
