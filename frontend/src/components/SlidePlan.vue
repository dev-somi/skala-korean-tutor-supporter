<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { SLIDE_LAYOUT_NAMES, type CultureNote, type SlidePlan } from '../api/types'
import SourceLink from './SourceLink.vue'

// 15장 슬라이드 구성안 (기획 ADR-0032). 학생 화면 문구와 교사 노트를 한 줄씩 펼쳐 본다.
const props = defineProps<{
  plan: SlidePlan
  culture?: CultureNote[]
}>()
const toast = useToast()

const open = ref<number | null>(null)
const toggle = (no: number) => (open.value = open.value === no ? null : no)

// 선생님이 고른 문화 후보 (기본은 1순위). 화면에서만 바꾸고 저장하지 않는다 (기술 ADR-0023)
const picked = ref(0)
const cultureNote = () => (props.culture?.length ? props.culture[picked.value] : null)

const failedChecks = () => props.plan.checks.filter(c => !c.passed)
const totalMinutes = () => props.plan.slides.reduce((a, s) => a + s.minutes, 0)

/** 선생님이 자기 자료에 붙여 넣을 수 있게 구성안 전체를 글로 만든다. 순서는 기준 문서 §11: 목표 → 슬라이드 표 → 교사 노트 → 숙제 */
function asText(): string {
  const p = props.plan
  const lines: string[] = ['[수업 목표]', p.lesson_goal, '', '[최종 미션]', p.final_mission, '', '[슬라이드 구성]']
  for (const s of p.slides) {
    lines.push(`${s.no}. ${s.name} (${s.minutes}분) — ${s.activity}`)
    for (const text of s.student_screen) lines.push(`   · ${text}`)
  }
  lines.push('', '[교사 노트]')
  for (const s of p.slides) {
    const n = s.note
    lines.push(`${s.no}. ${s.name}`, `[소요 시간] ${s.minutes}분`, `[목표] ${n.goal}`, `[진행] ${n.procedure}`)
    if (n.qa.length) lines.push('[기본 질문 / 예상 답변]', ...n.qa.map(q => `질문: ${q.question}\n답변 예: ${q.answer}`))
    lines.push(`[어려워하면] ${n.if_struggle}`, `[잘하면] ${n.if_good}`)
    if (n.source) lines.push(`[출처] ${n.source}`)
    if (s.needs_check.length) lines.push(`[확인 필요] ${s.needs_check.join(' / ')}`)
    lines.push('')
  }
  const h = p.homework
  lines.push('[숙제]', `쪽수: ${h.pages || '확인 필요'}`, `문항: ${h.items || '확인 필요'}`, `방법: ${h.how}`, `완료 예시: ${h.example}`)
  if (p.needs_check.length) lines.push('', '[확인 필요]', ...p.needs_check.map(t => `- ${t}`))
  return lines.join('\n')
}

async function copy() {
  await navigator.clipboard.writeText(asText())
  toast.add({ severity: 'success', summary: '구성안을 복사했어요', life: 2000 })
}
</script>

