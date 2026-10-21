import { ref } from 'vue'
import { materialsApi } from '../api/endpoints'

// 원본 PDF가 등록된 책 목록. 화면 전체에서 한 번만 받는다 (출처마다 요청하지 않게)
const books = ref(new Set<string>())
let loading: Promise<void> | null = null

export function useMaterials() {
  loading ??= materialsApi
    .list()
    .then(r => { books.value = new Set(r.books) })
    .catch(() => { loading = null }) // ai-server가 안 떠 있으면 버튼을 숨기고, 다음 화면에서 다시 받는다
  return { books }
}
