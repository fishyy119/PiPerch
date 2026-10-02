import type { DiscoveryItem } from '@/features/discovery/discovery-api'

export function discoveryItem(
  artworkId: number,
  overrides: Partial<DiscoveryItem> = {},
): DiscoveryItem {
  return {
    artworkId,
    title: `作品 ${String(artworkId)}`,
    authorName: '测试作者',
    artworkType: 'illust',
    pageCount: 1,
    xRestrict: 0,
    isAi: false,
    thumbnailUrl: null,
    inLibrary: false,
    ...overrides,
  }
}
