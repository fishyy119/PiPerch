import { onBeforeUnmount, onMounted, ref } from 'vue'

import { type SettingsSectionId, settingsSections } from './settings-sections'

export function useSettingsNavigation() {
  const activeSection = ref<SettingsSectionId>('settings-pixiv')
  let sectionObserver: IntersectionObserver | undefined

  function isSettingsSectionId(value: string): value is SettingsSectionId {
    return settingsSections.some((section) => section.id === value)
  }

  function scrollToSection(sectionId: SettingsSectionId) {
    activeSection.value = sectionId
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  onMounted(() => {
    if (!('IntersectionObserver' in window)) return

    sectionObserver = new IntersectionObserver(
      (entries) => {
        const currentEntry = entries
          .filter((entry) => entry.isIntersecting && isSettingsSectionId(entry.target.id))
          .sort(
            (left, right) =>
              Math.abs(left.boundingClientRect.top - 64) -
              Math.abs(right.boundingClientRect.top - 64),
          )[0]
        if (currentEntry && isSettingsSectionId(currentEntry.target.id)) {
          activeSection.value = currentEntry.target.id
        }
      },
      { rootMargin: '-64px 0px -65% 0px', threshold: 0 },
    )

    for (const section of settingsSections) {
      const element = document.getElementById(section.id)
      if (element) sectionObserver.observe(element)
    }
  })

  onBeforeUnmount(() => sectionObserver?.disconnect())

  return { activeSection, scrollToSection }
}
