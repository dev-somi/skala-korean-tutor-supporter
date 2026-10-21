<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Tag from 'primevue/tag'
import ErrorBox from './ErrorBox.vue'
import { studentsApi } from '../api/endpoints'
import { LANG_NAMES, PERSONA_NAMES, PERSONA_TEXTBOOKS, levelName, type Persona, type StudentSummary } from '../api/types'
import { toUiError, type UiError } from '../utils'

// 학습 목적(페르소나) 탭 (기획 ADR-0016, ADR-0018).
// 학습 목적은 선생님이 고르고, 중심 교재는 학습 목적에서 정해진다.
// "수업에서 강조할 점"은 선생님 페인포인트 정리(2026-10-20)의 참고 내용이고, 아직 수업 준비에 자동으로 반영하지 않는다.

const DETAILS: Record<Persona, { who: string; focus: string[] }> = {
  structured: {
    who: '문법을 단계적으로 쌓고 싶은 학생, TOPIK 같은 시험을 준비하는 학생',
    focus: ['문법 정확성과 등급별 진도', '시험 대비는 문제 유형 연습과 전략 설명', '복습은 퀴즈형'],
  },
  conversation: {
    who: '일상 대화를 하고 싶은 학생. 드라마·K-pop 같은 콘텐츠가 동기인 학생도 여기에 넣어요',
    focus: ['활용 활동은 롤플레이와 자기 이야기 말하기', '복습은 대화 속에서 다시 쓰게 하기', '관심사(드라마 등)에 맞는 예문을 앞에'],
  },
  travel: {
    who: '여행 준비가 목적인 학생 (단기 목표가 분명한 경우가 많아요)',
    focus: ['주문, 길 묻기, 숫자·가격 같은 상황별 대화', '바로 쓸 수 있는 표현 위주', '여행 날짜에 맞춘 짧은 계획'],
  },
  business: {
    who: '한국 회사에서 일하거나 이직·취업을 준비하는 학생',
    focus: ['격식체와 높임 표현', '면접 시뮬레이션, 자기소개, 이메일', '회의·보고 상황 롤플레이'],
  },
}
const PERSONAS = Object.keys(PERSONA_NAMES) as Persona[]

const students = ref<StudentSummary[] | null>(null)
const error = ref<UiError | null>(null)

async function load() {
  error.value = null
  try {
    students.value = await studentsApi.list()
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)

const byPersona = computed(() => {
  const groups: Record<string, StudentSummary[]> = {}
  for (const s of students.value ?? []) (groups[s.persona ?? 'none'] ??= []).push(s)
  return groups
})
</script>

<template>
  <div class="space-y-4">
    <section class="guide">
      <h2>학습 목적(페르소나)이란</h2>
      <ul>
        <li>학생이 <b>왜 한국어를 배우는지</b>에 따라 4가지로 나눠요. 선생님이 학생 등록 때 고르고, 자연어 등록에서는 AI가 추천만 해요.</li>
        <li>학습 목적이 <b>중심 교재</b>를 정해요. 진도와 배우는 순서는 그 교재를 따르고, 학생별 맞춤(약점, 관심사, 모국어 설명)은 그 위에서 해요.</li>
        <li>목적은 바뀔 수 있어요 (여행을 다녀온 뒤 시험 준비 등). 학생 정보 수정에서 바꾸면 돼요.</li>
      </ul>
      <p class="warn">지금 진도 데이터가 있는 교재는 「바로 배워 바로 쓰는 세종학당 한국어 1」(2~4과)뿐이라, 어떤 목적을 골라도 진도는 이 교재를 따라요.</p>
    </section>

    <ErrorBox :error="error" @retry="load" />

    <div class="grid gap-4 md:grid-cols-2">
      <section v-for="p in PERSONAS" :key="p" class="guide">
        <div class="mb-1 flex items-center gap-2">
          <h2 class="!m-0">{{ PERSONA_NAMES[p] }}</h2>
          <Tag :value="`학생 ${byPersona[p]?.length ?? 0}명`" severity="secondary" />
        </div>
        <p class="who">{{ DETAILS[p].who }}</p>
        <dl>
          <dt>중심 교재</dt>
          <dd>{{ PERSONA_TEXTBOOKS[p] }}</dd>
          <dt>수업에서 강조할 점 <small>(참고)</small></dt>
          <dd><ul class="!pl-4"><li v-for="f in DETAILS[p].focus" :key="f">{{ f }}</li></ul></dd>
          <dt>학생</dt>
          <dd>
            <span v-if="!students" class="text-surface-400">불러오는 중…</span>
            <span v-else-if="!byPersona[p]?.length" class="text-surface-400">아직 없어요</span>
            <span v-else class="flex flex-wrap gap-1">
              <RouterLink v-for="s in byPersona[p]" :key="s.id" :to="`/students/${s.id}`" class="student">
                {{ s.name }} <small>{{ LANG_NAMES[s.nativeLanguage] }} · {{ levelName(s.standardLevel) }}</small>
              </RouterLink>
            </span>
          </dd>
        </dl>
      </section>
    </div>

    <section v-if="byPersona.none?.length" class="guide">
      <h2>학습 목적을 아직 안 고른 학생</h2>
      <span class="flex flex-wrap gap-1">
        <RouterLink v-for="s in byPersona.none" :key="s.id" :to="`/students/${s.id}`" class="student">
          {{ s.name }} <small>{{ levelName(s.standardLevel) }}</small>
        </RouterLink>
      </span>
      <p class="note">학생 화면의 [정보 수정]에서 고를 수 있어요.</p>
    </section>
  </div>
</template>

<style scoped>
.guide {
  padding: 1rem 1.25rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 0.75rem;
  background: var(--p-surface-0);
}
.guide h2 {
  margin: 0 0 0.6rem;
  font-size: 1rem;
  font-weight: 700;
}
.guide > ul {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.9rem;
  line-height: 1.6;
}
.warn {
  margin: 0.75rem 0 0;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: var(--p-orange-50);
  color: var(--p-orange-800);
  font-size: 0.85rem;
}
.who {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  color: var(--p-surface-600);
}
dl {
  margin: 0;
  display: grid;
  grid-template-columns: 7.5rem 1fr;
  gap: 0.5rem 0.75rem;
  font-size: 0.875rem;
}
dt {
  color: var(--p-surface-500);
  font-weight: 600;
}
dt small {
  font-weight: 400;
}
dd {
  margin: 0;
}
dd ul {
  margin: 0;
}
.student {
  padding: 0.2rem 0.6rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 999px;
  color: var(--p-surface-800);
  text-decoration: none;
  font-size: 0.85rem;
}
.student:hover {
  border-color: var(--p-primary-400);
}
.student small {
  color: var(--p-surface-500);
}
.note {
  margin: 0.5rem 0 0;
  font-size: 0.8rem;
  color: var(--p-surface-500);
}
</style>
