<script setup lang="ts">
import { settingsSections } from '@/features/settings/settings-sections'
import { useSettingsLoadFeedback } from '@/features/settings/useSettingField'
import { useSettingsNavigation } from '@/features/settings/useSettingsNavigation'

import DownloadSettingsSection from './sections/DownloadSettingsSection.vue'
import PixivSettingsSection from './sections/PixivSettingsSection.vue'
import StorageSettingsSection from './sections/StorageSettingsSection.vue'

const { activeSection, scrollToSection } = useSettingsNavigation()
useSettingsLoadFeedback()
</script>

<template>
  <div class="grid min-h-[calc(100vh-4rem)] grid-cols-[14rem_minmax(0,1fr)] items-start">
    <aside
      class="sticky top-16 flex h-[calc(100vh-4rem)] flex-col border-r border-sidebar-border bg-sidebar p-4 text-sidebar-foreground"
    >
      <nav class="grid gap-1">
        <button
          v-for="section in settingsSections"
          :key="section.id"
          type="button"
          :class="[
            'flex cursor-pointer items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition',
            activeSection === section.id
              ? 'bg-sidebar-accent text-sidebar-accent-foreground'
              : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
          ]"
          @click="scrollToSection(section.id)"
        >
          <component :is="section.icon" :size="17" />
          {{ section.label }}
        </button>
      </nav>
    </aside>

    <div class="min-w-0 px-6 py-6">
      <div class="mx-auto max-w-4xl space-y-6">
        <PixivSettingsSection />
        <DownloadSettingsSection />
        <StorageSettingsSection />
      </div>
    </div>
  </div>
</template>
