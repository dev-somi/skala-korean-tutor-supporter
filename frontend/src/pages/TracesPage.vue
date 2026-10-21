<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ErrorBox from '../components/ErrorBox.vue'
import { tracesApi } from '../api/endpoints'
import type { TraceDetail, TraceList, TraceNode, TraceRow, TraceRunType, TraceStatus } from '../api/types'
import { formatDateTime, toUiError, type UiError } from '../utils'

// LangSmith에 쌓인 ai-server 실행 기록을 보여 준다 (기술 ADR-0028).
// 목록에서 하나를 고르면 그래프 노드 → 함수 → LLM 호출 트리와 시간 막대를 그린다.

const NAME_OPTIONS = [
  { label: '전체', value: null },
  { label: '수업 준비', value: 'lesson_prep' },
  { label: '수업 후 기록', value: 'post_lesson' },
  { label: '학생 등록', value: 'student_intake' },
  { label: '문법 질문', value: 'grammar_qa' },
]
const RUN_TYPE: Record<string, { name: string; bar: string }> = {
  chain: { name: '단계', bar: 'bg-surface-400' },
  llm: { name: 'LLM', bar: 'bg-sky-500' },
  retriever: { name: '검색', bar: 'bg-emerald-500' },
  tool: { name: '코드 점검', bar: 'bg-amber-500' },
}
const STATUS: Record<TraceStatus, { label: string; severity: 'success' | 'danger' | 'info' }> = {
  success: { label: '성공', severity: 'success' },
  error: { label: '에러', severity: 'danger' },
  running: { label: '실행 중', severity: 'info' },
}

const list = ref<TraceList | null>(null)
const name = ref<string | null>(null)
const errorsOnly = ref(false)
const loading = ref(false)
const error = ref<UiError | null>(null)

const selected = ref<TraceRow | null>(null)
const detail = ref<TraceDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref<UiError | null>(null)
const openNode = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    list.value = await tracesApi.list({ limit: 50, name: name.value, errorsOnly: errorsOnly.value })
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function select(row: TraceRow) {
  selected.value = row
  detail.value = null
  detailError.value = null
  openNode.value = null
  detailLoading.value = true
  try {
    detail.value = await tracesApi.get(row.trace_id)
  } catch (e) {
    detailError.value = toUiError(e)
  } finally {
    detailLoading.value = false
  }
}

/** 트리를 깊이와 함께 한 줄씩 펼친다 (들여쓰기 + 시간 막대) */
const rows = computed(() => {
  const d = detail.value
  if (!d || !d.enabled) return []
  const out: { node: TraceNode; depth: number }[] = []
  const walk = (node: TraceNode, depth: number) => {
    out.push({ node, depth })
    node.children.forEach(c => walk(c, depth + 1))
  }
  walk(d.root, 0)
  return out
})
const total = computed(() => {
  const d = detail.value
  if (!d || !d.enabled) return 1
  return Math.max(d.total_latency_ms ?? 0, ...rows.value.map(r => r.node.start_offset_ms + (r.node.latency_ms ?? 0)), 1)
})
const barStyle = (n: TraceNode) => ({
  left: `${(n.start_offset_ms / total.value) * 100}%`,
  width: `${Math.max(((n.latency_ms ?? total.value - n.start_offset_ms) / total.value) * 100, 0.5)}%`,
})
const barClass = (n: TraceNode) => (n.status === 'error' ? 'bg-red-500' : (RUN_TYPE[n.run_type]?.bar ?? 'bg-surface-300'))
const typeName = (t: TraceRunType) => RUN_TYPE[t]?.name ?? t

