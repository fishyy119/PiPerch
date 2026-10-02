<script setup lang="ts">
import { ChevronDown, ChevronUp, Download, ImageOff, LoaderCircle, RefreshCw, X } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { discover } from '@/features/discovery/discovery-api'
import {
  cancelDownloadJob,
  createDownloadJob,
  type DownloadJob,
  listDownloadJobs,
  retryDownloadJob,
} from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'

const props = defineProps<{ sourceLabel: string }>()
const queryClient = useQueryClient()
const selection = useDownloadSelection()
const notice = ref('')
const submissionError = ref('')
const previewExpanded = ref(false)
const previewGrid = ref<HTMLElement | null>(null)

const PREVIEW_ITEM_WIDTH_PX = 78
const PREVIEW_GAP_PX = 8
const PREVIEW_ROW_COUNT = 4
const previewLimit = ref(0)
const previewEntries = computed(() => selection.selectedEntries.slice(0, previewLimit.value))
const hiddenPreviewCount = computed(() =>
  previewLimit.value === 0 ? 0 : Math.max(selection.selectedIds.length - previewLimit.value, 0),
)
const missingPreviewIds = computed(() =>
  previewEntries.value.filter((entry) => entry.item === null).map((entry) => entry.artworkId),
)

watch(
  previewGrid,
  (element, _previous, onCleanup) => {
    if (element === null) return

    const updateLimit = (width: number) => {
      if (width <= 0) return
      const columns = Math.max(
        1,
        Math.floor((width + PREVIEW_GAP_PX) / (PREVIEW_ITEM_WIDTH_PX + PREVIEW_GAP_PX)),
      )
      previewLimit.value = columns * PREVIEW_ROW_COUNT
    }
    updateLimit(element.clientWidth)

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry !== undefined) updateLimit(entry.contentRect.width)
    })
    observer.observe(element)
    onCleanup(() => observer.disconnect())
  },
  { flush: 'post' },
)

const previewQuery = useQuery({
  queryKey: computed(() => ['download-selection-preview', missingPreviewIds.value]),
  queryFn: async () => {
    const result = await discover({
      sourceType: 'artwork',
      inputs: missingPreviewIds.value.map(String),
      page: 0,
    })
    return result.items
  },
  enabled: computed(() => previewExpanded.value && missingPreviewIds.value.length > 0),
  retry: false,
})

watch(
  () => previewQuery.data.value,
  (items) => {
    if (items !== undefined) selection.remember(items)
  },
)

watch(
  () => selection.selectedIds.length,
  (count) => {
    if (count !== 0) return
    previewExpanded.value = false
  },
)

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
          `${props.sourceLabel}来源（${String(artworkIds.length)} 项${batchSuffix}）`,
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
onBeforeUnmount(() => {
  events.close()
})

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
  const completedWorks =
    job.counts.succeeded + job.counts.skipped + job.counts.failed + job.counts.cancelled
  const progress = job.progress
  let currentWorkProgress = 0
  if (progress?.totalPages) {
    currentWorkProgress = Math.min(progress.completedPages / progress.totalPages, 0.99)
  }
  return ((completedWorks + currentWorkProgress) / Math.max(1, total)) * 100
}

function progressLabel(job: DownloadJob) {
  const progress = job.progress
  if (progress === null) return null
  if (progress.phase === 'preparing') {
    return `作品 ${String(progress.currentArtworkId)} · 正在读取作品信息`
  }
  if (progress.phase === 'finalizing') {
    return `作品 ${String(progress.currentArtworkId)} · 图片处理与入库中`
  }
  return progress.totalPages === null
    ? `作品 ${String(progress.currentArtworkId)} · 正在准备下载`
    : `作品 ${String(progress.currentArtworkId)} · ${String(progress.completedPages)} / ${String(progress.totalPages)} 页`
}
</script>

