import { errorMessage } from '@/shared/errors'
import { toast } from '@ui/toast'

export async function writeToClipboard(content: string) {
  try {
    await navigator.clipboard.writeText(content)
    toast.success('已写入剪贴板')
  } catch (error) {
    toast.error('写入剪贴板失败', { description: errorMessage(error) })
  }
}