function seconds(ms: number | null) {
  if (ms == null) return '-'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}초`
}
const cost = (v: number | null) => (v == null ? '-' : `$${v.toFixed(4)}`)
const tokens = (v: number) => (v ? v.toLocaleString() : '-')
</script>

<template>
  <h1 class="mb-1 mt-0 text-xl font-bold">AI 추적</h1>
  <p class="mb-4 mt-0 text-sm text-surface-500">
    ai-server가 LLM과 함수를 어떤 순서로, 얼마나 걸려서 불렀는지 LangSmith 기록으로 보여 줘요. 채팅 라우터(Spring AI)는 아직 기록하지 않아요.
  </p>
  <ErrorBox :error="error" @retry="load" />

  <section v-if="list && !list.enabled" class="rounded-xl border border-surface-200 bg-white p-4 text-sm">
    <h2 class="mb-2 mt-0 text-base font-bold">LangSmith 추적이 꺼져 있어요</h2>
    <p class="mt-0">루트의 <code>.env</code>에 아래 값을 넣고 <code>bash scripts/dev.sh</code>를 다시 실행하세요.</p>
    <pre class="m-0 overflow-x-auto rounded bg-surface-50 p-3 text-xs">LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=korean-tutor-dev</pre>
  </section>

  <template v-else-if="list && list.enabled">
    <div class="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div class="rounded-xl border border-surface-200 bg-white p-3">
        <div class="text-xs text-surface-500">실행 수</div>
        <div class="text-2xl font-bold">{{ list.summary.count }}</div>
      </div>
      <div class="rounded-xl border border-surface-200 bg-white p-3">
        <div class="text-xs text-surface-500">에러</div>
        <div class="text-2xl font-bold" :class="list.summary.errors ? 'text-red-600' : ''">{{ list.summary.errors }}</div>
      </div>
      <div class="rounded-xl border border-surface-200 bg-white p-3">
        <div class="text-xs text-surface-500">평균 시간</div>
        <div class="text-2xl font-bold">{{ seconds(list.summary.avg_latency_ms) }}</div>
      </div>
      <div class="rounded-xl border border-surface-200 bg-white p-3">
        <div class="text-xs text-surface-500">토큰 · 비용</div>
        <div class="text-2xl font-bold">{{ tokens(list.summary.total_tokens) }}</div>
        <div class="text-xs text-surface-500">{{ cost(list.summary.total_cost) }}</div>
      </div>
    </div>

    <div class="mb-3 flex flex-wrap items-center gap-3">
      <Select v-model="name" :options="NAME_OPTIONS" option-label="label" option-value="value" size="small" class="w-40" @change="load" />
      <label class="flex items-center gap-1 text-sm"><Checkbox v-model="errorsOnly" binary @change="load" /> 에러만</label>
      <Button label="새로고침" icon="pi pi-refresh" size="small" outlined :loading="loading" @click="load" />
      <span class="ml-auto text-xs text-surface-500">LangSmith 프로젝트: {{ list.project }}</span>
    </div>

    <DataTable
      :value="list.runs"
      size="small"
      class="mb-6 text-sm"
      selection-mode="single"
      :selection="selected"
      data-key="id"
      row-hover
      @row-click="select($event.data)"
    >
      <template #empty>아직 기록이 없어요. 수업 준비나 문법 질문을 한 번 실행해 보세요.</template>
      <Column header="시각"><template #body="{ data }">{{ formatDateTime(data.start_time) }}</template></Column>
      <Column header="실행"><template #body="{ data }">{{ data.label }}</template></Column>
      <Column header="상태"><template #body="{ data }"><Tag :value="STATUS[data.status as TraceStatus].label" :severity="STATUS[data.status as TraceStatus].severity" /></template></Column>
      <Column header="시간"><template #body="{ data }">{{ seconds(data.latency_ms) }}</template></Column>
      <Column header="토큰"><template #body="{ data }">{{ tokens(data.total_tokens) }}</template></Column>
      <Column header="비용"><template #body="{ data }">{{ cost(data.total_cost) }}</template></Column>
      <Column header="">
        <template #body="{ data }">
          <a v-if="data.url" :href="data.url" target="_blank" rel="noopener" class="text-xs" @click.stop>LangSmith ↗</a>
        </template>
      </Column>
    </DataTable>
  </template>

  <section v-if="selected" class="rounded-xl border border-surface-200 bg-white p-4">
    <div class="mb-3 flex flex-wrap items-baseline gap-3">
      <h2 class="m-0 text-base font-bold">{{ selected.label }} 실행 흐름</h2>
      <span class="text-xs text-surface-500">{{ formatDateTime(selected.start_time) }} · {{ seconds(selected.latency_ms) }}</span>
      <span class="ml-auto flex flex-wrap gap-3 text-xs text-surface-500">
        <span v-for="(t, key) in RUN_TYPE" :key="key"><i class="pi pi-circle-fill text-[0.5rem]" :class="t.bar.replace('bg-', 'text-')" /> {{ t.name }}</span>
        <span><i class="pi pi-circle-fill text-[0.5rem] text-red-500" /> 에러</span>
      </span>
    </div>
    <ErrorBox :error="detailError" @retry="select(selected)" />
    <p v-if="detailLoading" class="text-sm text-surface-500">불러오는 중…</p>

    <div v-for="{ node, depth } in rows" :key="node.id" class="border-b border-surface-100 last:border-0">
      <button
        type="button"
        class="grid w-full cursor-pointer grid-cols-[minmax(0,2fr)_minmax(0,3fr)_4rem] items-center gap-3 border-0 bg-transparent px-1 py-1.5 text-left text-sm hover:bg-surface-50"
        @click="openNode = openNode === node.id ? null : node.id"
      >
        <span class="flex min-w-0 items-center gap-2" :style="{ paddingLeft: `${depth * 1.1}rem` }">
          <i class="pi text-[0.6rem] text-surface-400" :class="openNode === node.id ? 'pi-chevron-down' : 'pi-chevron-right'" />
          <span class="truncate" :class="node.status === 'error' ? 'text-red-600' : ''">{{ node.label }}</span>
          <span class="shrink-0 rounded bg-surface-100 px-1.5 text-[0.7rem] text-surface-600">{{ typeName(node.run_type) }}</span>
        </span>
        <span class="relative h-3 rounded bg-surface-50">
          <span class="absolute top-0 h-full rounded" :class="barClass(node)" :style="barStyle(node)" />
        </span>
        <span class="text-right text-xs text-surface-500">{{ seconds(node.latency_ms) }}</span>
      </button>
      <div v-if="openNode === node.id" class="mb-2 space-y-2 rounded-lg bg-surface-50 p-3 text-xs">
        <div class="flex flex-wrap gap-4 text-surface-600">
          <span>이름: <code>{{ node.name }}</code></span>
          <span v-if="node.model">모델: {{ node.model }}</span>
          <span v-if="node.total_tokens">토큰: {{ tokens(node.total_tokens) }}</span>
          <span>시작: +{{ seconds(node.start_offset_ms) }}</span>
        </div>
        <pre v-if="node.error" class="m-0 whitespace-pre-wrap text-red-600">{{ node.error }}</pre>
        <div v-if="node.inputs"><b>입력</b><pre class="m-0 max-h-60 overflow-auto whitespace-pre-wrap">{{ node.inputs }}</pre></div>
        <div v-if="node.outputs"><b>출력</b><pre class="m-0 max-h-60 overflow-auto whitespace-pre-wrap">{{ node.outputs }}</pre></div>
      </div>
    </div>
  </section>
</template>