<template>
  <aside class="space-y-4">
    <Card class="sticky top-20 p-5">
      <h2 class="font-semibold">提交下载</h2>
      <div class="mt-1 flex items-center justify-between gap-3">
        <p class="text-sm text-muted-foreground">已选择 {{ selection.selectedIds.length }} 项</p>
        <button
          v-if="selection.selectedIds.length"
          type="button"
          class="inline-flex cursor-pointer items-center gap-1 text-xs text-muted-foreground transition hover:text-foreground"
          @click="previewExpanded = !previewExpanded"
        >
          {{ previewExpanded ? '收起预览' : '展开预览' }}
          <ChevronUp v-if="previewExpanded" :size="14" />
          <ChevronDown v-else :size="14" />
        </button>
      </div>
      <div v-if="previewExpanded && selection.selectedIds.length" class="mt-4">
        <div
          ref="previewGrid"
          class="grid grid-cols-[repeat(auto-fill,79.5px)] justify-between gap-2"
        >
          <div
            v-for="entry in previewEntries"
            :key="entry.artworkId"
            class="relative aspect-square overflow-hidden rounded-lg bg-muted"
            :title="entry.item?.title ?? `作品 ${String(entry.artworkId)}`"
          >
            <LoaderCircle
              v-if="entry.item === null && previewQuery.isFetching.value"
              class="absolute inset-0 m-auto animate-spin text-muted-foreground"
              :size="20"
            />
            <template v-else>
              <ImageOff class="absolute inset-0 m-auto text-muted-foreground" :size="20" />
              <img
                v-if="entry.item?.thumbnailUrl"
                class="relative size-full bg-muted object-cover"
                :src="entry.item.thumbnailUrl"
                alt=""
                loading="lazy"
                @error="($event.currentTarget as HTMLImageElement).remove()"
              />
            </template>
            <button
              type="button"
              :class="[
                'absolute top-1 right-1 inline-flex size-6 cursor-pointer items-center justify-center rounded-full',
                'bg-background/85 text-foreground shadow-sm backdrop-blur-sm transition',
                'hover:bg-destructive hover:text-destructive-foreground',
              ]"
              :title="`从队列移除作品 ${String(entry.artworkId)}`"
              @click="selection.removeIds([entry.artworkId])"
            >
              <X :size="14" />
            </button>
          </div>
        </div>
        <p v-if="previewQuery.isFetching.value" class="mt-2 text-xs text-muted-foreground">
          正在加载作品预览…
        </p>
        <div
          v-else-if="previewQuery.error.value && missingPreviewIds.length"
          class="mt-2 flex items-center justify-between gap-2"
        >
          <p class="text-xs text-destructive">
            {{ errorMessage(previewQuery.error.value) }}
          </p>
          <Button variant="ghost" size="small" @click="previewQuery.refetch()">重试</Button>
        </div>
        <p v-if="hiddenPreviewCount" class="mt-2 text-xs text-muted-foreground">
          另有 {{ hiddenPreviewCount }} 项未展示
        </p>
      </div>
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
        <h2 class="font-semibold">任务与历史</h2>
        <Button variant="ghost" @click="jobsQuery.refetch()"><RefreshCw :size="17" />刷新</Button>
      </div>
      <div v-if="jobsQuery.data.value?.items.length" class="divide-y">
        <article v-for="job in jobsQuery.data.value.items" :key="job.jobId" class="p-4">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <strong class="block truncate text-sm">{{ job.sourceLabel }}</strong>
              <span class="text-xs text-muted-foreground">
                {{ new Date(job.createdAt).toLocaleString() }}
              </span>
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
          <p class="mt-2 text-xs text-muted-foreground">
            完成 {{ job.counts.succeeded }} · 跳过 {{ job.counts.skipped }} · 失败
            {{ job.counts.failed }} · 等待 {{ job.counts.queued + job.counts.running }}
          </p>
          <p v-if="progressLabel(job)" class="mt-1 text-xs text-muted-foreground">
            {{ progressLabel(job) }}
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
      <p v-else class="p-8 text-center text-sm text-muted-foreground">暂无下载任务。</p>
    </Card>
  </aside>
</template>
