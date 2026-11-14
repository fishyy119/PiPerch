import { z } from 'zod'

import { artworkTypeSchema } from '@/features/artworks/artwork'
import { artworkSourceSchema } from '@/features/artworks/artwork-source'
import { artworkGroupSchema } from '@/features/groups/groups-api'
import { api } from '@/shared/api/http'

export const tagSchema = z.object({
  tagId: z.number().int(),
  name: z.string(),
  artworkCount: z.number().int().nullable().optional(),
})
export type Tag = z.infer<typeof tagSchema>

const artworkImageSchema = z.object({
  artworkId: z.number().int().positive(),
  role: z.enum(['page', 'ugoira']),
  pageIndex: z.number().int().nonnegative().nullable(),
  width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(),
})
export type ArtworkImage = z.infer<typeof artworkImageSchema>

const artworkSummaryWireSchema = z.object({
  artworkId: z.number().int().positive(),
  source: artworkSourceSchema,
  remoteId: z.number().int().positive(),
  title: z.string(),
  artworkType: artworkTypeSchema,
  authorId: z.number().int().positive(),
  authorName: z.string(),
  seriesId: z.number().int().positive().nullable(),
  seriesTitle: z.string().nullable(),
  pageCount: z.number().int().positive(),
  xRestrict: z.number().int().nonnegative().nullable(),
  isAi: z.boolean().nullable(),
  publishedAt: z.string().nullable(),
  downloadedAt: z.string(),
  isFavorite: z.boolean(),
  groupIds: z.array(z.number().int().positive()),
})
export const artworkSummarySchema = artworkSummaryWireSchema.transform(
  ({ artworkId, ...item }) => ({
    ...item,
    localArtworkId: artworkId,
  }),
)
export type ArtworkSummary = z.infer<typeof artworkSummarySchema>

const artworkPageSchema = z.object({
  items: z.array(artworkSummarySchema),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})

const namedCountSchema = z.object({
  itemId: z.number().int().positive(),
  name: z.string(),
  count: z.number().int(),
  subtitle: z.string().nullable(),
})
const namedCountPageSchema = z.object({
  items: z.array(namedCountSchema),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})
export type NamedCount = z.infer<typeof namedCountSchema>

const artworkLinkSchema = z.object({
  source: artworkSourceSchema,
  remoteId: z.number().int().positive(),
  localArtworkId: z.number().int().positive().nullable(),
})
export type ArtworkLink = z.infer<typeof artworkLinkSchema>

export const artworkDetailSchema = artworkSummaryWireSchema
  .extend({
    description: z.string(),
    artworkLinks: z.record(z.string(), artworkLinkSchema),
    tags: z.array(tagSchema),
    groups: z.array(artworkGroupSchema.pick({ groupId: true, name: true })),
    images: z.array(artworkImageSchema),
    ugoiraFrames: z.array(z.object({ fileName: z.string(), delayMs: z.number().int() })),
  })
  .transform(({ artworkId, ...item }) => ({ ...item, localArtworkId: artworkId }))
export type ArtworkDetail = z.infer<typeof artworkDetailSchema>

export type MultiValueMatch = 'any' | 'all'
export type AuthorFilter = number | 'followed' | 'unfollowed'

export interface ArtworkListFilters {
  page: number
  size: number
  search: string
  tagIds: number[]
  tagMatch: MultiValueMatch
  authorId?: AuthorFilter
  seriesId?: number
  artworkType?: string
  rating: string
  ai: string
  favorite: string
  groupIds: number[]
  groupMatch: MultiValueMatch
  sort: string
  order: string
  randomSeed?: number
}

function artworkListQuery(filters: ArtworkListFilters) {
  const params = new URLSearchParams({
    page: String(filters.page),
    size: String(filters.size),
    search: filters.search,
    tagMatch: filters.tagMatch,
    rating: filters.rating,
    ai: filters.ai,
    favorite: filters.favorite,
    groupMatch: filters.groupMatch,
    sort: filters.sort,
    order: filters.order,
  })
  filters.tagIds.forEach((id) => params.append('tagId', String(id)))
  filters.groupIds.forEach((id) => params.append('groupId', String(id)))
  if (filters.authorId !== undefined) params.set('authorId', String(filters.authorId))
  if (filters.seriesId !== undefined) params.set('seriesId', String(filters.seriesId))
  if (filters.artworkType) params.set('artworkType', filters.artworkType)
  if (filters.randomSeed !== undefined) params.set('randomSeed', String(filters.randomSeed))
  return params
}

export async function listArtworks(filters: ArtworkListFilters) {
  return artworkPageSchema.parse(
    await api.get<unknown>(`/api/artworks?${artworkListQuery(filters).toString()}`),
  )
}

export async function listArtworkImages(artworkIds: readonly number[], signal?: AbortSignal) {
  const params = new URLSearchParams()
  artworkIds.forEach((id) => params.append('artworkId', String(id)))
  return z
    .array(artworkImageSchema)
    .parse(
      await api.get<unknown>(`/api/artworks/images?${params.toString()}`, signal ? { signal } : {}),
    )
}

export async function listTags(search = '', includeIds: number[] = []) {
  const params = new URLSearchParams({ search, limit: '100' })
  includeIds.forEach((id) => params.append('includeId', String(id)))
  return z.array(tagSchema).parse(await api.get<unknown>(`/api/tags?${params.toString()}`))
}

export async function listAuthors(search: string, includeIds: number[] = []) {
  const params = new URLSearchParams({ search, limit: '100' })
  includeIds.forEach((id) => params.append('includeId', String(id)))
  return z
    .array(namedCountSchema)
    .parse(await api.get<unknown>(`/api/authors?${params.toString()}`))
}

export async function listSeries(page: number, search: string) {
  const params = new URLSearchParams({ page: String(page), search })
  return namedCountPageSchema.parse(await api.get<unknown>(`/api/series?${params.toString()}`))
}

export async function getArtwork(artworkId: number) {
  return artworkDetailSchema.parse(await api.get<unknown>(`/api/artworks/${String(artworkId)}`))
}

export async function listRelatedArtworks(artworkId: number, limit = 12) {
  return z
    .array(artworkSummarySchema)
    .parse(
      await api.get<unknown>(`/api/artworks/${String(artworkId)}/related?limit=${String(limit)}`),
    )
}

const artworkDeleteResultSchema = z.object({
  deleted: z.number().int().nonnegative(),
  skippedFavoriteArtworkIds: z.array(z.number().int().positive()),
})
export type ArtworkDeleteResult = z.infer<typeof artworkDeleteResultSchema>

export type DeleteArtworksRequest =
  { mode: 'single'; localArtworkId: number } | { mode: 'bulk'; localArtworkIds: number[] }

export async function deleteArtworks(request: DeleteArtworksRequest) {
  const response =
    request.mode === 'single'
      ? await api.delete<unknown>(`/api/artworks/${String(request.localArtworkId)}`)
      : await api.post<unknown>('/api/artworks/bulk-delete', {
          artworkIds: request.localArtworkIds,
        })
  return artworkDeleteResultSchema.parse(response)
}
