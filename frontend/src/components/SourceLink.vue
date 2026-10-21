<script setup lang="ts">
// 출처 글 옆의 "원문" 버튼. 누르면 선생님 컴퓨터의 원본 PDF가 출처 쪽으로 열린다 (기술 ADR-0030).
// 원본 PDF가 등록되지 않은 책이거나 예전 응답이라 book·pages가 없으면 버튼을 숨긴다.
import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { materialsApi } from '../api/endpoints'
import { useMaterials } from '../composables/useMaterials'

const props = defineProps<{ book?: string; pages?: number[] }>()

const toast = useToast()
const { books } = useMaterials()
const page = computed(() => (props.pages?.length ? Math.min(...props.pages) : null))
const canOpen = computed(() => !!props.book && page.value !== null && books.value.has(props.book))
const busy = ref(false)

async function open() {
  if (!canOpen.value || busy.value) return
  busy.value = true
  try {
    const r = await materialsApi.open(props.book!, page.value!)
    if (!r.opened) toast.add({ severity: 'warn', summary: '원문을 열지 못했어요', detail: r.message, life: 4000 })
    else if (r.message) toast.add({ severity: 'info', summary: '원문을 열었어요', detail: r.message, life: 4000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: '원문을 열지 못했어요', detail: (e as Error).message, life: 4000 })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button
    v-if="canOpen"
    type="button"
    class="ml-1 inline-flex cursor-pointer items-center gap-0.5 rounded border-0 bg-transparent px-1 align-baseline text-xs text-primary-600 hover:bg-primary-50 hover:underline disabled:opacity-50"
    :disabled="busy"
    :title="`원본 PDF ${page}쪽 열기`"
    @click.stop.prevent="open"
  ><i class="pi pi-external-link text-[0.7rem]" />원문</button>
</template>
