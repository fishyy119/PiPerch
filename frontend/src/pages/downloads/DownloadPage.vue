<script setup lang="ts">
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  RefreshCw,
  Search,
  UsersRound,
  X,
} from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, ref } from 'vue'

import {
  cancelDownloadJob,
  createDownloadJob,
  discover,
  type DiscoveryItem,
  type DiscoveryRequest,
  type DownloadJob,
  type FollowedUser,
  listDownloadJobs,
  listFollowedUsers,
  listSelectableUserArtworkIds,
  retryDownloadJob,
} from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import DiscoveryCandidateResults from '@/pages/downloads/DiscoveryCandidateResults.vue'
import FollowedUserSelector from '@/pages/downloads/FollowedUserSelector.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Input from '@ui/Input.vue'
import Textarea from '@ui/Textarea.vue'

type SourceType = DiscoveryRequest['sourceType']

const queryClient = useQueryClient()
const selection = useDownloadSelection()
const sourceType = ref<SourceType>('artwork')
const sourceInput = ref('')
const discoveryPage = ref(0)
const candidates = ref<DiscoveryItem[]>([])
const nextPage = ref<number | null>(null)
const notice = ref('')
const submissionError = ref('')
const loadedAuthorSelection = ref<{ userId: number; artworkIds: number[] } | null>(null)
const followedUsers = ref<FollowedUser[]>([])
const showFollowedUsers = ref(false)
const openFollowedUsersAfterFetch = ref(false)

const defaultSource: { value: SourceType; label: string; placeholder: string } = {
  value: 'artwork',
  label: '作品',
  placeholder: '作品 URL 或 ID，每行一个',
}
const sourceOptions: { value: SourceType; label: string; placeholder: string }[] = [
  defaultSource,
  { value: 'user', label: '用户', placeholder: '用户 ID' },
  { value: 'series', label: '系列', placeholder: '插画系列 ID' },
]

const currentSource = computed(
  () => sourceOptions.find((item) => item.value === sourceType.value) ?? defaultSource,
)
const pageFullySelected = computed(() => {
  const selectable = candidates.value.filter((item) => !item.inLibrary)
  return (
    selectable.length > 0 &&
    selectable.every((item) => selection.selectedIds.includes(item.artworkId))
  )
})
const currentUserId = computed(() => {
  if (sourceType.value !== 'user') return null
  const value = Number(sourceInput.value.trim())
  return Number.isSafeInteger(value) && value > 0 ? value : null
})
const allAuthorWorksSelected = computed(() => {
  const loaded = loadedAuthorSelection.value
  return (
    loaded !== null &&
    loaded.userId === currentUserId.value &&
    loaded.artworkIds.length > 0 &&
    loaded.artworkIds.every((artworkId) => selection.selectedIds.includes(artworkId))
  )
})

function makeDiscoveryRequest(page: number): DiscoveryRequest {
  const value = sourceInput.value.trim()
  if (sourceType.value === 'artwork') {
    const inputs = value
      .split(/[\s,]+/u)
      .map((item) => item.trim())
      .filter(Boolean)
    if (inputs.length === 0) throw new Error('请输入至少一个作品 URL 或 ID。')
    return { sourceType: 'artwork', inputs, page }
  }
  const id = Number(value)
  if (!Number.isSafeInteger(id) || id <= 0) throw new Error('请输入有效的正整数 ID。')
  return sourceType.value === 'user'
    ? { sourceType: 'user', userId: id, page }
    : { sourceType: 'series', seriesId: id, page }
}

function switchSource(nextSource: SourceType) {
  if (nextSource === sourceType.value) return
  sourceType.value = nextSource
  sourceInput.value = ''
  discoveryPage.value = 0
  candidates.value = []
  nextPage.value = null
  loadedAuthorSelection.value = null
  showFollowedUsers.value = false
  openFollowedUsersAfterFetch.value = false
  notice.value = ''
}

const discoveryMutation = useMutation({
  mutationFn: async (page: number) => discover(makeDiscoveryRequest(page)),
  onSuccess: (result) => {
    candidates.value = result.items
    selection.removeAll(result.items.filter((item) => item.inLibrary))
    discoveryPage.value = result.page
    nextPage.value = result.nextPage
    notice.value = result.items.length === 0 ? '这一页没有找到候选作品。' : ''
  },
})

