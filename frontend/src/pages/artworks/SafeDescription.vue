<script setup lang="ts">
import DOMPurify from 'dompurify'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { pixivArtworkIdFromUrl } from '@/features/artworks/pixiv-artwork-link'

const props = defineProps<{ html: string; localArtworkIds: readonly number[] }>()
const router = useRouter()
const clean = computed(() => {
  const sanitized = DOMPurify.sanitize(props.html)
  const localArtworkIds = new Set(props.localArtworkIds)
  const document = new DOMParser().parseFromString(sanitized, 'text/html')
  document.querySelectorAll<HTMLAnchorElement>('a').forEach((anchor) => {
    // 站内跳转标记，保护性清除同名属性。
    anchor.removeAttribute('data-local-artwork-id')

    const href = anchor.getAttribute('href')
    if (href === null) return

    const artworkId = pixivArtworkIdFromUrl(href)
    if (artworkId !== null && localArtworkIds.has(artworkId)) {
      anchor.href = `/artworks/${String(artworkId)}`
      anchor.dataset.localArtworkId = String(artworkId)
      anchor.removeAttribute('target')
      return
    }

    // 严格限制外链行为
    anchor.target = '_blank'
    anchor.relList.add('noreferrer')
  })
  return document.body.innerHTML
})

function navigateToLocalArtwork(event: MouseEvent) {
  if (event.defaultPrevented || event.button !== 0) return
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return // 对应打开新标签页等行为，自动由浏览器操作
  if (!(event.target instanceof Element)) return

  const anchor = event.target.closest<HTMLAnchorElement>('a[data-local-artwork-id]')
  const artworkId = anchor?.dataset.localArtworkId
  if (!artworkId) return

  event.preventDefault()
  // 复用SPA的站内导航，避免重复页面加载
  void router.push(`/artworks/${artworkId}`)
}
</script>

<template>
  <!-- Pixiv 简介经 DOMPurify 清理后才允许渲染。 -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="safe-description" @click="navigateToLocalArtwork" v-html="clean" />
</template>

<style scoped>
.safe-description :deep(a) {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 0.15rem;
}

.safe-description :deep(p) {
  margin-block: 0.5rem;
}
</style>
