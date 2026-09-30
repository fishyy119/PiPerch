<script setup lang="ts">
import { Search, X } from '@lucide/vue'

import Input from '@ui/Input.vue'

withDefaults(
  defineProps<{
    placeholder?: string
    clearable?: boolean
    submitButton?: boolean
  }>(),
  { placeholder: '', clearable: false, submitButton: false },
)

const model = defineModel<string>({ default: '' })
const emit = defineEmits<{ clear: [] }>()

function clear() {
  model.value = ''
  emit('clear')
}
</script>

<template>
  <div class="relative">
    <button
      v-if="submitButton"
      type="submit"
      class="absolute inset-y-0 left-0 z-10 grid w-10 cursor-pointer place-items-center text-muted-foreground transition hover:text-primary"
    >
      <Search :size="18" />
    </button>
    <Search
      v-else
      class="pointer-events-none absolute top-1/2 left-3 z-10 -translate-y-1/2 text-muted-foreground"
      :size="16"
    />
    <Input
      :model-value="model"
      class="w-full rounded-full pr-9 pl-10"
      :placeholder="placeholder"
      @update:model-value="model = String($event)"
    />
    <button
      v-if="clearable && model"
      type="button"
      class="absolute inset-y-0 right-0 z-10 grid w-9 cursor-pointer place-items-center text-muted-foreground transition hover:text-primary"
      @click="clear"
    >
      <X :size="16" />
    </button>
  </div>
</template>
