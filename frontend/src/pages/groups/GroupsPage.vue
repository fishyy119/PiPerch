<script setup lang="ts">
import { Images, Pencil, Plus, Save, Trash2 } from '@lucide/vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  type ArtworkGroup,
  createGroup as createArtworkGroup,
  deleteGroup,
  listGroups,
  renameGroup,
} from '@/features/gallery/gallery-api'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import Input from '@ui/Input.vue'
import { toast } from '@ui/toast'

const router = useRouter()
const queryClient = useQueryClient()
const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: listGroups })
const newName = ref('')
const editingId = ref<number | null>(null)
const editingName = ref('')
const deleting = ref<ArtworkGroup | null>(null)
const busy = ref(false)

async function invalidateGroupData() {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['groups'] }),
    queryClient.invalidateQueries({ queryKey: ['artworks'] }),
  ])
}

async function run(label: string, operation: () => Promise<unknown>) {
  busy.value = true
  try {
    await operation()
    await invalidateGroupData()
    toast.success(label)
    return true
  } catch (error) {
    toast.error(`${label}失败`, { description: errorMessage(error) })
    return false
  } finally {
    busy.value = false
  }
}

async function createGroup() {
  const name = newName.value.trim()
  if (!name) return
  if (await run('本地分组已创建', () => createArtworkGroup(name))) newName.value = ''
}

function beginRename(group: ArtworkGroup) {
  editingId.value = group.groupId
  editingName.value = group.name
}

async function saveRename() {
  if (editingId.value === null || !editingName.value.trim()) return
  const groupId = editingId.value
  if (await run('本地分组已重命名', () => renameGroup(groupId, editingName.value))) {
    editingId.value = null
  }
}

async function confirmDelete() {
  if (deleting.value === null) return
  const groupId = deleting.value.groupId
  if (await run('本地分组已删除', () => deleteGroup(groupId))) deleting.value = null
}

function viewGroup(groupId: number) {
  void router.push({
    path: '/gallery',
    query: { groupId: String(groupId) },
  })
}
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <Card class="p-5 md:p-6">
      <h2 class="font-semibold">新增本地分组</h2>
      <p class="mt-1 text-sm text-muted-foreground">分组独立于收藏状态，仅用于整理本地作品。</p>
      <form class="mt-4 flex max-w-xl gap-2" @submit.prevent="createGroup">
        <Input v-model="newName" maxlength="20" placeholder="新分组名称" :disabled="busy" />
        <Button type="submit" class="shrink-0" :disabled="busy || !newName.trim()">
          <Plus :size="17" />新增
        </Button>
      </form>
    </Card>

    <Card class="overflow-hidden">
      <header
        class="flex items-center justify-between gap-3 border-b border-border px-5 py-4 md:px-6"
      >
        <div>
          <h2 class="font-semibold">本地分组</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            共 {{ groupsQuery.data.value?.length ?? 0 }} 个分组
          </p>
        </div>
      </header>

      <div v-if="groupsQuery.isPending.value" class="px-6 py-16 text-center text-muted-foreground">
        正在读取本地分组…
      </div>
      <div v-else-if="groupsQuery.error.value" class="px-6 py-16 text-center text-destructive">
        {{ errorMessage(groupsQuery.error.value) }}
      </div>
      <div v-else-if="groupsQuery.data.value?.length" class="divide-y divide-border">
        <div
          v-for="group in groupsQuery.data.value"
          :key="group.groupId"
          class="grid gap-3 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_7rem_auto] sm:items-center md:px-6"
        >
          <div v-if="editingId === group.groupId" class="min-w-0">
            <Input
              v-model="editingName"
              maxlength="20"
              :disabled="busy"
              @keyup.enter="saveRename"
            />
          </div>
          <p v-else class="min-w-0 truncate text-sm font-medium">{{ group.name }}</p>

          <p class="text-sm text-muted-foreground">{{ group.artworkCount }} 件作品</p>

          <div class="flex flex-wrap justify-end gap-1">
            <Button variant="ghost" size="small" @click="viewGroup(group.groupId)">
              <Images :size="15" />查看
            </Button>
            <Button
              :variant="editingId === group.groupId ? 'primary' : 'ghost'"
              size="small"
              :disabled="busy || (editingId === group.groupId && !editingName.trim())"
              @click="editingId === group.groupId ? saveRename() : beginRename(group)"
            >
              <Save v-if="editingId === group.groupId" :size="15" />
              <Pencil v-else :size="15" />
              {{ editingId === group.groupId ? '保存' : '重命名' }}
            </Button>
            <Button variant="ghost" size="small" :disabled="busy" @click="deleting = group">
              <Trash2 :size="15" class="text-destructive" />删除
            </Button>
          </div>
        </div>
      </div>
      <div v-else class="px-6 py-16 text-center text-sm text-muted-foreground">
        还没有本地分组，可在上方创建第一个分组。
      </div>
    </Card>
  </div>

  <ConfirmDialog
    :open="deleting !== null"
    title="删除本地分组"
    :description="`将删除本地分组“${deleting?.name ?? ''}”及其分组关系，不会影响作品的收藏状态。`"
    confirm-text="删除分组"
    :busy="busy"
    @close="deleting = null"
    @confirm="confirmDelete"
  />
</template>
