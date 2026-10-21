<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import SelectButton from 'primevue/selectbutton'
import DataTable, { type DataTablePageEvent } from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ErrorBox from '../components/ErrorBox.vue'
import StandardGuide from '../components/StandardGuide.vue'
import { standardApi } from '../api/endpoints'
import type { StandardGrammar, StandardSource, StandardVocab } from '../api/types'
import { toUiError, type UiError } from '../utils'

// 국립국어원 「국제 통용 한국어 표준 교육과정」 어휘·문법 등급 목록 찾아보기 (기획 ADR-0016).
// 문법(336개)은 한 번에 받고, 어휘(10,635개)는 서버에서 나눠 받는다.

type Tab = 'grammar' | 'vocab' | 'guide'
// 서버에서 목록을 받지 않는 탭 (고정된 설명)
const STATIC_TABS: Tab[] = ['guide']
const tab = ref<Tab>('grammar')
const tabOptions = [
  { label: '문법·표현 (336)', value: 'grammar' },
  { label: '어휘 (10,635)', value: 'vocab' },
  { label: '분류·품사 설명', value: 'guide' },
]
const level = ref<number | null>(1)
const levelOptions = [{ label: '전체', value: null }, ...[1, 2, 3, 4, 5, 6].map(n => ({ label: `${n}급`, value: n }))]
const q = ref('')
// 문법 분류: 국립국어원 원본 엑셀의 '분류' 칸 (형태 기준)
const category = ref<string | null>(null)
const categoryCounts = ref<Record<string, number>>({})
// 어휘 품사: 원본의 묶인 품사("부사/명사")를 쪼개서 센다. 품사가 둘인 단어는 양쪽에 다 세서 합이 전체보다 클 수 있다
const pos = ref<string | null>(null)
const posCounts = ref<Record<string, number>>({})
const vocabAllTotal = ref(0)

const grammar = ref<StandardGrammar[]>([])
const vocab = ref<StandardVocab[]>([])
const total = ref(0)
const first = ref(0)
const rows = 50
const source = ref<StandardSource | null>(null)
const loading = ref(false)
const error = ref<UiError | null>(null)

async function load() {
  if (STATIC_TABS.includes(tab.value)) return
  loading.value = true
  error.value = null
  try {
    if (tab.value === 'grammar') {
      const res = await standardApi.grammar({ level: level.value, category: category.value, q: q.value.trim() })
      grammar.value = res.items
      categoryCounts.value = res.categories ?? {}
      total.value = res.total
      source.value = res.source
    } else {
      const res = await standardApi.vocab({ level: level.value, pos: pos.value, q: q.value.trim(), offset: first.value, limit: rows })
      posCounts.value = res.pos_counts ?? {}
      vocabAllTotal.value = res.all_total ?? res.total
      vocab.value = res.items
      total.value = res.total
      source.value = res.source
    }
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// 조건이 바뀌면 첫 쪽부터. 검색어는 입력이 멈추면 (0.3초)
let timer: ReturnType<typeof setTimeout> | undefined
watch([tab, level, pos, category], () => {
  first.value = 0
  load()
})
watch(q, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    first.value = 0
    load()
  }, 300)
})

function onPage(e: DataTablePageEvent) {
  first.value = e.first
  load()
}
</script>

