<script setup lang="ts">
import { ref, watch } from 'vue'

import Button from '@ui/Button.vue'
import Dialog from '@ui/Dialog.vue'
import Input from '@ui/Input.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    description?: string
    busy?: boolean
  }>(),
  { description: '创建一个新的本地分组。', busy: false },
)
const emit = defineEmits<{
  close: []
  save: [name: string]
}>()

const name = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) name.value = ''
  },
)

function save() {
  const normalized = name.value.trim()
  if (normalized) emit('save', normalized)
}
</script>

<template>
  <Dialog
    :open="open"
    title="添加到新分组"
    :description="description"
    @update:open="!$event && emit('close')"
  >
    <form class="mt-5" @submit.prevent="save">
      <Input v-model="name" maxlength="20" placeholder="新分组名称" :disabled="busy" />
      <div class="mt-6 flex justify-end gap-2">
        <Button variant="secondary" :disabled="busy" @click="emit('close')">取消</Button>
        <Button type="submit" :disabled="busy || !name.trim()">
          {{ busy ? '添加中…' : '创建并添加' }}
        </Button>
      </div>
    </form>
  </Dialog>
</template>
