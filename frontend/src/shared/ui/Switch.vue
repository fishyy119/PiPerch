<script setup lang="ts">
import { SwitchRoot, SwitchThumb } from 'reka-ui'

withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false })
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <SwitchRoot
    v-model="model"
    :class="[
      'relative inline-flex h-6 w-11 cursor-pointer items-center rounded-full',
      'bg-input transition data-[state=checked]:bg-primary',
      'disabled:cursor-not-allowed disabled:opacity-50',
    ]"
    :disabled="disabled"
  >
    <SwitchThumb
      class="pointer-events-none block size-5 translate-x-0.5 rounded-full bg-background shadow-sm transition-transform data-[state=checked]:translate-x-5"
    />
  </SwitchRoot>
</template>
