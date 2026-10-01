<script setup lang="ts">
import { Compass, Download, Images, Menu, Settings, X } from '@lucide/vue'
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const mobileOpen = ref(false)
const pageTitle = computed(() =>
  typeof route.meta.title === 'string' ? route.meta.title : 'PiPerch',
)
const showPageTitle = computed(() => route.meta.hideTitle !== true)
const navigation = [
  { to: '/discover', label: '发现', icon: Compass },
  { to: '/downloads', label: '下载', icon: Download },
  { to: '/gallery', label: '图库', icon: Images },
  { to: '/settings', label: '设置', icon: Settings },
]
</script>

<template>
  <div class="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
    <div
      v-if="mobileOpen"
      class="fixed inset-0 z-30 bg-overlay/45 lg:hidden"
      @click="mobileOpen = false"
    />
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-40 w-60 -translate-x-full lg:sticky lg:top-0 lg:h-screen lg:translate-x-0',
        'flex flex-col transition',
        'border-r border-sidebar-border bg-sidebar text-sidebar-foreground',
        mobileOpen ? 'translate-x-0' : '',
      ]"
    >
      <div class="flex h-16 items-center justify-between border-b px-5">
        <RouterLink to="/gallery" class="flex items-center gap-3" @click="mobileOpen = false">
          <span
            class="grid size-9 place-items-center rounded-xl bg-sidebar-primary font-bold text-sidebar-primary-foreground"
            >P</span
          >
          <span>
            <strong class="block leading-tight">PiPerch</strong>
            <small class="app-muted">Local Pixiv Library</small>
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
          class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-muted-foreground transition hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          active-class="bg-sidebar-accent! text-sidebar-accent-foreground!"
          @click="mobileOpen = false"
        >
          <component :is="item.icon" :size="19" />
          {{ item.label }}
        </RouterLink>
      </nav>
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
