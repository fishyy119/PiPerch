import { z } from 'zod'

import { api } from '@/shared/api/http'

const userProfileSchema = z.object({
  avatarUrl: z.string().startsWith('/api/pixiv-images?url=').nullable(),
  isFollowed: z.boolean().nullable(),
})

export type UserProfile = z.infer<typeof userProfileSchema>

const followedUserSchema = z.object({
  userId: z.number().int().positive(),
  name: z.string(),
  avatarUrl: z.string().startsWith('/api/pixiv-images?url=').nullable(),
})

export type FollowedUser = z.infer<typeof followedUserSchema>

export function userProfileKey(userId: number) {
  return ['user-profile', userId] as const
}

function userFollowPath(userId: number) {
  return `/api/authors/${encodeURIComponent(String(userId))}/follow`
}

export async function getUserProfile(userId: number) {
  const path = `/api/authors/${encodeURIComponent(String(userId))}/profile`
  return userProfileSchema.parse(await api.get<unknown>(path))
}

export async function listFollowedUsers() {
  const schema = z.object({ items: z.array(followedUserSchema) })
  return schema.parse(await api.get<unknown>('/api/authors/followed')).items
}

export async function followUser(userId: number) {
  await api.post<undefined>(userFollowPath(userId))
}

export async function unfollowUser(userId: number) {
  await api.delete<undefined>(userFollowPath(userId))
}
