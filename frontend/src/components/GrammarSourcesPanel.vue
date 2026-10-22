<script setup lang="ts">
// 문법 질문(PRD F6-4)의 답. 비교표(문법·등급·쓰임·교재 예문) → 핵심 차이 → 교재 근거(접힘) → AI 보충 순서다 (기술 ADR-0043).
// 쓰임 한 줄은 LLM, 예문은 코드가 핸드북에서 고른 것이다. 학생에게 줄 일본어·영어 설명은 핸드북 원문을 그대로 보여 준다.
// 근거는 문법마다 접어 두고, 표의 줄이나 근거 제목을 누르면 펼친다. 지침서 인용은 펼친 뒤에도 길면 한 번 더 접는다.
import { computed, ref } from 'vue'
import Tag from 'primevue/tag'
import type { GrammarSources } from '../api/types'
import SourceLink from './SourceLink.vue'

// text = 핵심 차이 ("• …" 줄들, 스트리밍으로 들어온다)
const props = defineProps<{ sources: GrammarSources; text?: string }>()

const open = ref(new Set<string>()) // 펼친 문법 (form.key)
const fullQuote = ref(new Set<string>()) // 끝까지 펼친 지침서 인용
function flip(set: typeof open, id: string) {
  if (!set.value.delete(id)) set.value.add(id)
  set.value = new Set(set.value)
}
const toggleForm = (key: string) => flip(open, key)
const toggleQuote = (id: string) => flip(fullQuote, id)

const outOfLevel = computed(() => new Map(props.sources.out_of_level.map(o => [o.form, o.level])))
const aiForms = computed(() => props.sources.forms.filter(f => f.ai))
const hasAi = computed(() => aiForms.value.length > 0 || !!props.sources.ai_note.trim() || props.sources.removed_points.length > 0 || props.sources.ungrounded_forms.length > 0)
const differences = computed(() => (props.text ?? '').split('\n').map(l => l.replace(/^•\s*/, '').trim()).filter(Boolean))
const sourceCount = computed(() => props.sources.forms.reduce((n, f) => n + f.sources.length + f.l1_notes.length, 0))
</script>

