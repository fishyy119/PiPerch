import { z } from 'zod'

import { artworkTypeSchema } from '@/features/artworks/artwork'
import type { ArtworkSource, DownloadReference } from '@/features/artworks/artwork-source'
import { authorSummarySchema } from '@/features/authors/author-api'
import { api, type ApiRequestOptions } from '@/shared/api/http'

const discoveryItemFields = {
  artworkId: z.number().int().positive(),
  localArtworkId: z.number().int().positive().nullable(),
  title: z.string(),
  authorName: z.string(),
  artworkType: artworkTypeSchema,
  pageCount: z.number().int().positive(),
  xRestrict: z.number().int().nonnegative().nullable(),
  isAi: z.boolean().nullable(),
  thumbnailUrl: z
    .union([
      z.string().startsWith('/api/pixiv-images?url='),
      z.string().startsWith('/api/fanbox-images?url='),
    ])
    .nullable(),
  inLibrary: z.boolean(),
}

export const discoveryItemSchema = z
  .discriminatedUnion('source', [
    z.object({
      ...discoveryItemFields,
      source: z.literal('pixiv'),
      authorId: z.number().int().positive().nullable(),
    }),
    z.object({
      ...discoveryItemFields,
      source: z.literal('fanbox'),
      authorId: z.number().int().positive(),
    }),
  ])
  .transform(({ artworkId, ...item }) => ({ ...item, remoteId: artworkId }))
export type DiscoveryItem = z.infer<typeof discoveryItemSchema>

export const recommendedUserSchema = z.object({
  userId: z.number().int().positive(),
  name: z.string(),
  comment: z.string(),
  avatarUrl: z.string().startsWith('/api/pixiv-images?url=').nullable(),
  isFollowed: z.boolean(),
  artworks: z.array(discoveryItemSchema),
})
export type RecommendedUser = z.infer<typeof recommendedUserSchema>

export const bookmarkVisibilitySchema = z.enum(['public', 'private'])
export type BookmarkVisibility = z.infer<typeof bookmarkVisibilitySchema>

export const bookmarkFolderReferenceSchema = z.object({
  visibility: bookmarkVisibilitySchema,
  tag: z.string().nullable(),
})
export type BookmarkFolderReference = z.infer<typeof bookmarkFolderReferenceSchema>

export const bookmarkFolderSchema = bookmarkFolderReferenceSchema.extend({
  kind: z.enum(['all', 'uncategorized', 'tag']),
  name: z.string(),
  itemCount: z.number().int().nonnegative(),
})
export type BookmarkFolder = z.infer<typeof bookmarkFolderSchema>

const discoveryResponseSchema = z.object({
  items: z.array(discoveryItemSchema),
  page: z.number().int().nonnegative(),
  nextPage: z.number().int().nonnegative().nullable(),
  totalPages: z.number().int().nonnegative().nullable().default(null),
  failures: z
    .array(
      z
        .object({ artworkId: z.number().int().positive(), message: z.string() })
        .transform(({ artworkId, ...failure }) => ({ ...failure, remoteId: artworkId })),
    )
    .default([]),
})

const recommendationsResponseSchema = z.object({
  items: z.array(discoveryItemSchema),
})

const recommendedUsersResponseSchema = z.object({
  items: z.array(recommendedUserSchema),
})

const artworkPreviewResponseSchema = z.object({
  urls: z.array(
    z.union([
      z.string().startsWith('/api/pixiv-images?url='),
      z.string().startsWith('/api/fanbox-images?url='),
    ]),
  ),
})

export type DiscoveryRequest =
  | { sourceType: 'artwork'; inputs: string[]; page: number }
  | { sourceType: 'search'; keyword: string; page: number }
  | { sourceType: 'user'; source?: ArtworkSource; userId: number; page: number }
  | { sourceType: 'followUpdates'; page: number }
  | { sourceType: 'bookmark'; folder: BookmarkFolderReference; page: number }
  | { sourceType: 'series'; seriesId: number; page: number }

export async function discover(request: DiscoveryRequest) {
  return discoveryResponseSchema.parse(await api.post<unknown>('/api/discovery', request))
}

export async function listRecommendations() {
  return recommendationsResponseSchema.parse(
    await api.get<unknown>('/api/discovery/recommendations'),
  ).items
}

export async function listArtworkRecommendations(artworkId: number, options?: ApiRequestOptions) {
  const path = `/api/discovery/artworks/${encodeURIComponent(String(artworkId))}/recommendations`
  return recommendationsResponseSchema.parse(await api.get<unknown>(path, options)).items
}

export async function listRecommendedUsers() {
  return recommendedUsersResponseSchema.parse(
    await api.get<unknown>('/api/discovery/recommended-users'),
  ).items
}

export async function listArtworkPreviewUrls(artwork: DownloadReference) {
  const query =
    artwork.source === 'fanbox' ? `?source=fanbox&authorId=${String(artwork.authorId)}` : ''
  const path = `/api/discovery/artworks/${encodeURIComponent(String(artwork.remoteId))}/preview${query}`
  return artworkPreviewResponseSchema.parse(await api.get<unknown>(path)).urls
}

export async function listSelectableUserArtworkIds(
  userId: number,
  source: ArtworkSource = 'pixiv',
) {
  const schema = z.object({ artworkIds: z.array(z.number().int().positive()) })
  const path = `/api/discovery/users/${encodeURIComponent(String(userId))}/selectable-artwork-ids${source === 'fanbox' ? '?source=fanbox' : ''}`
  return schema.parse(await api.get<unknown>(path)).artworkIds
}

export async function searchFanboxAuthors(query: string) {
  const schema = z.object({ items: z.array(authorSummarySchema) })
  return schema.parse(
    await api.get<unknown>(`/api/discovery/fanbox/authors?query=${encodeURIComponent(query)}`),
  ).items
}

export async function listBookmarkFolders() {
  const schema = z.object({ items: z.array(bookmarkFolderSchema) })
  return schema.parse(await api.get<unknown>('/api/discovery/bookmark-folders')).items
}

export async function listSelectableBookmarkArtworkIds(folders: BookmarkFolderReference[]) {
  const schema = z.object({ artworkIds: z.array(z.number().int().positive()) })
  return schema.parse(
    await api.post<unknown>('/api/discovery/bookmarks/selectable-artwork-ids', { folders }),
  ).artworkIds
}
