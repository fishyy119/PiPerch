<script setup lang="ts">
import { HardDrive } from '@lucide/vue'

import Input from '@ui/Input.vue'
import Slider from '@ui/Slider.vue'
import Switch from '@ui/Switch.vue'

import SettingItem from '../SettingItem.vue'
import SettingsSection from '../SettingsSection.vue'
import { useSettingField } from '../useSettingField'

const libraryRootField = useSettingField('libraryRoot', {
  label: '图库根目录',
  initialValue: '',
  write: (value) => value.trim(),
  validate: (value) => (value.trim() ? null : '图库根目录不能为空。'),
})
const libraryRoot = libraryRootField.value

const webpEnabledField = useSettingField('webpEnabled', {
  label: 'WebP 转换',
  initialValue: true,
})
const webpEnabled = webpEnabledField.value

const webpQualityField = useSettingField('webpQuality', {
  label: 'WebP 质量',
  initialValue: 85,
})
const webpQuality = webpQualityField.value

function updateWebpEnabled(value: boolean) {
  webpEnabled.value = value
  webpEnabledField.save()
}

function commitWebpQuality(value: number) {
  webpQuality.value = value
  webpQualityField.save()
}
</script>

<template>
  <SettingsSection
    section-id="settings-storage"
    title="存储"
    description="设置图库位置和下载图片的转换规则。"
    :icon="HardDrive"
  >
    <SettingItem
      title="图库根目录"
      description="作品文件和图库数据的本地存储位置。"
      control-id="library-root"
    >
      <Input id="library-root" v-model="libraryRoot" required @blur="libraryRootField.save" />
    </SettingItem>
    <SettingItem
      title="转换为 WebP"
      description="减小图库占用空间，不影响 Ugoira 动画包。"
      control-id="webp-enabled"
    >
      <div class="flex justify-end">
        <Switch
          id="webp-enabled"
          :model-value="webpEnabled"
          @update:model-value="updateWebpEnabled"
        />
      </div>
    </SettingItem>
    <SettingItem
      title="WebP 质量"
      description="默认 85；数值越高，画质和文件体积越大。"
      :disabled="!webpEnabled"
    >
      <div class="flex items-center gap-4">
        <Slider
          v-model="webpQuality"
          class="flex-1"
          :min="50"
          :max="100"
          :step="1"
          :disabled="!webpEnabled"
          @commit="commitWebpQuality"
        />
        <output class="min-w-9 text-right text-sm font-medium tabular-nums">
          {{ webpQuality }}
        </output>
      </div>
    </SettingItem>
  </SettingsSection>
</template>
