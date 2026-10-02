import { useQueryClient } from '@tanstack/vue-query'
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { createDownloadJob } from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'

export interface DownloadSubmissionResult {
  createdJobCount: number
  submittedArtworkIds: number[]
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
          `${sourceLabel}来源（${String(artworkIds.length)} 项${batchSuffix}）`,
        )
        submittedArtworkIds.push(...batch)
        createdJobCount += 1
      } catch (submissionError) {
        if (createdJobCount === 0) throw submissionError
        failedError = submissionError
        break
      }
    }
    const result = {
      createdJobCount,
      submittedArtworkIds,
      remainingCount: artworkIds.length - submittedArtworkIds.length,
      failedError,
    }
    selection.removeIds(result.submittedArtworkIds)
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