<template>
  <div class="space-y-3 text-sm">
    <!-- 1. 비교표 -->
    <div class="overflow-x-auto rounded-lg border border-surface-200 bg-white">
      <table class="w-full border-collapse text-left">
        <thead class="bg-surface-50 text-xs text-surface-500">
          <tr>
            <th class="px-2 py-1.5 font-medium">문법</th>
            <th class="px-2 py-1.5 font-medium">쓰임</th>
            <th class="px-2 py-1.5 font-medium">교재 예문</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="f in sources.forms"
            :key="f.key"
            class="cursor-pointer border-t border-surface-100 align-top hover:bg-surface-50"
            :title="open.has(f.key) ? '근거 접기' : '교재 근거 보기'"
            @click="toggleForm(f.key)"
          >
            <td class="whitespace-nowrap px-2 py-1.5">
              <div class="font-semibold">{{ f.form }}</div>
              <div class="mt-0.5 flex flex-wrap gap-1">
                <Tag v-if="f.level !== null" :value="`${f.level}급`" severity="secondary" class="!px-1.5 !py-0 !text-[0.7rem]" />
                <Tag v-if="outOfLevel.has(f.form)" value="안 배움" severity="warn" class="!px-1.5 !py-0 !text-[0.7rem]" />
              </div>
            </td>
            <td class="px-2 py-1.5 leading-snug">
              <template v-if="f.grounded">{{ f.usage || f.meaning || '—' }}</template>
              <template v-else-if="f.ai?.usage">
                {{ f.ai.usage }} <Tag value="AI" severity="contrast" class="!px-1 !py-0 !text-[0.65rem]" />
              </template>
              <span v-else class="text-red-600">교재 근거 없음 · 아래 AI 설명</span>
              <div v-if="f.standard_form" class="mt-0.5 text-xs text-surface-500">{{ f.standard_form }}의 관련형</div>
            </td>
            <td class="px-2 py-1.5 leading-snug text-surface-600">{{ f.example || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 2. 핵심 차이 -->
    <div v-if="differences.length">
      <div class="mb-1 text-xs font-medium text-surface-500">{{ sources.forms.length >= 2 ? '핵심 차이' : '가르칠 때' }}</div>
      <ul class="my-0 list-disc space-y-1 pl-5 text-[0.925rem] leading-relaxed">
        <li v-for="(d, k) in differences" :key="k">{{ d }}</li>
      </ul>
    </div>

    <!-- 3. 교재 근거 (문법마다 접힘) -->
    <div v-if="sourceCount" class="space-y-1">
      <div class="text-xs font-medium text-emerald-700"><i class="pi pi-book" /> 교재 근거 {{ sourceCount }}개 · 표의 줄을 눌러도 펼쳐져요</div>
      <div v-for="f in sources.forms.filter(f => f.sources.length || f.l1_notes.length)" :key="f.key" class="rounded-lg border border-surface-200 bg-white">
        <button type="button" class="flex w-full cursor-pointer items-center gap-2 border-0 bg-transparent px-2 py-1.5 text-left" @click="toggleForm(f.key)">
          <i class="pi text-xs text-surface-400" :class="open.has(f.key) ? 'pi-chevron-down' : 'pi-chevron-right'" />
          <span class="whitespace-nowrap font-semibold">{{ f.form }}</span>
          <span class="min-w-0 truncate text-xs text-surface-500">{{ f.sources.map(s => s.source).join(' · ') }}</span>
        </button>
        <div v-if="open.has(f.key)" class="space-y-2 px-2 pb-2">
          <div v-for="(s, j) in f.sources" :key="j" class="border-l-4 border-emerald-500 pl-2">
            <div class="text-xs font-medium text-emerald-700">{{ s.source }}<SourceLink :book="s.book" :pages="s.pages" /></div>
            <template v-if="s.kind === 'handbook'">
              <p v-if="s.explain_ko" class="my-1 leading-relaxed">{{ s.explain_ko }}</p>
              <p v-if="s.explain_native" :lang="s.native_lang ?? undefined" class="my-1 rounded bg-emerald-50 p-1.5 leading-relaxed">{{ s.explain_native }}</p>
              <ul v-if="s.examples?.length" class="my-1 list-none pl-0 text-surface-600">
                <li v-for="(ex, k) in s.examples.slice(0, 4)" :key="k">{{ ex }}</li>
              </ul>
            </template>
            <template v-else>
              <p class="my-1 pre-line leading-relaxed text-surface-700" :class="fullQuote.has(f.key + j) ? '' : 'line-clamp-4'">{{ s.quote }}</p>
              <button type="button" class="cursor-pointer border-0 bg-transparent p-0 text-xs text-primary-700 hover:underline" @click="toggleQuote(f.key + j)">
                {{ fullQuote.has(f.key + j) ? '접기' : '더 보기' }}
              </button>
            </template>
          </div>
          <div v-for="(n, j) in f.l1_notes" :key="'n' + j" class="border-l-4 border-amber-400 pl-2">
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
    </div>

    <!-- 4. AI 보충 -->
    <div v-if="hasAi" class="rounded-lg border border-dashed border-surface-400 p-2 text-surface-600">
      <div class="text-xs font-medium"><i class="pi pi-sparkles" /> AI 설명 · 검수 필요</div>
      <p v-if="sources.ungrounded_forms.length" class="my-1">
        {{ sources.ungrounded_forms.join(', ') }}: 색인된 교재에 설명이 없어서 AI가 설명을 만들었어요. 수업에 쓰기 전에 확인해 주세요.
      </p>
      <div v-for="f in aiForms" :key="'ai' + f.key" class="mt-2 text-surface-700">
        <div class="font-semibold">{{ f.form }}</div>
        <p class="my-1 leading-relaxed">{{ f.ai!.explanation }}</p>
        <ul v-if="f.ai!.examples.length" class="my-1 list-none pl-0">
          <li v-for="(ex, k) in f.ai!.examples" :key="k"><span class="mr-1 text-xs text-surface-500">AI 예문</span>{{ ex }}</li>
        </ul>
        <p v-if="f.ai!.caution" class="my-1 text-surface-600"><i class="pi pi-flag text-xs" /> {{ f.ai!.caution }}</p>
      </div>
      <p v-if="sources.ai_note.trim()" class="my-1">{{ sources.ai_note }}</p>
      <p v-if="sources.removed_points.length" class="my-1">근거에 없는 예문이 들어 있어 뺀 내용:</p>
      <ul v-if="sources.removed_points.length" class="my-1 pl-4">
        <li v-for="(p, k) in sources.removed_points" :key="k" class="line-through decoration-surface-400">{{ p }}</li>
      </ul>
    </div>
  </div>
</template>