const followedUsersMutation = useMutation({
  mutationFn: listFollowedUsers,
  onSuccess: (items) => {
    followedUsers.value = items
    showFollowedUsers.value = openFollowedUsersAfterFetch.value
  },
})

const selectAllAuthorMutation = useMutation({
  mutationFn: async (userId: number) => ({
    userId,
    artworkIds: await listSelectableUserArtworkIds(userId),
  }),
  onSuccess: (result) => {
    loadedAuthorSelection.value = result
    selection.addIds(result.artworkIds)
    notice.value = result.artworkIds.length
      ? `已选择该作者的全部 ${String(result.artworkIds.length)} 个作品。`
      : '该作者没有可选择的插画或漫画。'
  },
})

const jobsQuery = useQuery({
  queryKey: ['download-jobs'],
  queryFn: listDownloadJobs,
  refetchInterval: 15_000,
})

const createMutation = useMutation({
  mutationFn: async () => {
    const artworkIds = [...selection.selectedIds]
    const batches = Array.from({ length: Math.ceil(artworkIds.length / 1000) }, (_, index) =>
      artworkIds.slice(index * 1000, (index + 1) * 1000),
    )
    const submittedArtworkIds: number[] = []
    let createdJobCount = 0
    let failedError: unknown = null
    for (const [index, batch] of batches.entries()) {
      try {
        const batchSuffix =
          batches.length > 1 ? `，第 ${String(index + 1)}/${String(batches.length)} 批` : ''
        await createDownloadJob(
          batch,
          `${currentSource.value.label}来源（${String(artworkIds.length)} 项${batchSuffix}）`,
        )
        submittedArtworkIds.push(...batch)
        createdJobCount += 1
      } catch (error) {
        if (createdJobCount === 0) throw error
        failedError = error
        break
      }
    }
    return {
      createdJobCount,
      submittedArtworkIds,
      remainingCount: artworkIds.length - submittedArtworkIds.length,
      failedError,
    }
  },
  onMutate: () => {
    notice.value = ''
    submissionError.value = ''
  },
  onSuccess: async (result) => {
    selection.removeIds(result.submittedArtworkIds)
    if (result.failedError !== null) {
      submissionError.value = `已提交 ${String(result.createdJobCount)} 个下载任务，仍有 ${String(result.remainingCount)} 项未提交：${errorMessage(result.failedError)}`
    } else {
      notice.value =
        result.createdJobCount === 1
          ? '下载任务已提交。'
          : `已分批提交 ${String(result.createdJobCount)} 个下载任务。`
    }
    await queryClient.invalidateQueries({ queryKey: ['download-jobs'] })
  },
})

const actionMutation = useMutation({
  mutationFn: async ({ action, jobId }: { action: 'cancel' | 'retry'; jobId: string }) => {
    if (action === 'cancel') await cancelDownloadJob(jobId)
    else await retryDownloadJob(jobId)
  },
  onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['download-jobs'] }),
})

const events = new EventSource('/api/events/downloads')
events.addEventListener('job-updated', () => {
  void queryClient.invalidateQueries({ queryKey: ['download-jobs'] })
})
events.addEventListener('error', () => {
  void queryClient.invalidateQueries({ queryKey: ['download-jobs'] })
})
onBeforeUnmount(() => events.close())

function togglePage() {
  const selectable = candidates.value.filter((item) => !item.inLibrary)
  if (pageFullySelected.value) selection.removeAll(selectable)
  else selection.addAll(selectable)
}

function fetchFollowedUsers() {
  showFollowedUsers.value = false
  openFollowedUsersAfterFetch.value = true
  followedUsersMutation.mutate()
}

function selectFollowedUser(user: FollowedUser) {
  sourceInput.value = String(user.userId)
}

function previewDiscovery() {
  if (sourceType.value === 'user' && currentUserId.value !== null) {
    showFollowedUsers.value = false
    openFollowedUsersAfterFetch.value = false
  }
  discoveryMutation.mutate(0)
}

