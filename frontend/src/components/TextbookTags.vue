<script setup lang="ts">
// 표준 항목을 다루는 교재 과를 "한국어 1 · 3과" 태그로 보여 준다. 검수 전(draft) 시트는 흐리게 (기술 ADR-0036)
import Tag from 'primevue/tag'
import type { StandardTextbookLink } from '../api/types'

defineProps<{ links: StandardTextbookLink[] }>()

const tip = (t: StandardTextbookLink) => `${t.title} ${t.unit_no}과${t.status === 'draft' ? ' (단원 시트 검수 전)' : ''}`
</script>

<template>
  <Tag
    v-for="t in links"
    :key="`${t.book}-${t.unit_no}`"
    :value="`${t.short} · ${t.unit_no}과`"
    :severity="t.status === 'reviewed' ? 'info' : 'secondary'"
    class="mr-1 !text-xs"
    v-tooltip.top="tip(t)"
  />
</template>
