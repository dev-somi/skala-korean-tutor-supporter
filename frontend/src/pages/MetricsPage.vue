<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ErrorBox from '../components/ErrorBox.vue'
import { dashboardApi } from '../api/endpoints'
import { CATEGORY_NAMES, type KindSummary, type QualityMetrics, type Rate, type TimeMetrics } from '../api/types'
import { formatDateTime, toUiError, type UiError } from '../utils'

const toast = useToast()
const metrics = ref<TimeMetrics | null>(null)
const quality = ref<QualityMetrics | null>(null)
const error = ref<UiError | null>(null)
const forms = ref<Record<'prep' | 'post', { minutes: number | null; note: string; isEstimate: boolean }>>({
  prep: { minutes: null, note: '', isEstimate: false },
  post: { minutes: null, note: '', isEstimate: false },
})
const KIND_NAMES = { prep: '수업 준비', post: '수업 후 정리' } as const
const TARGET = { prep: '기준 대비 50% 이상 감소', post: '5분 이내' } as const

async function load() {
  error.value = null
  try {
    ;[metrics.value, quality.value] = await Promise.all([dashboardApi.metrics(), dashboardApi.quality()])
    for (const kind of ['prep', 'post'] as const) {
      const m = metrics.value[kind]
      forms.value[kind] = { minutes: m.baselineMinutes, note: m.baselineNote ?? '', isEstimate: m.baselineIsEstimate }
    }
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)

async function saveBaseline(kind: 'prep' | 'post') {
  const f = forms.value[kind]
  if (!f.minutes) return
  try {
    await dashboardApi.saveBaseline(kind, f.minutes, f.note, f.isEstimate)
    toast.add({ severity: 'success', summary: '기준 시간을 저장했어요', life: 2000 })
    await load()
  } catch (e) {
    error.value = toUiError(e)
  }
}

const POST_FIELDS = { covered_item_ids: '다룬 항목', strengths: '잘한 점', errors: '오류·교정', weakness_changes: '약점 변경', homework: '숙제' } as const
const rateText = (r: Rate) => (r.percent == null ? '-' : `${r.percent}%`)

/** 막대 길이: 기준 시간과 평균 중 큰 값을 100%로 */
function bar(m: KindSummary, value: number | null) {
  const max = Math.max(m.baselineMinutes ?? 0, m.avgTotalMinutes ?? 0, 1)
  return `${Math.round(((value ?? 0) / max) * 100)}%`
}
</script>

<template>
  <h1 class="mb-1 mt-0 text-xl font-bold">지표</h1>
  <p class="mb-4 mt-0 text-sm text-surface-500">주 지표는 <b>AI 초안을 고치지 않고 그대로 승인한 비율</b>이에요. 시간은 보조 지표예요 (기획 ADR-0020).</p>
  <ErrorBox :error="error" @retry="load" />

  <div v-if="quality" class="mb-6 grid gap-4 lg:grid-cols-2">
    <section class="rounded-xl border border-surface-200 bg-white p-4">
      <h2 class="mb-1 mt-0 text-base font-bold">수업안 — 첫 검토에서 바로 승인</h2>
      <p class="mt-0 text-xs text-surface-500">수업·범주마다 첫 결정이 '승인'이면 초안을 그대로 쓴 것으로 셉니다.</p>
      <div class="mb-3 text-3xl font-bold text-primary-700">{{ rateText(quality.prep.all) }}</div>
      <div class="text-xs text-surface-500 mb-2">{{ quality.prep.all.kept }} / {{ quality.prep.all.total }}개 범주</div>
      <ul class="m-0 list-none space-y-1 p-0 text-sm">
        <li v-for="c in (['review', 'new_vocab', 'new_grammar', 'homework'] as const)" :key="c" class="flex justify-between">
          <span>{{ CATEGORY_NAMES[c] }}</span><span>{{ rateText(quality.prep[c]) }} <small class="text-surface-400">({{ quality.prep[c].kept }}/{{ quality.prep[c].total }})</small></span>
        </li>
      </ul>
    </section>
    <section class="rounded-xl border border-surface-200 bg-white p-4">
      <h2 class="mb-1 mt-0 text-base font-bold">수업 후 기록 — 초안 항목이 그대로 남은 비율</h2>
      <p class="mt-0 text-xs text-surface-500">고치거나 체크를 풀어 뺀 항목은 '그대로'로 세지 않습니다.</p>
      <div class="mb-3 text-3xl font-bold text-primary-700">{{ rateText(quality.post.all) }}</div>
      <div class="text-xs text-surface-500 mb-2">{{ quality.post.all.kept }} / {{ quality.post.all.total }}개 항목</div>
      <ul class="m-0 list-none space-y-1 p-0 text-sm">
        <li v-for="(name, f) in POST_FIELDS" :key="f" class="flex justify-between">
          <span>{{ name }}</span><span>{{ rateText(quality.post[f]) }} <small class="text-surface-400">({{ quality.post[f].kept }}/{{ quality.post[f].total }})</small></span>
        </li>
      </ul>
    </section>
  </div>

  <h2 class="mb-3 mt-0 text-base font-bold text-surface-600">보조 지표: 시간</h2>
  <div v-if="metrics" class="grid gap-4 lg:grid-cols-2">
    <section v-for="kind in (['prep', 'post'] as const)" :key="kind" class="rounded-xl border border-surface-200 bg-white p-4">
      <h2 class="mb-1 mt-0 text-base font-bold">{{ KIND_NAMES[kind] }}</h2>
      <p class="mt-0 text-xs text-surface-500">
        {{ kind === 'prep' ? '[준비 시작] ~ 모든 범주 승인' : '메모 쓰기 시작 ~ 기록 승인' }} · 목표: {{ TARGET[kind] }}
      </p>

      <div class="mb-4 space-y-2 text-sm">
        <div>
          <div class="flex justify-between"><span>AI 사용 (평균 {{ metrics[kind].sessions }}회)</span><b>{{ metrics[kind].avgTotalMinutes ?? '-' }}분</b></div>
          <div class="h-3 overflow-hidden rounded bg-surface-100">
            <div class="flex h-full" :style="{ width: bar(metrics[kind], metrics[kind].avgTotalMinutes) }">
              <div class="h-full bg-sky-400" :style="{ flex: metrics[kind].avgAiWaitMinutes ?? 0 }" v-tooltip.top="'AI 대기 ' + (metrics[kind].avgAiWaitMinutes ?? 0) + '분'" />
              <div class="h-full bg-primary-500" :style="{ flex: metrics[kind].avgTeacherMinutes ?? 0 }" v-tooltip.top="'선생님 작업 ' + (metrics[kind].avgTeacherMinutes ?? 0) + '분'" />
            </div>
          </div>
          <div class="mt-1 text-xs text-surface-500">
            <span class="mr-3"><i class="pi pi-circle-fill text-[0.5rem] text-sky-400" /> AI 대기 {{ metrics[kind].avgAiWaitMinutes ?? '-' }}분</span>
            <span><i class="pi pi-circle-fill text-[0.5rem] text-primary-500" /> 선생님 작업 {{ metrics[kind].avgTeacherMinutes ?? '-' }}분</span>
          </div>
        </div>
        <div>
          <div class="flex justify-between"><span>AI 없이 (기준{{ metrics[kind].baselineIsEstimate ? ', 추정' : '' }})</span><b>{{ metrics[kind].baselineMinutes ?? '-' }}분</b></div>
          <div class="h-3 overflow-hidden rounded bg-surface-100"><div class="h-full bg-surface-400" :style="{ width: bar(metrics[kind], metrics[kind].baselineMinutes) }" /></div>
        </div>
        <div v-if="metrics[kind].reductionPercent !== null" class="text-lg font-bold" :class="metrics[kind].reductionPercent! >= 0 ? 'text-primary-700' : 'text-red-600'">
          {{ metrics[kind].reductionPercent! >= 0 ? metrics[kind].reductionPercent + '% 감소' : -metrics[kind].reductionPercent! + '% 증가' }}
        </div>
      </div>

      <form class="mb-4 flex flex-wrap items-end gap-2 rounded-lg bg-surface-50 p-3" @submit.prevent="saveBaseline(kind)">
        <label class="flex flex-col gap-1 text-xs font-semibold">기준 시간 (분)<InputNumber v-model="forms[kind].minutes" :min="1" :max="600" input-class="w-20" /></label>
        <label class="flex min-w-40 flex-1 flex-col gap-1 text-xs font-semibold">메모<InputText v-model="forms[kind].note" placeholder="예: 3과 직접 준비해 봄" /></label>
        <label class="flex items-center gap-1 pb-2 text-xs"><Checkbox v-model="forms[kind].isEstimate" binary /> 추정치</label>
        <Button type="submit" label="저장" size="small" :disabled="!forms[kind].minutes" />
      </form>

      <DataTable :value="metrics[kind].recent" size="small" class="text-sm">
        <template #empty>아직 기록이 없어요.</template>
        <Column header="학생"><template #body="{ data }">{{ data.studentName }}</template></Column>
        <Column header="시작"><template #body="{ data }">{{ formatDateTime(data.startedAt) }}</template></Column>
        <Column field="totalMinutes" header="전체(분)" />
        <Column field="aiWaitMinutes" header="AI(분)" />
        <Column field="teacherMinutes" header="선생님(분)" />
      </DataTable>
    </section>
  </div>
</template>
