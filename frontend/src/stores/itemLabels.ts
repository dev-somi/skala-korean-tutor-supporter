import { ref } from 'vue'
import { textbookApi } from '../api/endpoints'
import type { TextbookItem } from '../api/types'

// 교재 항목 이름표. 앱에서 한 번만 불러와 같이 쓴다. 못 불러오면 ID를 그대로 보여 준다 (기술 ADR-0029)
const items = ref<Record<string, TextbookItem>>({})
let loading: Promise<void> | null = null

export function useItemLabels() {
  if (!loading) {
    loading = textbookApi.items().then(r => { items.value = r.items }).catch(() => { loading = null })
  }
  const item = (id: string): TextbookItem | undefined => items.value[id]
  const label = (id: string) => items.value[id]?.label ?? id
  return { item, label }
}
