<script setup lang="ts">
import { Images, Pencil, Plus, RefreshCw, Save, Trash2 } from '@lucide/vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  applyFavoriteSyncPlan,
  type ArtworkGroup,
  createFavoriteSyncPlan,
  createGroup as createArtworkGroup,
  deleteGroup,
  type FavoriteSyncPlan,
  listGroups,
  renameGroup,
} from '@/features/gallery/gallery-api'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import Dialog from '@ui/Dialog.vue'
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
const favoriteSyncPlan = ref<FavoriteSyncPlan | null>(null)
const favoriteSyncDialogOpen = ref(false)
const checkingFavoriteSync = ref(false)
const applyingFavoriteSync = ref(false)

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

async function checkFavoriteSync() {
  if (checkingFavoriteSync.value) return
  checkingFavoriteSync.value = true
  try {
    favoriteSyncPlan.value = await createFavoriteSyncPlan()
    toast.success('Pixiv 收藏检查完成', {
      description: '可通过旁边的“查看同步摘要”确认差异。',
    })
  } catch (error) {
    toast.error('检查 Pixiv 收藏失败', { description: errorMessage(error) })
  } finally {
    checkingFavoriteSync.value = false
  }
}

function closeFavoriteSyncDialog() {
  if (applyingFavoriteSync.value) return
  favoriteSyncDialogOpen.value = false
}

function showFavoriteSyncDialog() {
  if (favoriteSyncPlan.value !== null) favoriteSyncDialogOpen.value = true
}

async function applyFavoriteSync() {
  if (applyingFavoriteSync.value) return
  const plan = favoriteSyncPlan.value
  if (plan === null) return
  applyingFavoriteSync.value = true
  try {
    const result = await applyFavoriteSyncPlan(plan.planId)
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['artworks'] }),
      queryClient.invalidateQueries({ queryKey: ['artwork'] }),
    ])
    favoriteSyncDialogOpen.value = false
    favoriteSyncPlan.value = null
    toast.success(
      `本地收藏已同步：添加 ${String(result.added)} 件，移除 ${String(result.removed)} 件`,
    )
  } catch (error) {
    toast.error('同步本地收藏失败', { description: errorMessage(error) })
  } finally {
    applyingFavoriteSync.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <Card class="p-5 md:p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="max-w-2xl">
          <h2 class="font-semibold">Pixiv 收藏同步</h2>
          <p class="mt-1 text-sm leading-6 text-muted-foreground">
            读取当前账号的公开与非公开收藏，与本地图库比较。确认差异后只更新本地收藏标记，不修改
            Pixiv 收藏或本地分组。
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            v-if="favoriteSyncPlan"
            variant="secondary"
            :disabled="applyingFavoriteSync"
            @click="showFavoriteSyncDialog"
          >
            查看同步摘要
          </Button>
          <Button
            variant="secondary"
            :disabled="checkingFavoriteSync || applyingFavoriteSync"
            @click="checkFavoriteSync"
          >
            <RefreshCw :size="17" :class="checkingFavoriteSync ? 'animate-spin' : ''" />
            {{ checkingFavoriteSync ? '正在检查…' : '检查同步差异' }}
          </Button>
        </div>
      </div>
    </Card>

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

  <Dialog
    :open="favoriteSyncDialogOpen"
    title="确认同步 Pixiv 收藏"
    description="以下差异来自刚刚读取的 Pixiv 收藏快照。批准后将一次性更新本地数据库。"
    @update:open="!$event && closeFavoriteSyncDialog()"
  >
    <template v-if="favoriteSyncPlan">
      <dl class="mt-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        <div class="rounded-xl bg-muted p-3">
          <dt class="text-muted-foreground">Pixiv 收藏</dt>
          <dd class="mt-1 text-xl font-semibold">{{ favoriteSyncPlan.pixivFavoriteCount }}</dd>
        </div>
        <div class="rounded-xl bg-muted p-3">
          <dt class="text-muted-foreground">本地已收藏</dt>
          <dd class="mt-1 text-xl font-semibold">{{ favoriteSyncPlan.localFavoriteCount }}</dd>
        </div>
        <div class="rounded-xl bg-muted p-3">
          <dt class="text-muted-foreground">本地可匹配</dt>
          <dd class="mt-1 text-xl font-semibold">{{ favoriteSyncPlan.matchedFavoriteCount }}</dd>
        </div>
        <div class="rounded-xl bg-muted p-3">
          <dt class="text-muted-foreground">将添加收藏</dt>
          <dd class="mt-1 text-xl font-semibold text-primary">{{ favoriteSyncPlan.addCount }}</dd>
        </div>
        <div class="rounded-xl bg-muted p-3">
          <dt class="text-muted-foreground">将移除收藏</dt>
          <dd class="mt-1 text-xl font-semibold text-destructive">
            {{ favoriteSyncPlan.removeCount }}
          </dd>
        </div>
        <div class="rounded-xl bg-muted p-3">
          <dt class="text-muted-foreground">未下载，忽略</dt>
          <dd class="mt-1 text-xl font-semibold">
            {{ favoriteSyncPlan.unavailableLocallyCount }}
          </dd>
        </div>
      </dl>
      <p class="mt-4 text-sm text-muted-foreground">
        本地图库共 {{ favoriteSyncPlan.localArtworkCount }} 件作品。同步摘要有效期为 10
        分钟；过期后需重新检查。
      </p>
      <div class="mt-6 flex justify-end gap-2">
        <Button
          variant="secondary"
          :disabled="applyingFavoriteSync"
          @click="closeFavoriteSyncDialog"
        >
          {{ favoriteSyncPlan.addCount || favoriteSyncPlan.removeCount ? '取消' : '关闭' }}
        </Button>
        <Button
          :disabled="
            applyingFavoriteSync || (!favoriteSyncPlan.addCount && !favoriteSyncPlan.removeCount)
          "
          @click="applyFavoriteSync"
        >
          {{
            applyingFavoriteSync
              ? '同步中…'
              : favoriteSyncPlan.addCount || favoriteSyncPlan.removeCount
                ? '批准并同步'
                : '无需同步'
          }}
        </Button>
      </div>
    </template>
  </Dialog>
</template>
