import { z } from 'zod'

import { api } from '@/shared/api/http'

export const artworkGroupSchema = z.object({
  groupId: z.number().int().positive(),
  name: z.string(),
  artworkCount: z.number().int().nonnegative(),
})
export type ArtworkGroup = z.infer<typeof artworkGroupSchema>

const artworkGroupsSchema = z.object({
  artworkId: z.number().int().positive(),
  groupIds: z.array(z.number().int().positive()),
})

export async function listGroups() {
  return z.array(artworkGroupSchema).parse(await api.get<unknown>('/api/groups'))
}

export async function createGroup(name: string) {
  return artworkGroupSchema.parse(await api.post<unknown>('/api/groups', { name }))
}

export async function renameGroup(groupId: number, name: string) {
  return artworkGroupSchema.parse(
    await api.patch<unknown>(`/api/groups/${String(groupId)}`, { name }),
  )
}

export async function deleteGroup(groupId: number) {
  return z
    .object({ deleted: z.number().int() })
    .parse(await api.delete<unknown>(`/api/groups/${String(groupId)}`))
}

export async function replaceArtworkGroups(artworkId: number, groupIds: number[]) {
  return artworkGroupsSchema.parse(
    await api.put<unknown>(`/api/artworks/${String(artworkId)}/groups`, { groupIds }),
  )
}

export async function bulkUpdateArtworkGroups(
  artworkIds: number[],
  addGroupIds: number[],
  removeGroupIds: number[],
) {
  await api.patch<undefined>('/api/artworks/groups', { artworkIds, addGroupIds, removeGroupIds })
}
