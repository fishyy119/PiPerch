import type { DiscoveryItem } from '@/features/discovery/discovery-api'

type PixivItem = Extract<DiscoveryItem, { source: 'pixiv' }>
type FanboxItem = Extract<DiscoveryItem, { source: 'fanbox' }>

export function discoveryItem(
  remoteId: number,
  overrides:
    Partial<PixivItem> | (Partial<FanboxItem> & Pick<FanboxItem, 'source' | 'authorId'>) = {},
): DiscoveryItem {
  const fields = {
    remoteId,
    localArtworkId: null,
    title: `作品 ${String(remoteId)}`,
    authorName: '测试作者',
    artworkType: 'illust' as const,
    pageCount: 1,
    xRestrict: 0,
    isAi: false,
    thumbnailUrl: null,
    inLibrary: false,
    previewOnly: false,
  }
  return overrides.source === 'fanbox'
    ? { ...fields, ...overrides }
    : { ...fields, source: 'pixiv', authorId: null, ...overrides }
}
