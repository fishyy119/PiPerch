import { z } from 'zod'

import { api } from '@/shared/api/http'

const jobStateSchema = z.enum([
  'queued',
  'running',
  'succeeded',
  'partiallySucceeded',
  'failed',
  'cancelled',
])

const countsSchema = z.object({
  queued: z.number().int(),
  running: z.number().int(),
  skipped: z.number().int(),
  succeeded: z.number().int(),
  failed: z.number().int(),
  cancelled: z.number().int(),
})

const downloadProgressSchema = z.object({
  currentArtworkId: z.number().int().positive(),
  completedPages: z.number().int().nonnegative(),
  totalPages: z.number().int().positive().nullable(),
  phase: z.enum(['preparing', 'downloading', 'finalizing']),
})

export const downloadJobSchema = z.object({
  jobId: z.string(),
  sourceLabel: z.string(),
  state: jobStateSchema,
  createdAt: z.string(),
  startedAt: z.string().nullable(),
  finishedAt: z.string().nullable(),
  errorSummary: z.string().nullable(),
  counts: countsSchema,
  progress: downloadProgressSchema.nullable(),
})
export type DownloadJob = z.infer<typeof downloadJobSchema>

const jobPageSchema = z.object({
  items: z.array(downloadJobSchema),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})

export async function createDownloadJob(artworkIds: number[], sourceLabel: string) {
  const schema = z.object({ jobId: z.string() })
  return schema.parse(await api.post<unknown>('/api/download-jobs', { artworkIds, sourceLabel }))
}

export async function listDownloadJobs() {
  return jobPageSchema.parse(await api.get<unknown>('/api/download-jobs?size=100'))
}

export async function cancelDownloadJob(jobId: string) {
  await api.post<undefined>(`/api/download-jobs/${encodeURIComponent(jobId)}/cancel`)
}

export async function retryDownloadJob(jobId: string) {
  await api.post<undefined>(`/api/download-jobs/${encodeURIComponent(jobId)}/retry`)
}
