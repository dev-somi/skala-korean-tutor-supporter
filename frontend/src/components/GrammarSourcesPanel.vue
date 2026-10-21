<script setup lang="ts">
// 문법 질문(PRD F6-4)의 근거 카드. 교재 근거 / 모국어 주의점 / 등급 밖 / AI 보충을 색으로 나눠 보여 준다 (기술 ADR-0024).
// 학생에게 줄 일본어·영어 설명은 LLM이 만들지 않고 핸드북 원문을 그대로 보여 준다.
// 넓게 보기(wide)에서 형태가 둘 이상이면 나란히 놓아 비교한다. 지침서 인용은 길어서 접어 둔다.
import { computed, ref } from 'vue'
import Tag from 'primevue/tag'
import type { GrammarSources } from '../api/types'
import SourceLink from './SourceLink.vue'

const props = defineProps<{ sources: GrammarSources; wide?: boolean }>()

const expanded = ref(new Set<string>())
function toggle(id: string) {
  if (!expanded.value.delete(id)) expanded.value.add(id)
  expanded.value = new Set(expanded.value)
}

const outOfLevel = computed(() => new Map(props.sources.out_of_level.map(o => [o.form, o.level])))
const hasAi = computed(() => !!props.sources.ai_note || props.sources.removed_points.length > 0 || props.sources.ungrounded_forms.length > 0)
</script>

<template>
  <div class="mt-3 space-y-2 text-sm">
    <div class="grid gap-2" :class="wide && sources.forms.length >= 2 ? 'md:grid-cols-2' : 'grid-cols-1'">
    <div v-for="f in sources.forms" :key="f.key" class="min-w-0 rounded-lg border border-surface-200 bg-white p-2">
      <div class="mb-1 flex flex-wrap items-center gap-1">
        <span class="font-semibold">{{ f.form }}</span>
        <Tag v-if="f.level !== null" :value="`표준 ${f.level}급`" severity="secondary" />
        <Tag v-if="f.meaning" :value="f.meaning" severity="secondary" />
        <Tag v-if="outOfLevel.has(f.form)" value="아직 안 배운 문법" severity="warn" icon="pi pi-exclamation-triangle" />
        <Tag v-if="!f.grounded" value="교재 근거 없음" severity="danger" />
      </div>

      <div v-for="(s, j) in f.sources" :key="j" class="mt-1 border-l-4 border-emerald-500 pl-2">
        <div class="text-xs font-medium text-emerald-700"><i class="pi pi-book" /> 교재 근거 · {{ s.source }}<SourceLink :book="s.book" :pages="s.pages" /></div>
        <template v-if="s.kind === 'handbook'">
          <p v-if="s.explain_ko" class="my-1 leading-relaxed">{{ s.explain_ko }}</p>
          <p v-if="s.explain_native" :lang="s.native_lang ?? undefined" class="my-1 rounded bg-emerald-50 p-1.5 leading-relaxed">{{ s.explain_native }}</p>
          <ul v-if="s.examples?.length" class="my-1 list-none pl-0 text-surface-600">
            <li v-for="(ex, k) in s.examples.slice(0, 4)" :key="k">{{ ex }}</li>
          </ul>
        </template>
        <template v-else>
          <p class="my-1 pre-line leading-relaxed text-surface-700" :class="expanded.has(f.key + j) ? '' : 'line-clamp-4'">{{ s.quote }}</p>
          <button type="button" class="cursor-pointer border-0 bg-transparent p-0 text-xs text-primary-700 hover:underline" @click="toggle(f.key + j)">
            {{ expanded.has(f.key + j) ? '접기' : '더 보기' }}
          </button>
        </template>
      </div>

      <div v-for="(n, j) in f.l1_notes" :key="'n' + j" class="mt-1 border-l-4 border-amber-400 pl-2">
        <div class="text-xs font-medium text-amber-700">
          <i class="pi pi-flag" /> 자주 틀리는 점 <span v-if="!n.reviewed">(검수 전)</span>
        </div>
        <ul class="my-1 pl-4">
          <li v-for="(c, k) in n.common_mistakes" :key="k">{{ c }}</li>
        </ul>
        <p v-if="n.explain_tip" class="my-1 text-surface-600">팁: {{ n.explain_tip }}</p>
      </div>
    </div>
    </div>

    <div v-if="hasAi" class="rounded-lg border border-dashed border-surface-400 p-2 text-surface-600">
      <div class="text-xs font-medium"><i class="pi pi-sparkles" /> AI 보충 · 검수 필요</div>
      <p v-if="sources.ungrounded_forms.length" class="my-1">
        {{ sources.ungrounded_forms.join(', ') }}: 색인된 교재에 설명이 없어요. 이 문법에 대한 내용은 AI 설명입니다.
      </p>
      <p v-if="sources.ai_note" class="my-1">{{ sources.ai_note }}</p>
      <p v-if="sources.removed_points.length" class="my-1">근거에 없는 예문이 들어 있어 뺀 내용:</p>
      <ul v-if="sources.removed_points.length" class="my-1 pl-4">
        <li v-for="(p, k) in sources.removed_points" :key="k" class="line-through decoration-surface-400">{{ p }}</li>
      </ul>
    </div>
  </div>
</template>
