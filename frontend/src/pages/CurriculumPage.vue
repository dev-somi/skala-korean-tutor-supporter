<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SelectButton from 'primevue/selectbutton'
import CurriculumGuide from '../components/CurriculumGuide.vue'
import PersonaGuide from '../components/PersonaGuide.vue'

// 커리큘럼과 페르소나(학습 목적)를 한 메뉴의 탭으로 본다. 탭은 주소(?tab=persona)에 남겨서 새로고침해도 유지한다.

const ROADMAP = 'https://nuri.iksi.or.kr/front/page/siteguide/learning/roadmap/main.do'

type Tab = 'curriculum' | 'persona'
const tabOptions = [
  { label: '커리큘럼', value: 'curriculum' },
  { label: '페르소나 (학습 목적)', value: 'persona' },
]
const route = useRoute()
const router = useRouter()
const tab = computed<Tab>({
  get: () => (route.query.tab === 'persona' ? 'persona' : 'curriculum'),
  set: v => router.replace({ query: { ...route.query, tab: v === 'curriculum' ? undefined : v } }),
})
</script>

<template>
  <h1 class="mb-1 mt-0 text-xl font-bold">커리큘럼 · 페르소나</h1>
  <p class="mb-4 mt-0 text-sm text-surface-500">
    세종학당 교육과정과 학습 목적(페르소나)별 중심 교재를 봐요. 등급별 어휘·문법은 상단 [어휘·문법]에 있어요.
  </p>
  <a
    :href="ROADMAP"
    target="_blank"
    rel="noopener"
    class="mb-4 inline-flex items-center gap-2 rounded-lg border border-primary-200 bg-primary-50 px-3 py-1.5 text-sm font-semibold text-primary-700 no-underline transition hover:bg-primary-100"
  >
    <i class="pi pi-map" />
    누리-세종학당 학습 로드맵 보기
    <i class="pi pi-external-link text-xs" />
  </a>
  <div class="mb-4">
    <SelectButton v-model="tab" :options="tabOptions" option-label="label" option-value="value" :allow-empty="false" />
  </div>
  <CurriculumGuide v-if="tab === 'curriculum'" />
  <PersonaGuide v-else />
</template>
