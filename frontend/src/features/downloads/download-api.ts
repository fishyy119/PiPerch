import { z } from 'zod'

import { api } from '@/shared/api/http'

export const artworkTypeSchema = z.enum(['illust', 'manga', 'ugoira'])
export type ArtworkType = z.infer<typeof artworkTypeSchema>

export const discoveryItemSchema = z.object({
  artworkId: z.number().int().positive(),
  title: z.string(),
  authorName: z.string(),
  artworkType: artworkTypeSchema,
  pageCount: z.number().int().positive(),
  xRestrict: z.number().int().nonnegative(),
  isAi: z.boolean(),
  thumbnailUrl: z.string().startsWith('/api/pixiv-images?url=').nullable(),
  inLibrary: z.boolean(),
})
export type DiscoveryItem = z.infer<typeof discoveryItemSchema>

export const followedUserSchema = z.object({
  userId: z.number().int().positive(),
  name: z.string(),
  avatarUrl: z.string().startsWith('/api/pixiv-images?url=').nullable(),
})
export type FollowedUser = z.infer<typeof followedUserSchema>

const discoveryResponseSchema = z.object({
  items: z.array(discoveryItemSchema),
  page: z.number().int().nonnegative(),
  nextPage: z.number().int().nonnegative().nullable(),
})

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

export const downloadJobSchema = z.object({
  jobId: z.string(),
  sourceLabel: z.string(),
  state: jobStateSchema,
  createdAt: z.string(),
  startedAt: z.string().nullable(),
  finishedAt: z.string().nullable(),
  errorSummary: z.string().nullable(),
  counts: countsSchema,
})
export type DownloadJob = z.infer<typeof downloadJobSchema>

const jobPageSchema = z.object({
  items: z.array(downloadJobSchema),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})

export type DiscoveryRequest =
  | { sourceType: 'artwork'; inputs: string[]; page: number }
  | { sourceType: 'user'; userId: number; page: number }
  | { sourceType: 'series'; seriesId: number; page: number }

export async function discover(request: DiscoveryRequest) {
  return discoveryResponseSchema.parse(await api.post<unknown>('/api/discovery', request))
}

export async function listSelectableUserArtworkIds(userId: number) {
  const schema = z.object({ artworkIds: z.array(z.number().int().positive()) })
  const path = `/api/discovery/users/${encodeURIComponent(String(userId))}/selectable-artwork-ids`
  return schema.parse(await api.get<unknown>(path)).artworkIds
}

export async function listFollowedUsers() {
  const schema = z.object({ items: z.array(followedUserSchema) })
  return schema.parse(await api.get<unknown>('/api/discovery/followed-users')).items
}

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
