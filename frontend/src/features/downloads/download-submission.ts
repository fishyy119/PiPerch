import { useQueryClient } from '@tanstack/vue-query'
import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { DownloadReference } from '@/features/artworks/artwork-source'
import { createDownloadJob, type DownloadBatch } from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'

export interface DownloadSubmissionResult {
  createdJobCount: number
  submittedReferences: DownloadReference[]
  remainingCount: number
  failedError: unknown
}

export const useDownloadSubmissionStore = defineStore('download-submission', () => {
  const queryClient = useQueryClient()
  const selection = useDownloadSelection()
  const isPending = ref(false)
  const error = ref<unknown>(null)
  let activeSubmission: Promise<DownloadSubmissionResult> | null = null

  async function runSubmission(sourceLabel: string): Promise<DownloadSubmissionResult> {
    const references = [...selection.selectedReferences]
    const batches: DownloadBatch[] = []
    const pixiv = references.filter((item) => item.source === 'pixiv')
    const fanbox = references.filter((item) => item.source === 'fanbox')
    for (let index = 0; index < pixiv.length; index += 1000)
      batches.push({ source: 'pixiv', references: pixiv.slice(index, index + 1000) })
    for (let index = 0; index < fanbox.length; index += 1000)
      batches.push({ source: 'fanbox', references: fanbox.slice(index, index + 1000) })
    const submittedReferences: DownloadReference[] = []
    let createdJobCount = 0
    let failedError: unknown = null
    for (const [index, batch] of batches.entries()) {
      try {
        const batchSuffix =
          batches.length > 1 ? `，第 ${String(index + 1)}/${String(batches.length)} 批` : ''
        await createDownloadJob(
          batch,
          `${sourceLabel}来源（${String(references.length)} 项${batchSuffix}）`,
        )
        submittedReferences.push(...batch.references)
        selection.remove(batch.references)
        createdJobCount += 1
      } catch (submissionError) {
        if (createdJobCount === 0) throw submissionError
        failedError = submissionError
        break
      }
    }
    const result = {
      createdJobCount,
      submittedReferences,
      remainingCount: references.length - submittedReferences.length,
      failedError,
    }
    await queryClient.invalidateQueries({ queryKey: ['download-jobs'] })
    return result
  }

  function submit(sourceLabel: string): Promise<DownloadSubmissionResult> {
    if (activeSubmission !== null) return activeSubmission
    isPending.value = true
    error.value = null
    activeSubmission = (async () => {
      try {
        return await runSubmission(sourceLabel)
      } catch (submissionError) {
        error.value = submissionError
        throw submissionError
      } finally {
        isPending.value = false
        activeSubmission = null
      }
    })()
    return activeSubmission
  }

  return { isPending, error, submit }
})
