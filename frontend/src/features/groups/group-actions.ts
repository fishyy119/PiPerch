import { createGroup, replaceArtworkGroups } from '@/features/groups/groups-api'

export interface CreateGroupAndAddArtworkRequest {
  localArtworkId: number
  name: string
  groupIds: number[]
}

export async function createGroupAndAddArtwork(request: CreateGroupAndAddArtworkRequest) {
  const group = await createGroup(request.name)
  const groupIds = Array.from(new Set([...request.groupIds, group.groupId]))
  return replaceArtworkGroups(request.localArtworkId, groupIds)
}
