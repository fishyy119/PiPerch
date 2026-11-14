<script setup lang="ts">
import { Compass, Dices, Download, Folders, Images, Menu, Settings, X } from '@lucide/vue'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, nextTick, onScopeDispose, ref } from 'vue'
import {
  isNavigationFailure,
  NavigationFailureType,
  RouterLink,
  RouterView,
  useRoute,
  useRouter,
} from 'vue-router'

import { useAppEvents } from '@/app/useAppEvents'
import { useRandomArtwork } from '@/features/artworks/useRandomArtwork'
import { imageRequests } from '@/shared/lib/image-loading'
import { Button } from '@ui/button'
import { cn } from '@ui/cn'

useAppEvents()

const route = useRoute()
const router = useRouter()
const queryClient = useQueryClient()

function retryUnfinishedImages() {
  // 视图更新后，只恢复仍被使用的未完成图片，保留已加载的结果。
  void nextTick(() => {
    void imageRequests.retryUnfinished(queryClient)
  })
}

onScopeDispose(
  router.beforeEach(() => {
    void imageRequests.cancel(queryClient)
  }),
)
onScopeDispose(
  router.afterEach((_to, _from, failure) => {
    // 被下一次导航取代时，由后续页面决定需要加载的图片。
    if (!isNavigationFailure(failure, NavigationFailureType.cancelled)) retryUnfinishedImages()
  }),
)
onScopeDispose(router.onError(retryUnfinishedImages))

const mobileOpen = ref(false)
const { openRandomArtwork } = useRandomArtwork()
const showRandomShortcut = computed(
  () => route.path === '/gallery' || route.params.artworkId !== undefined,
)

function selectRandomArtwork() {
  mobileOpen.value = false
  void openRandomArtwork()
}

const pageTitle = computed(() =>
  typeof route.meta.title === 'string' ? route.meta.title : 'PiPerch',
)
const showPageTitle = computed(() => route.meta.hideTitle !== true)
const navigation = [
  { to: '/discover', label: '发现', icon: Compass },
  { to: '/downloads', label: '下载', icon: Download },
  { to: '/gallery', label: '图库', icon: Images },
  { to: '/groups', label: '分组', icon: Folders },
  { to: '/settings', label: '设置', icon: Settings },
]
</script>

<template>
  <div class="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
    <div
      v-if="mobileOpen"
      class="fixed inset-0 z-30 bg-foreground/45 lg:hidden dark:bg-background/45"
      @click="mobileOpen = false"
    />
    <aside
      :class="
        cn(
          'fixed inset-y-0 left-0 z-40 w-60 -translate-x-full lg:sticky lg:top-0 lg:h-screen lg:translate-x-0',
          'flex flex-col transition',
          'border-r border-border bg-card text-card-foreground',
          mobileOpen ? 'translate-x-0' : '',
        )
      "
    >
      <div class="flex h-16 items-center justify-between border-b px-5">
        <RouterLink to="/gallery" class="flex items-center gap-3" @click="mobileOpen = false">
          <span
            class="grid size-9 place-items-center rounded-xl bg-primary font-bold text-primary-foreground"
            >P</span
          >
          <span>
            <strong class="block leading-tight">PiPerch</strong>
            <small class="text-muted-foreground">Local Pixiv Library</small>
          </span>
        </RouterLink>
        <button class="lg:hidden" type="button" @click="mobileOpen = false">
          <X :size="20" />
        </button>
      </div>
      <nav class="grid gap-1 p-3">
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-muted-foreground transition hover:bg-accent/10 hover:text-foreground"
          active-class="bg-accent/15! text-foreground!"
          @click="mobileOpen = false"
        >
          <component :is="item.icon" :size="19" />
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="mx-3 border-t pt-3">
        <Button
          variant="ghost"
          class="w-full justify-start gap-3 px-3 py-2.5 font-normal text-muted-foreground hover:bg-accent/10 hover:text-foreground"
          @click="selectRandomArtwork"
        >
          <Dices :size="19" />
          随机作品
          <kbd
            v-if="showRandomShortcut"
            class="ml-auto rounded border px-1.5 text-xs text-muted-foreground"
            >R</kbd
          >
        </Button>
      </div>
    </aside>

    <div class="min-w-0">
      <header
        class="sticky top-0 z-20 flex min-h-16 items-center gap-4 border-b bg-card/95 px-4 text-card-foreground backdrop-blur md:px-6"
      >
        <button class="lg:hidden" type="button" @click="mobileOpen = true">
          <Menu :size="22" />
        </button>
        <h1 v-if="showPageTitle" class="shrink-0 font-semibold">{{ pageTitle }}</h1>
        <div
          id="topbar-actions"
          class="flex min-w-0 flex-1"
          :class="showPageTitle ? 'ml-auto justify-end' : 'justify-start'"
        />
      </header>
      <main :class="route.meta.flushContent === true ? 'w-full' : 'w-full p-4 md:p-6'">
        <RouterView />
      </main>
    </div>
  </div>
</template>
