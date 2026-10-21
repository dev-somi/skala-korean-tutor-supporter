<script setup lang="ts">
import Panel from 'primevue/panel'
import Tag from 'primevue/tag'
import { computed } from 'vue'
import type { Briefing } from '../api/types'
import SourceLink from './SourceLink.vue'

const props = defineProps<{ briefing: Briefing | null; collapsed?: boolean }>()

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
    <div class="grid gap-5 md:grid-cols-2">
      <section>
        <h4 class="mb-2 mt-0 text-sm font-bold text-primary-700"><i class="pi pi-book mr-1" />문법 설명 포인트 <Tag v-if="briefing.references?.length" value="지침서 근거" severity="success" class="ml-1" /></h4>
        <div v-for="g in briefing.grammar_points" :key="g.item_id" class="mb-3">
          <div class="mb-1 font-mono text-xs text-surface-500">{{ g.item_id }}</div>
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
