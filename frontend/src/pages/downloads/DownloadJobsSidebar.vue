<script setup lang="ts">
import { Download, RefreshCw } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { onBeforeUnmount, ref } from 'vue'

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
onBeforeUnmount(() => events.close())

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
        <h2 class="font-semibold">任务与历史</h2>
        <Button variant="ghost" @click="jobsQuery.refetch()"><RefreshCw :size="17" />刷新</Button>
      </div>
      <div v-if="jobsQuery.data.value?.items.length" class="divide-y">
        <article v-for="job in jobsQuery.data.value.items" :key="job.jobId" class="p-4">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <strong class="block truncate text-sm">{{ job.sourceLabel }}</strong>
              <span class="app-muted text-xs">{{ new Date(job.createdAt).toLocaleString() }}</span>
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
</template>
