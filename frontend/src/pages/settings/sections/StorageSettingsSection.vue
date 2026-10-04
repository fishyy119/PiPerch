<script setup lang="ts">
import { HardDrive } from '@lucide/vue'
import { useMutation } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, ref } from 'vue'

import { getHealth, migrateLibraryRoot } from '@/features/settings/settings-api'
import { useSettingField, useSettingsQuery } from '@/features/settings/useSettingField'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Input from '@ui/Input.vue'
import Slider from '@ui/Slider.vue'
import Switch from '@ui/Switch.vue'
import { toast } from '@ui/toast'

import SettingItem from '../SettingItem.vue'
import SettingsSection from '../SettingsSection.vue'

const settingsQuery = useSettingsQuery()
const libraryRoot = computed(() => settingsQuery.data.value?.libraryRoot ?? '')
const migrationStarted = ref(false)
let restartPoll = 0

const migrationMutation = useMutation({
  mutationFn: migrateLibraryRoot,
  onSuccess: (result) => {
    if (result.status === 'cancelled') {
      toast.info(result.message)
      return
    }
    migrationStarted.value = true
    toast.success(result.message)
    void waitForRestart(result.instanceId)
  },
  onError: (error) => {
    toast.error('图库迁移未启动', { description: errorMessage(error) })
  },
})

async function waitForRestart(instanceId: string) {
  const currentPoll = ++restartPoll
  while (currentPoll === restartPoll) {
    await new Promise((resolve) => window.setTimeout(resolve, 1000))
    try {
      const health = await getHealth()
      if (health.instanceId !== instanceId) {
        window.location.reload()
        return
      }
    } catch {
      // 后端重启期间连接失败属于预期状态，继续等待新实例。
    }
  }
}

onBeforeUnmount(() => {
  restartPoll += 1
})

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
      description="作品文件的本地存储位置；数据库、设置和缓存不会随之迁移。"
      control-id="library-root"
    >
      <div class="flex items-center gap-3">
        <Input id="library-root" :model-value="libraryRoot" class="min-w-0 flex-1" readonly />
        <Button
          variant="secondary"
          class="shrink-0"
          :disabled="migrationMutation.isPending.value || migrationStarted"
          @click="migrationMutation.mutate()"
        >
          {{
            migrationStarted
              ? '迁移中…'
              : migrationMutation.isPending.value
                ? '等待确认…'
                : '迁移目录'
          }}
        </Button>
      </div>
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