<template>
  <h1 class="mb-1 mt-0 text-xl font-bold">어휘·문법 등급 목록</h1>
  <p class="mb-4 mt-0 text-sm text-surface-500">
    국립국어원 표준 교육과정의 등급별 어휘·문법이에요. 학생 수준, 레벨테스트, 진도 리포트, 예문 수준 판정의 기준으로 써요.
  </p>

  <section class="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-surface-200 bg-white p-4">
    <SelectButton v-model="tab" :options="tabOptions" option-label="label" option-value="value" :allow-empty="false" />
    <template v-if="!STATIC_TABS.includes(tab)">
    <SelectButton v-model="level" :options="levelOptions" option-label="label" option-value="value" :allow-empty="false" />
    <span class="relative flex-1">
      <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
      <InputText v-model="q" :placeholder="tab === 'grammar' ? '문법 찾기 (예: 을, -고 싶다, 추측)' : '단어 찾기 (예: 가다, 학교)'" class="w-full !pl-9" />
    </span>
    <div v-if="tab === 'grammar'" class="flex w-full flex-wrap items-center gap-2">
      <span class="text-sm font-semibold text-surface-500">분류</span>
      <button class="chip" :class="{ on: category === null }" @click="category = null">
        전체 <small>{{ Object.values(categoryCounts).reduce((a, b) => a + b, 0) }}</small>
      </button>
      <button v-for="(n, c) in categoryCounts" :key="c" class="chip" :class="{ on: category === c }" :disabled="!n && category !== c" @click="category = category === c ? null : c">
        {{ c }} <small>{{ n }}</small>
      </button>
      <span class="text-xs text-surface-400" v-tooltip.top="'학교문법의 조사·어미 구분 + 여러 형태가 묶인 덩어리(표현). 기능(이유·추측 등)은 의미 칸에 일부만 있어요'">
        <i class="pi pi-info-circle" /> 형태 기준 (국립국어원 원본)
      </span>
    </div>
    <div v-else class="flex w-full flex-wrap items-center gap-2">
      <span class="text-sm font-semibold text-surface-500">품사</span>
      <button class="chip" :class="{ on: pos === null }" @click="pos = null">전체 <small>{{ vocabAllTotal.toLocaleString() }}</small></button>
      <button v-for="(n, p) in posCounts" :key="p" class="chip" :class="{ on: pos === p }" :disabled="!n && pos !== p" @click="pos = pos === p ? null : p">
        {{ p }} <small>{{ n.toLocaleString() }}</small>
      </button>
      <span class="text-xs text-surface-400" v-tooltip.top="'원본에 \'부사/명사\'처럼 품사가 둘인 단어는 양쪽에 다 세요. 그래서 합이 전체보다 클 수 있어요'">
        <i class="pi pi-info-circle" /> 품사가 둘인 단어는 양쪽에 셈
      </span>
    </div>
    </template>
  </section>

  <ErrorBox :error="error" @retry="load" />

  <StandardGuide v-if="tab === 'guide'" />
  <section v-else class="rounded-xl border border-surface-200 bg-white p-2">
    <DataTable v-if="tab === 'grammar'" :value="grammar" :loading="loading" size="small" data-key="id" striped-rows scrollable scroll-height="65vh">
      <template #header><span class="text-sm text-surface-500">{{ total }}개</span></template>
      <template #empty>찾는 문법이 없어요.</template>
      <Column header="등급" style="width: 4.5rem"><template #body="{ data }">{{ data.level }}급</template></Column>
      <Column field="category" header="분류" style="width: 6rem" />
      <Column header="대표형">
        <template #body="{ data }">
          <b>{{ data.form }}</b><sup v-if="data.has_homonyms && data.homonym" class="cursor-help text-surface-400" v-tooltip.top="`같은 글자가 목록에 여러 번 있어요. 동음이의어 ${data.homonym}번 (뜻은 옆 칸을 보세요)`">{{ data.homonym }}</sup>
        </template>
      </Column>
      <Column header="관련형"><template #body="{ data }">{{ data.related.join(', ') }}</template></Column>
      <Column field="meaning" header="의미" />
      <Column header="교재">
        <template #body="{ data }">
          <Tag v-for="t in data.textbook" :key="t.item_id" :value="`한국어 1 · ${t.unit_no}과`" severity="info" class="mr-1 !text-xs" v-tooltip.top="`${t.book} ${t.item_id}`" />
        </template>
      </Column>
    </DataTable>

    <DataTable
      v-else
      :value="vocab"
      :loading="loading"
      lazy
      paginator
      :rows="rows"
      :first="first"
      :total-records="total"
      size="small"
      data-key="id"
      striped-rows
      @page="onPage"
    >
      <template #header><span class="text-sm text-surface-500">{{ total.toLocaleString() }}개</span></template>
      <template #empty>찾는 단어가 없어요.</template>
      <Column header="등급" style="width: 4.5rem"><template #body="{ data }">{{ data.level }}급</template></Column>
      <Column header="단어">
        <template #body="{ data }">
          <b>{{ data.word }}</b><sup v-if="data.has_homonyms && data.homonym" class="cursor-help text-surface-400" v-tooltip.top="`같은 글자가 목록에 여러 번 있어요. 동음이의어 ${data.homonym}번 (뜻은 옆 칸을 보세요)`">{{ data.homonym }}</sup>
        </template>
      </Column>
      <Column field="pos" header="품사" style="width: 8rem" />
      <Column field="guide" header="길잡이말" />
    </DataTable>
  </section>

  <p v-if="source && !STATIC_TABS.includes(tab)" class="mt-3 text-xs text-surface-500">
    출처: {{ source.publisher }}, <a :href="source.url" target="_blank" rel="noopener">{{ source.title }}</a> · {{ source.license }}
  </p>
</template>

<style scoped>
.chip {
  padding: 0.25rem 0.7rem;
  border: 1px solid var(--p-surface-300);
  border-radius: 999px;
  background: var(--p-surface-0);
  font-size: 0.85rem;
  cursor: pointer;
}
.chip small {
  margin-left: 0.2rem;
  color: var(--p-surface-500);
}
.chip.on {
  border-color: var(--p-primary-500);
  background: var(--p-primary-50);
  color: var(--p-primary-700);
}
.chip:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
