<script setup lang="ts">
import { Plus } from '@lucide/vue'
import { ref, watch } from 'vue'

import {
  type ArtworkGroup,
  createGroup as createArtworkGroup,
} from '@/features/gallery/gallery-api'
import CreateGroupDialog from '@/shared/components/groups/CreateGroupDialog.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Checkbox from '@ui/Checkbox.vue'
import Dialog from '@ui/Dialog.vue'
import { toast } from '@ui/toast'

const props = defineProps<{
  open: boolean
  groups: ArtworkGroup[]
  selectionCount: number
  busy?: boolean
}>()
const emit = defineEmits<{
  close: []
  save: [addGroupIds: number[], removeGroupIds: number[]]
  groupsChanged: []
}>()

const addGroupIds = ref<number[]>([])
const removeGroupIds = ref<number[]>([])
const createGroupOpen = ref(false)
const creatingGroup = ref(false)

watch(
  () => props.open,
  (open) => {
    if (!open) {
      createGroupOpen.value = false
      return
    }
    addGroupIds.value = []
    removeGroupIds.value = []
  },
)

function toggle(groupId: number, mode: 'add' | 'remove') {
  const own = mode === 'add' ? addGroupIds : removeGroupIds
  const other = mode === 'add' ? removeGroupIds : addGroupIds
  own.value = own.value.includes(groupId)
    ? own.value.filter((id) => id !== groupId)
    : [...own.value, groupId]
  other.value = other.value.filter((id) => id !== groupId)
}

async function createGroup(name: string) {
  creatingGroup.value = true
  try {
    const group = await createArtworkGroup(name)
    addGroupIds.value = [...addGroupIds.value, group.groupId]
    removeGroupIds.value = removeGroupIds.value.filter((id) => id !== group.groupId)
    createGroupOpen.value = false
    emit('groupsChanged')
    toast.success('本地分组已创建，并加入待添加分组')
  } catch (error) {
    toast.error('创建本地分组失败', { description: errorMessage(error) })
  } finally {
    creatingGroup.value = false
  }
}
</script>

<template>
  <Dialog
    :open="open"
    title="批量修改本地分组"
    :description="`将修改 ${String(selectionCount)} 件作品的本地分组，不影响收藏状态，也不会请求 Pixiv。`"
    @update:open="!$event && emit('close')"
  >
    <div class="mt-5 grid gap-4 sm:grid-cols-2">
      <section>
        <h3 class="mb-2 text-sm font-medium">添加到分组</h3>
        <div class="max-h-64 space-y-1 overflow-y-auto rounded-xl border border-border p-2">
          <button
            type="button"
            class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="busy || creatingGroup"
            @click="createGroupOpen = true"
          >
            <Plus :size="17" class="text-primary" />
            <span class="truncate text-sm">添加到新分组</span>
          </button>
          <div v-if="groups.length" class="my-1 h-px bg-border" />
          <button
            v-for="group in groups"
            :key="group.groupId"
            type="button"
            class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-accent"
            @click="toggle(group.groupId, 'add')"
          >
            <Checkbox
              :model-value="addGroupIds.includes(group.groupId)"
              class="pointer-events-none"
            />
            <span class="truncate text-sm">{{ group.name }}</span>
          </button>
        </div>
      </section>
      <section>
        <h3 class="mb-2 text-sm font-medium">从分组移除</h3>
        <div class="max-h-64 space-y-1 overflow-y-auto rounded-xl border border-border p-2">
          <button
            v-for="group in groups"
            :key="group.groupId"
            type="button"
            class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-accent"
            @click="toggle(group.groupId, 'remove')"
          >
            <Checkbox
              :model-value="removeGroupIds.includes(group.groupId)"
              class="pointer-events-none"
            />
            <span class="truncate text-sm">{{ group.name }}</span>
          </button>
        </div>
      </section>
    </div>
    <p v-if="groups.length === 0" class="mt-4 text-sm text-muted-foreground">
      还没有本地分组，可通过上方“添加到新分组”创建。
    </p>
    <div class="mt-6 flex justify-end gap-2">
      <Button variant="secondary" :disabled="busy" @click="emit('close')">取消</Button>
      <Button
        :disabled="busy || (!addGroupIds.length && !removeGroupIds.length)"
        @click="emit('save', addGroupIds, removeGroupIds)"
      >
        {{ busy ? '保存中…' : '应用修改' }}
      </Button>
    </div>
  </Dialog>

  <CreateGroupDialog
    :open="createGroupOpen"
    description="创建分组后会自动加入本次批量操作的待添加分组。"
    :busy="creatingGroup"
    @close="createGroupOpen = false"
    @save="createGroup"
  />
</template>
