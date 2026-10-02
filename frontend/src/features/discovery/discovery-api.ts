import { z } from 'zod'

import { artworkTypeSchema } from '@/features/artworks/artwork'
import { api } from '@/shared/api/http'

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

export const recommendedUserSchema = z.object({
  userId: z.number().int().positive(),
  name: z.string(),
  comment: z.string(),
  avatarUrl: z.string().startsWith('/api/pixiv-images?url=').nullable(),
  isFollowed: z.boolean(),
  artworks: z.array(discoveryItemSchema),
})
export type RecommendedUser = z.infer<typeof recommendedUserSchema>

export const followedUserSchema = z.object({
  userId: z.number().int().positive(),
  name: z.string(),
  avatarUrl: z.string().startsWith('/api/pixiv-images?url=').nullable(),
})
export type FollowedUser = z.infer<typeof followedUserSchema>

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
})

const recommendationsResponseSchema = z.object({
  items: z.array(discoveryItemSchema),
})

const recommendedUsersResponseSchema = z.object({
  items: z.array(recommendedUserSchema),
})

const artworkPreviewResponseSchema = z.object({
  urls: z.array(z.string().startsWith('/api/pixiv-images?url=')),
})

export type DiscoveryRequest =
  | { sourceType: 'artwork'; inputs: string[]; page: number }
  | { sourceType: 'user'; userId: number; page: number }
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

export async function listRecommendedUsers() {
  return recommendedUsersResponseSchema.parse(
    await api.get<unknown>('/api/discovery/recommended-users'),
  ).items
}

export async function followUser(userId: number) {
  const path = `/api/discovery/users/${encodeURIComponent(String(userId))}/follow`
  await api.post<undefined>(path)
}

export async function listArtworkPreviewUrls(artworkId: number) {
  const path = `/api/discovery/artworks/${encodeURIComponent(String(artworkId))}/preview`
  return artworkPreviewResponseSchema.parse(await api.get<unknown>(path)).urls
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