<template>
  <section class="mb-4 rounded-xl border border-surface-200 bg-white p-4">
    <div class="mb-3 flex items-center gap-2">
      <h3 class="m-0 text-base font-bold"><i class="pi pi-list mr-1 text-primary-600" />수업 구성안 ({{ plan.slides.length }}장 · {{ totalMinutes() }}분)</h3>
      <div class="flex-1" />
      <Button label="글로 복사" icon="pi pi-copy" size="small" severity="secondary" outlined @click="copy" />
    </div>

    <div class="mb-3 rounded-lg bg-primary-50 p-3 text-sm">
      <div><span class="font-semibold text-primary-800">수업 목표</span> {{ plan.lesson_goal }}</div>
      <div class="mt-1"><span class="font-semibold text-primary-800">최종 미션</span> {{ plan.final_mission }}</div>
    </div>

    <ul v-if="failedChecks().length" class="mb-3 space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3 pl-7 text-sm text-amber-900">
      <li v-for="c in failedChecks()" :key="c.name"><b>{{ c.name }}</b> — {{ c.reason }}</li>
    </ul>

    <ol class="m-0 list-none space-y-2 p-0">
      <li v-for="s in plan.slides" :key="s.no" class="rounded-lg border border-surface-100">
        <button type="button" class="flex w-full items-start gap-3 p-3 text-left" @click="toggle(s.no)">
          <div class="flex w-12 shrink-0 flex-col items-center">
            <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-800">{{ s.no }}</span>
            <span class="mt-1 text-xs text-surface-500">{{ s.minutes }}분</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-semibold">{{ s.name }}</span>
              <Tag :value="SLIDE_LAYOUT_NAMES[s.layout] ?? s.layout" severity="secondary" />
              <Tag v-if="s.needs_check.length" value="확인 필요" severity="warn" />
            </div>
            <p class="m-0 mt-0.5 text-sm text-surface-500">{{ s.activity }}</p>
            <ul v-if="s.student_screen.length" class="m-0 mt-2 space-y-0.5 pl-5 text-sm">
              <li v-for="(text, j) in s.student_screen" :key="j">{{ text }}</li>
            </ul>
            <p v-else class="m-0 mt-2 text-sm text-surface-400">학생 화면은 수업 중에 채워요.</p>
          </div>
          <i :class="open === s.no ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="mt-1 text-xs text-surface-400" />
        </button>

        <dl v-if="open === s.no" class="m-0 grid gap-x-3 gap-y-1 border-t border-surface-100 bg-surface-50 p-3 text-sm sm:grid-cols-[7rem_1fr]">
          <dt class="font-semibold text-surface-500">소요 시간</dt><dd class="m-0">{{ s.minutes }}분</dd>
          <dt class="font-semibold text-surface-500">목표</dt><dd class="m-0">{{ s.note.goal }}</dd>
          <dt class="font-semibold text-surface-500">진행</dt><dd class="m-0 whitespace-pre-line">{{ s.note.procedure }}</dd>
          <template v-if="s.note.qa.length">
            <dt class="font-semibold text-surface-500">질문 / 예상 답변</dt>
            <dd class="m-0">
              <div v-for="(q, j) in s.note.qa" :key="j">질문: {{ q.question }} <span class="text-surface-500">→ {{ q.answer }}</span></div>
            </dd>
          </template>
          <dt class="font-semibold text-surface-500">어려워하면</dt><dd class="m-0">{{ s.note.if_struggle }}</dd>
          <dt class="font-semibold text-surface-500">잘하면</dt><dd class="m-0">{{ s.note.if_good }}</dd>
          <template v-if="s.note.source">
            <dt class="font-semibold text-surface-500">출처</dt><dd class="m-0">{{ s.note.source }}</dd>
          </template>
          <template v-if="s.needs_check.length">
            <dt class="font-semibold text-amber-700">확인 필요</dt>
            <dd class="m-0 text-amber-800">{{ s.needs_check.join(' / ') }}</dd>
          </template>
        </dl>
      </li>
    </ol>

    <div class="mt-3 rounded-lg border border-surface-200 p-3 text-sm">
      <div class="mb-1 font-semibold"><i class="pi pi-book mr-1 text-primary-600" />숙제</div>
      <div>쪽수 {{ plan.homework.pages || '확인 필요' }} · 문항 {{ plan.homework.items || '확인 필요' }}</div>
      <div class="text-surface-600">{{ plan.homework.how }}</div>
      <div v-if="plan.homework.example" class="text-surface-500">완료 예시: {{ plan.homework.example }}</div>
    </div>
    <ul v-if="plan.needs_check.length" class="mb-0 mt-3 space-y-1 pl-5 text-sm text-amber-800">
      <li v-for="(t, i) in plan.needs_check" :key="i">{{ t }}</li>
    </ul>

    <div v-if="culture" class="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
      <div class="mb-1 flex flex-wrap items-center gap-2">
        <span class="font-semibold text-amber-800"><i class="pi pi-globe mr-1" />문화 포인트</span>
        <template v-if="culture.length > 1">
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
  </section>
</template>