function toggleAllAuthorWorks() {
  const userId = currentUserId.value
  if (userId === null) return
  const loaded = loadedAuthorSelection.value
  if (loaded?.userId === userId) {
    if (allAuthorWorksSelected.value) selection.removeIds(loaded.artworkIds)
    else selection.addIds(loaded.artworkIds)
    return
  }
  selectAllAuthorMutation.mutate(userId)
}

function stateLabel(state: string) {
  const labels: Record<string, string> = {
    queued: '等待中',
    running: '下载中',
    succeeded: '已完成',
    partiallySucceeded: '部分完成',
    failed: '失败',
    cancelled: '已取消',
    skipped: '已跳过',
  }
  return labels[state] ?? state
}

function jobProgress(job: DownloadJob) {
  const total = Object.values(job.counts).reduce((sum, count) => sum + count, 0)
  const complete =
    job.counts.succeeded + job.counts.skipped + job.counts.failed + job.counts.cancelled
  return (complete / Math.max(1, total)) * 100
}
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(24rem,0.65fr)]">
    <section class="space-y-4">
      <Card class="p-5">
        <div class="mb-4 flex flex-wrap gap-2">
          <button
            v-for="option in sourceOptions"
            :key="option.value"
            type="button"
            class="cursor-pointer rounded-xl px-4 py-2 text-sm"
            :class="
              sourceType === option.value
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            "
            @click="switchSource(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
        <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="previewDiscovery">
          <Textarea
            v-if="sourceType === 'artwork'"
            v-model="sourceInput"
            class="flex-1 resize-y"
            :placeholder="currentSource.placeholder"
          />
          <Input
            v-else
            v-model="sourceInput"
            class="flex-1"
            :placeholder="currentSource.placeholder"
          />
          <Button
            v-if="sourceType === 'user'"
            type="button"
            variant="secondary"
            :disabled="followedUsersMutation.isPending.value"
            @click="fetchFollowedUsers"
          >
            <UsersRound :size="18" />
            {{ followedUsersMutation.isPending.value ? '获取中…' : '获取已关注作者' }}
          </Button>
          <Button type="submit" :disabled="discoveryMutation.isPending.value">
            <Search :size="18" />
            {{ discoveryMutation.isPending.value ? '加载中…' : '预览' }}
          </Button>
        </form>
        <p v-if="discoveryMutation.error.value" class="mt-3 text-sm text-destructive">
          {{ errorMessage(discoveryMutation.error.value) }}
        </p>
        <p v-if="followedUsersMutation.error.value" class="mt-3 text-sm text-destructive">
          {{ errorMessage(followedUsersMutation.error.value) }}
        </p>
        <div v-if="sourceType === 'user' && showFollowedUsers" class="mt-4 border-t pt-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <h2 class="text-sm font-semibold">已关注作者</h2>
            <span class="app-muted text-xs">共 {{ followedUsers.length }} 位</span>
          </div>
          <FollowedUserSelector
            :users="followedUsers"
            :selected-user-id="currentUserId"
            @select="selectFollowedUser"
          />
        </div>
      </Card>

      <Card class="overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b p-4">
          <div>
            <h2 class="font-semibold">候选作品</h2>
            <p class="app-muted text-sm">跨页选择会保留，提交任务后自动清空。</p>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="secondary" :disabled="candidates.length === 0" @click="togglePage">
              <Check :size="17" />{{ pageFullySelected ? '取消本页' : '选择本页' }}
            </Button>
            <Button
              v-if="sourceType === 'user'"
              variant="secondary"
              :disabled="currentUserId === null || selectAllAuthorMutation.isPending.value"
              @click="toggleAllAuthorWorks"
            >
              <Check :size="17" />
              <template v-if="selectAllAuthorMutation.isPending.value">读取全部…</template>
              <template v-else-if="allAuthorWorksSelected">
                取消全部（{{ loadedAuthorSelection?.artworkIds.length ?? 0 }}）
              </template>
              <template v-else>选择全部</template>
            </Button>
            <Button
              variant="ghost"
              :disabled="selection.selectedIds.length === 0"
              @click="selection.clear"
            >
              <X :size="17" />清空
            </Button>
          </div>
        </div>

        <DiscoveryCandidateResults
          v-if="candidates.length"
          :candidates="candidates"
          :selected-ids="selection.selectedIds"
          @toggle="selection.toggle"
        />
        <p v-else class="app-muted p-10 text-center">请先输入来源并预览。</p>

        <p v-if="selectAllAuthorMutation.error.value" class="px-4 pb-3 text-sm text-destructive">
          {{ errorMessage(selectAllAuthorMutation.error.value) }}
        </p>

        <div class="flex items-center justify-between border-t p-4">
          <Button
            variant="secondary"
            :disabled="discoveryPage === 0 || discoveryMutation.isPending.value"
            @click="discoveryMutation.mutate(discoveryPage - 1)"
          >
            <ChevronLeft :size="17" />上一页
          </Button>
          <span class="app-muted text-sm">第 {{ discoveryPage + 1 }} 页</span>
          <Button
            variant="secondary"
            :disabled="nextPage === null || discoveryMutation.isPending.value"
            @click="nextPage !== null && discoveryMutation.mutate(nextPage)"
          >
            下一页<ChevronRight :size="17" />
          </Button>
        </div>
      </Card>
    </section>

    <aside class="space-y-4">
      <Card class="sticky top-20 p-5">
        <h2 class="font-semibold">提交下载</h2>
        <p class="app-muted mt-1 text-sm">已选择 {{ selection.selectedIds.length }} 项</p>
        <Button
          class="mt-4 w-full"
          :disabled="selection.selectedIds.length === 0 || createMutation.isPending.value"
          @click="createMutation.mutate()"
        >
          <Download :size="18" />
          {{ createMutation.isPending.value ? '提交中…' : '创建下载任务' }}
        </Button>
        <p v-if="notice" class="mt-3 text-sm text-success">{{ notice }}</p>
        <p v-if="submissionError" class="mt-3 text-sm text-destructive">
          {{ submissionError }}
        </p>
        <p v-else-if="createMutation.error.value" class="mt-3 text-sm text-destructive">
          {{ errorMessage(createMutation.error.value) }}
        </p>
      </Card>

      <Card class="overflow-hidden">
        <div class="flex items-center justify-between border-b p-4">
          <div>
            <h2 class="font-semibold">任务与历史</h2>
          </div>
          <Button variant="ghost" @click="jobsQuery.refetch()">
            <RefreshCw :size="17" />刷新
          </Button>
        </div>
        <div v-if="jobsQuery.data.value?.items.length" class="divide-y">
          <article v-for="job in jobsQuery.data.value.items" :key="job.jobId" class="p-4">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <strong class="block truncate text-sm">{{ job.sourceLabel }}</strong>
                <span class="app-muted text-xs">{{
                  new Date(job.createdAt).toLocaleString()
                }}</span>
              </div>
              <span class="rounded-lg bg-muted px-2 py-1 text-xs text-muted-foreground">
                {{ stateLabel(job.state) }}
              </span>
            </div>
            <div class="mt-3 h-2 overflow-hidden rounded-full bg-muted">
              <div
                class="h-full bg-primary transition-all"
                :style="{ width: `${String(jobProgress(job))}%` }"
              />
            </div>
            <p class="app-muted mt-2 text-xs">
              完成 {{ job.counts.succeeded }} · 跳过 {{ job.counts.skipped }} · 失败
              {{ job.counts.failed }} · 等待 {{ job.counts.queued + job.counts.running }}
            </p>
            <p v-if="job.errorSummary" class="mt-2 text-xs text-destructive">
              {{ job.errorSummary }}
            </p>
            <div class="mt-3 flex gap-2">
              <Button
                v-if="job.state === 'queued' || job.state === 'running'"
                variant="secondary"
                :disabled="actionMutation.isPending.value"
                @click="actionMutation.mutate({ action: 'cancel', jobId: job.jobId })"
              >
                取消
              </Button>
              <Button
                v-if="job.state === 'failed' || job.state === 'partiallySucceeded'"
                variant="secondary"
                :disabled="actionMutation.isPending.value"
                @click="actionMutation.mutate({ action: 'retry', jobId: job.jobId })"
              >
                重试失败项
              </Button>
            </div>
          </article>
        </div>
        <p v-else class="app-muted p-8 text-center text-sm">暂无下载任务。</p>
      </Card>
    </aside>
  </div>
</template>
