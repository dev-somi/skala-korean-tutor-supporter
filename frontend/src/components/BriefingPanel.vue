<script setup lang="ts">
import Panel from 'primevue/panel'
import Tag from 'primevue/tag'
import { computed } from 'vue'
import type { Briefing } from '../api/types'
import SourceLink from './SourceLink.vue'
import { useItemLabels } from '../stores/itemLabels'

const props = defineProps<{ briefing: Briefing | null; collapsed?: boolean }>()
const { label } = useItemLabels()

// 모국어 칸의 출처 표시. 하나라도 덜 믿을 만한 출처가 있으면 그쪽으로 표시한다
const l1Tag = computed(() => {
  const origins = new Set((props.briefing?.l1_sources ?? []).map(s => s.origin))
  if (!props.briefing?.l1_sources) return { value: 'AI 생성 · 검수 필요', severity: 'warn' }
  if (origins.has('llm')) return { value: '일부 AI 생성 · 검수 필요', severity: 'warn' }
  if (origins.has('draft')) return { value: 'Claude 초안 · 검수 전', severity: 'info' }
  return { value: '선생님 검수', severity: 'success' }
})
</script>

<template>
  <Panel v-if="briefing" header="선생님 브리핑" toggleable :collapsed="collapsed" class="mb-4">
    <!-- 자료에서 자동으로 만든 단원 시트 (기획 ADR-0030): 이번 과 항목을 선생님이 확인해야 한다 -->
    <div v-if="briefing.unit_sheet?.status === 'draft'" class="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <i class="pi pi-exclamation-triangle mr-1" /><b>검수 전 단원</b> — 이번 과의 문법·어휘는 지침서에서 자동으로 뽑았어요. 빠지거나 틀린 항목이 있을 수 있으니 원문과 비교해 주세요.
      <ul v-if="briefing.unit_sheet.notes.length" class="m-0 mt-1 pl-5 text-xs">
        <li v-for="(n, i) in briefing.unit_sheet.notes" :key="i">{{ n }}</li>
      </ul>
    </div>
    <div class="grid gap-5 md:grid-cols-2">
      <section>
        <h4 class="mb-2 mt-0 text-sm font-bold text-primary-700"><i class="pi pi-book mr-1" />문법 설명 포인트 <Tag v-if="briefing.references?.length" value="지침서 근거" severity="success" class="ml-1" /></h4>
        <div v-for="g in briefing.grammar_points" :key="g.item_id" class="mb-3">
          <div class="mb-1 inline-block rounded-md border border-primary-200 bg-primary-50 px-1.5 py-0.5 text-sm font-semibold text-primary-800" :title="g.item_id">{{ label(g.item_id) }}</div>
          <ul class="m-0 space-y-1 pl-5 text-sm">
            <li v-for="(p, i) in g.key_points" :key="i">{{ p }}</li>
          </ul>
        </div>
      </section>
      <section>
        <h4 class="mb-2 mt-0 text-sm font-bold text-orange-700"><i class="pi pi-exclamation-circle mr-1" />모국어 화자가 자주 틀리는 점 <Tag :value="l1Tag.value" :severity="l1Tag.severity" class="ml-1" /></h4>
        <ul class="m-0 mb-4 space-y-1 pl-5 text-sm">
          <li v-for="(m, i) in briefing.common_mistakes" :key="i">{{ m }}</li>
        </ul>
        <h4 class="mb-2 mt-0 text-sm font-bold text-sky-700"><i class="pi pi-lightbulb mr-1" />이 학생 맞춤 팁</h4>
        <ul class="m-0 space-y-1 pl-5 text-sm">
          <li v-for="(t, i) in briefing.tips" :key="i">{{ t }}</li>
        </ul>
      </section>
      <section class="md:col-span-2">
        <h4 class="mb-2 mt-0 text-sm font-bold text-violet-700"><i class="pi pi-question-circle mr-1" />예상 질문과 답 <Tag :value="l1Tag.value" :severity="l1Tag.severity" class="ml-1" /></h4>
        <dl class="m-0 grid gap-2 text-sm md:grid-cols-2">
          <div v-for="(qa, i) in briefing.expected_qa" :key="i" class="rounded-lg bg-surface-50 p-3">
            <dt class="font-semibold">Q. {{ qa.question }}</dt>
            <dd class="m-0 mt-1 text-surface-700">A. {{ qa.answer }}</dd>
          </div>
        </dl>
      </section>
      <section v-if="briefing.references?.length" class="md:col-span-2">
        <h4 class="mb-2 mt-0 text-sm font-bold text-surface-600"><i class="pi pi-bookmark mr-1" />근거 자료 (원문을 확인하세요)</h4>
        <ul class="m-0 space-y-1 pl-5 text-sm text-surface-600">
          <li v-for="r in briefing.references" :key="r.source">{{ r.source }}<SourceLink :book="r.book" :pages="r.pages" /></li>
        </ul>
      </section>
    </div>
  </Panel>
</template>
