<script setup lang="ts">
const model = defineModel<string>({ default: '' })
</script>

<template>
  <textarea
    v-model="model"
    class="min-h-24 rounded-xl border border-input bg-background px-3 py-2 text-foreground disabled:cursor-not-allowed disabled:opacity-50"
  />
</template>
