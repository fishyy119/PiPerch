import { Cookie, Download, HardDrive } from '@lucide/vue'

export const settingsSections = [
  { id: 'settings-pixiv', label: 'Pixiv', icon: Cookie },
  { id: 'settings-download', label: '下载与网络', icon: Download },
  { id: 'settings-storage', label: '存储', icon: HardDrive },
] as const

export type SettingsSectionId = (typeof settingsSections)[number]['id']
