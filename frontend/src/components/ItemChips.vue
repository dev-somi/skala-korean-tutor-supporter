<script setup lang="ts">
// 교재 항목 ID 목록을 단어·문법 이름 칩으로 보여 준다. 마우스를 올리면 ID와 뜻이 보인다 (기술 ADR-0029)
import { useItemLabels } from '../stores/itemLabels'

defineProps<{ ids: string[]; empty?: string }>()
const { item, label } = useItemLabels()

const tip = (id: string) => [id, item(id)?.meaning].filter(Boolean).join(' · ')
const tone = (id: string) =>
  item(id)?.kind === 'grammar' ? 'border-primary-200 bg-primary-50 text-primary-800 font-semibold' : 'border-surface-200 bg-white text-surface-700'
</script>

<template>
  <span v-if="!ids.length" class="text-xs text-surface-400">{{ empty ?? '없음' }}</span>
  <span v-else class="inline-flex flex-wrap gap-1 align-middle">
    <span v-for="id in ids" :key="id" :title="tip(id)" class="rounded-md border px-1.5 py-0.5 text-xs" :class="tone(id)">{{ label(id) }}</span>
  </span>
</template>
