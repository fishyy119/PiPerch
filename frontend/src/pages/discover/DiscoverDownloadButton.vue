<script setup lang="ts">
import { Download, LoaderCircle } from '@lucide/vue'

import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useDownloadSubmissionStore } from '@/features/downloads/download-submission'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import { toast } from '@ui/toast'

const selection = useDownloadSelection()
const submission = useDownloadSubmissionStore()

async function submitSelection() {
  try {
    const result = await submission.submit('发现')
    if (result.failedError !== null) {
      toast.error('部分下载任务提交失败', {
        description: `已提交 ${String(result.createdJobCount)} 个下载任务，仍有 ${String(result.remainingCount)} 项未提交：${errorMessage(result.failedError)}`,
      })
      return
    }
    toast.success(
      result.createdJobCount === 1
        ? '下载任务已提交。'
        : `已分批提交 ${String(result.createdJobCount)} 个下载任务。`,
    )
  } catch (error) {
    toast.error('下载任务提交失败', { description: errorMessage(error) })
  }
}
</script>

<template>
  <Transition
    enter-active-class="transition duration-150 ease-out"
    enter-from-class="translate-y-3 opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition duration-100 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="translate-y-3 opacity-0"
  >
    <Button
      v-if="selection.selectedIds.length"
      size="icon"
      class="fixed right-4 bottom-4 z-20 size-14! rounded-full! shadow-xl md:right-6 md:bottom-6"
      :disabled="submission.isPending"
      :title="`提交 ${String(selection.selectedIds.length)} 个候选作品`"
      @click="submitSelection"
    >
      <LoaderCircle v-if="submission.isPending" class="animate-spin" :size="23" />
      <Download v-else :size="23" />
      <span
        :class="[
          'absolute -right-1 -bottom-1 grid min-h-5 min-w-5 place-items-center rounded-full px-1',
          'bg-background text-[0.6875rem] leading-none font-semibold text-primary tabular-nums',
          'shadow-sm ring-2 ring-background',
        ]"
      >
        {{ selection.selectedIds.length }}
      </span>
    </Button>
  </Transition>
</template>
