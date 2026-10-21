<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import { CATEGORY_NAMES, type Category, type CategoryDraft, type CultureNote, type FrameStep } from '../api/types'
import SourceLink from './SourceLink.vue'
import ItemChips from './ItemChips.vue'
import { useItemLabels } from '../stores/itemLabels'

// 고정된 7단계 수업 틀 (기획 ADR-0015). 범주 내용은 drafts에서, 문화는 culture에서 꺼내 보여 준다.
const props = defineProps<{
  frame: FrameStep[]
  drafts: Partial<Record<Category, CategoryDraft>> | null
  culture?: CultureNote[]
}>()
const toast = useToast()
const { label } = useItemLabels()

// 선생님이 고른 문화 후보 (기본은 1순위). 화면에서만 바꾸고 저장하지 않는다 (기술 ADR-0023)
const picked = ref(props.frame.find(s => s.key === 'present')?.culture ?? 0)
const cultureNote = () => (props.culture?.length ? props.culture[picked.value] : null)

function examplesOf(c: Category): string[] {
  return (props.drafts?.[c]?.examples ?? []).map(e => e.korean).slice(0, 3)
}

/** 선생님이 자기 자료에 붙여 넣을 수 있게 수업안 전체를 글로 만든다 */
function asText(): string {
  const lines: string[] = []
  props.frame.forEach((s, i) => {
    lines.push(`${i + 1}. ${s.name} (${s.minutes}분) — ${s.guide}`)
    for (const item of s.items) lines.push(`   - ${item}`)
    for (const c of s.categories) {
      const d = props.drafts?.[c]
      if (!d) continue
      lines.push(`   [${CATEGORY_NAMES[c]}] ${d.item_ids.map(label).join(', ')}`)
      for (const ex of examplesOf(c)) lines.push(`   예) ${ex}`)
    }
    if (s.culture !== undefined) {
      const n = cultureNote()
      lines.push(n ? `   [문화] ${n.summary} (${n.source})\n   [비교 질문] ${n.question_ko} / ${n.question_l1}` : '   [문화] (선생님이 채워 주세요)')
    }
  })
  return lines.join('\n')
}

async function copy() {
  await navigator.clipboard.writeText(asText())
  toast.add({ severity: 'success', summary: '수업안을 복사했어요', life: 2000 })
}
</script>

<template>
  <section class="mb-4 rounded-xl border border-surface-200 bg-white p-4">
    <div class="mb-3 flex items-center gap-2">
      <h3 class="m-0 text-base font-bold"><i class="pi pi-list mr-1 text-primary-600" />수업 진행 ({{ frame.reduce((a, s) => a + s.minutes, 0) }}분)</h3>
      <div class="flex-1" />
      <Button label="글로 복사" icon="pi pi-copy" size="small" severity="secondary" outlined @click="copy" />
    </div>
    <ol class="m-0 list-none space-y-3 p-0">
      <li v-for="(s, i) in frame" :key="s.key" class="flex gap-3">
        <div class="flex w-14 shrink-0 flex-col items-center">
          <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-800">{{ i + 1 }}</span>
          <span class="mt-1 text-xs text-surface-500">{{ s.minutes }}분</span>
        </div>
        <div class="min-w-0 flex-1 border-b border-surface-100 pb-3">
          <div class="font-semibold">{{ s.name }}</div>
          <p class="m-0 mt-0.5 text-sm text-surface-500">{{ s.guide }}</p>
          <ul v-if="s.items.length" class="m-0 mt-2 space-y-1 pl-5 text-sm">
            <li v-for="(item, j) in s.items" :key="j">{{ item }}</li>
          </ul>
          <div v-for="c in s.categories" :key="c" class="mt-2 grid gap-1 text-sm sm:grid-cols-[5.5rem_1fr]">
            <span class="pt-0.5 text-xs font-semibold text-surface-500">{{ CATEGORY_NAMES[c] }}</span>
            <div>
              <ItemChips :ids="drafts?.[c]?.item_ids ?? []" />
              <div v-if="examplesOf(c).length" class="mt-1 text-surface-600">예) {{ examplesOf(c).join(' / ') }}</div>
            </div>
          </div>
          <div v-if="s.culture !== undefined" class="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
            <div class="mb-1 flex flex-wrap items-center gap-2">
              <span class="font-semibold text-amber-800"><i class="pi pi-globe mr-1" />문화 포인트</span>
              <template v-if="culture?.length && culture.length > 1">
                <button
                  v-for="(n, k) in culture"
                  :key="k"
                  :title="n.summary"
                  type="button"
                  class="rounded-full border px-2 py-0.5 text-xs"
                  :class="k === picked ? 'border-amber-600 bg-amber-600 text-white' : 'border-amber-300 bg-white text-amber-800'"
                  @click="picked = k"
                >후보 {{ k + 1 }}</button>
              </template>
            </div>
            <template v-if="cultureNote()">
              <p class="m-0">{{ cultureNote()!.summary }}</p>
              <p class="m-0 mt-1 text-surface-700">비교 질문: {{ cultureNote()!.question_ko }} <span class="text-surface-500">/ {{ cultureNote()!.question_l1 }}</span></p>
              <details class="mt-1 text-xs text-surface-500">
                <summary class="cursor-pointer">출처: {{ cultureNote()!.source }}<SourceLink :book="cultureNote()!.book" :pages="cultureNote()!.pages" /></summary>
                <p class="m-0 mt-1 whitespace-pre-line">{{ cultureNote()!.excerpt }}</p>
              </details>
            </template>
            <p v-else class="m-0 text-amber-800">세종학당 자료에서 이번 과에 맞는 문화를 찾지 못했어요. 선생님이 채워 주세요.</p>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>
