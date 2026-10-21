<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import ErrorBox from '../components/ErrorBox.vue'
import LevelTestResultCard from '../components/LevelTestResultCard.vue'
import { levelTestApi } from '../api/endpoints'
import { levelName, type LevelTest, type LevelTestResult, type LevelTestScore } from '../api/types'
import { toUiError, type UiError } from '../utils'
import { SCREEN_LANG_NAMES, openScreenChannel, type ScreenItem, type ScreenLang, type ScreenMessage } from '../levelTestScreen'

// 체험수업 레벨테스트 (기획 ADR-0018, ADR-0021). 판정 규칙은 ai-server에 있고, 화면은 맞음/틀림만 모아 보낸다.
// 학생 화면(/level-test/screen) 창을 따로 열어 화상수업에서 공유한다. 이 화면에서 고른 문항만 그 창에 보인다.
// [결과 저장]하면 추천 등급과 함께 남고, 학생 카드에는 선생님이 결과 카드에서 확인해야 반영된다.

const toast = useToast()

const test = ref<LevelTest | null>(null)
const answers = ref<Record<string, boolean>>({})
const result = ref<LevelTestScore | null>(null)
const note = ref('')
const error = ref<UiError | null>(null)
const showHowTo = ref(true)
const saving = ref(false)
const saved = ref<LevelTestResult | null>(null)

async function load() {
  error.value = null
  try {
    test.value = await levelTestApi.get()
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)

// ── 학생 화면 ──
const shown = ref<string | null>(null) // 학생 화면에 보이는 문항 ID
const screenLang = ref<ScreenLang>('en')
const langOptions = (Object.keys(SCREEN_LANG_NAMES) as ScreenLang[]).map(value => ({ value, label: SCREEN_LANG_NAMES[value] }))

/** 문항 순서대로: 한글 읽기 → 1급 문법·어휘 → 2급 … 학생 화면에 보낼 글만 담는다 */
const screenItems = computed(() => {
  const items = new Map<string, ScreenItem>()
  if (!test.value) return items
  const words = test.value.hangul.words
  words.forEach((w, i) => items.set(w.id, { kind: 'hangul', text: w.word, level: null, index: i + 1, total: words.length }))
  for (const s of test.value.levels) {
    const total = s.grammar.length + s.vocab.length
    s.grammar.forEach((g, i) => items.set(g.id, { kind: 'grammar', text: g.question, level: s.level, index: i + 1, total }))
    s.vocab.forEach((v, i) => items.set(v.id, { kind: 'vocab', text: v.word, level: s.level, index: s.grammar.length + i + 1, total }))
  }
  return items
})

const channel = openScreenChannel()
const send = (msg: ScreenMessage) => channel.postMessage(msg)
const sendCurrent = () =>
  saved.value
    ? send({ type: 'done', lang: screenLang.value })
    : send({ type: 'show', lang: screenLang.value, item: shown.value ? screenItems.value.get(shown.value) ?? null : null })
channel.onmessage = (e: MessageEvent<ScreenMessage>) => {
  if (e.data.type === 'hello') sendCurrent() // 학생 창을 새로 열거나 새로고침했을 때
}
onBeforeUnmount(() => channel.close())
watch([shown, screenLang, saved], sendCurrent)

function openScreen() {
  window.open('/level-test/screen', 'level-test-screen', 'popup,width=1100,height=720')
}

/** 이 문항을 학생 화면에 보여 준다. 다시 누르면 대기 화면으로 */
function show(id: string) {
  shown.value = shown.value === id ? null : id
}

/** 같은 버튼을 다시 누르면 "확인 안 함"으로 돌아간다. 학생 화면에 보이던 문항을 채점하면 다음 문항으로 넘어간다 */
function mark(id: string, value: boolean) {
  const next = { ...answers.value }
  if (next[id] === value) delete next[id]
  else next[id] = value
  answers.value = next

  if (id === shown.value && id in next) {
    const ids = [...screenItems.value.keys()]
    shown.value = ids[ids.indexOf(id) + 1] ?? null
  }
}

let seq = 0
watch(answers, async value => {
  const mine = ++seq
  try {
    const scored = await levelTestApi.score(value)
    if (mine === seq) result.value = scored // 늦게 온 이전 응답은 버린다
  } catch (e) {
    error.value = toUiError(e)
  }
})

const statusOf = (level: number) => result.value?.levels.find(l => l.level === level)
const STATUS_TEXT = { passed: '통과', failed: '못 넘음', not_enough: '더 확인 필요', untested: '' } as const
const STATUS_SEVERITY = { passed: 'success', failed: 'danger', not_enough: 'warn', untested: 'secondary' } as const

const checkedCount = computed(() => Object.keys(answers.value).length)
const itemClass = (id: string) => [
  answers.value[id] === true ? 'ok' : answers.value[id] === false ? 'ng' : '',
  shown.value === id ? 'shown' : '',
]

async function copy(text: string) {
  await navigator.clipboard.writeText(text)
  toast.add({ severity: 'info', summary: '복사했어요', detail: text, life: 1500 })
}

function reset() {
  answers.value = {}
  note.value = ''
  result.value = null
  shown.value = null
  saved.value = null
}

/** 판정은 저장할 때 서버가 다시 한다. 학생 화면은 "수고했어요"로 바뀐다 */
async function save() {
  saving.value = true
  error.value = null
  try {
    saved.value = await levelTestApi.save(answers.value, note.value)
    toast.add({ severity: 'success', summary: '결과를 저장했어요', detail: '학생 카드에 반영하려면 등급을 확인해 주세요', life: 3000 })
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mb-4 flex flex-wrap items-center gap-2">
    <h1 class="m-0 text-xl font-bold">체험수업 레벨테스트</h1>
    <Tag v-if="test" :value="`${test.minutes}분`" severity="secondary" />
    <Tag v-if="test" value="문항: Claude 초안 · 검수 필요" severity="warn" />
    <div class="flex-1" />
    <Button label="새 테스트" icon="pi pi-refresh" severity="secondary" text :disabled="!checkedCount && !saved" @click="reset" />
  </div>
  <ErrorBox :error="error" @retry="load" />

  <div v-if="!test && !error" class="space-y-3"><Skeleton v-for="i in 3" :key="i" height="8rem" /></div>

  <div v-else-if="test" class="grid gap-6 lg:grid-cols-[1fr_20rem]">
    <div class="space-y-5">
      <!-- 학생 화면 -->
      <section class="rounded-xl border border-primary-200 bg-primary-50 p-4">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="m-0 text-base font-bold"><i class="pi pi-desktop mr-1" />학생 화면</h2>
          <div class="flex-1" />
          <SelectButton v-model="screenLang" :options="langOptions" option-label="label" option-value="value" :allow-empty="false" size="small" />
          <Button label="학생 화면 열기" icon="pi pi-external-link" size="small" @click="openScreen" />
        </div>
        <p class="mb-0 mt-2 text-sm text-surface-600">
          새 창을 열어 화상수업에서 <b>그 창만</b> 공유하세요. 문항을 누르면 학생 화면에 크게 보이고, 맞음/틀림을 누르면 다음 문항으로 넘어가요.
          예시 답·확인할 점·등급은 학생 화면에 나오지 않아요. 안내 문구는 한국어 아래에 고른 언어로 한 줄 더 나와요.
        </p>
      </section>

      <section class="rounded-xl border border-surface-200 bg-white p-4">
        <button class="flex w-full items-center gap-2 border-0 bg-transparent p-0 text-left text-base font-bold" @click="showHowTo = !showHowTo">
          <i :class="showHowTo ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" class="text-sm" />진행 방법
        </button>
        <ol v-if="showHowTo" class="mb-0 mt-3 space-y-1 pl-5 text-sm text-surface-700">
          <li v-for="(line, i) in test.how_to" :key="i">{{ line }}</li>
        </ol>
        <p class="mb-0 mt-3 text-xs text-surface-500">
          문항은 국립국어원 「국제 통용 한국어 표준 교육과정」 등급 목록의 항목에 하나씩 묶여 있어요. 질문·예시 답은 Claude가 쓴 초안이라 검수가 필요해요.
        </p>
      </section>

      <!-- 한글 읽기 -->
      <section class="rounded-xl border border-surface-200 bg-white p-4">
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <h2 class="m-0 text-base font-bold">0. 한글 읽기</h2>
          <span class="text-sm text-surface-500">{{ test.hangul.pass_min }}/{{ test.hangul.words.length }}개 미만이면 입문</span>
          <div class="flex-1" />
          <Button label="단어 모두 복사" icon="pi pi-copy" size="small" severity="secondary" text @click="copy(test.hangul.words.map(w => w.word).join('  '))" />
        </div>
        <p class="mb-3 mt-0 text-sm text-surface-600">{{ test.hangul.instruction }}</p>
        <div class="flex flex-wrap gap-2">
          <div v-for="w in test.hangul.words" :key="w.id" class="item" :class="itemClass(w.id)">
            <button class="show-btn text-lg font-semibold" title="학생 화면에 보여 주기" @click="show(w.id)">{{ w.word }}</button>
            <span class="marks">
              <Button icon="pi pi-check" size="small" rounded :outlined="answers[w.id] !== true" severity="success" aria-label="맞음" @click="mark(w.id, true)" />
              <Button icon="pi pi-times" size="small" rounded :outlined="answers[w.id] !== false" severity="danger" aria-label="틀림" @click="mark(w.id, false)" />
            </span>
          </div>
        </div>
      </section>

      <!-- 등급별 -->
      <section v-for="section in test.levels" :key="section.level" class="rounded-xl border border-surface-200 bg-white p-4">
        <div class="mb-3 flex flex-wrap items-center gap-2">
          <h2 class="m-0 text-base font-bold">{{ section.name }}</h2>
          <span class="text-sm text-surface-500">약 {{ section.minutes }}분</span>
          <Tag
            v-if="statusOf(section.level) && statusOf(section.level)!.status !== 'untested'"
            :value="`${STATUS_TEXT[statusOf(section.level)!.status]} · ${statusOf(section.level)!.correct}/${statusOf(section.level)!.answered}`"
            :severity="STATUS_SEVERITY[statusOf(section.level)!.status]"
          />
        </div>

        <h3 class="mb-2 mt-0 text-sm font-semibold text-surface-500">문법 — 질문하고 대답에서 표현을 듣기</h3>
        <div class="space-y-2">
          <div v-for="g in section.grammar" :key="g.id" class="item block" :class="itemClass(g.id)">
            <div class="flex items-start gap-2">
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <Tag :value="g.form" severity="info" class="!text-xs" />
                  <button class="show-btn font-semibold" title="학생 화면에 보여 주기" @click="show(g.id)">{{ g.question }}</button>
                  <Button icon="pi pi-copy" size="small" text severity="secondary" aria-label="질문 복사" @click="copy(g.question)" />
                </div>
                <div class="mt-1 text-sm text-surface-600">듣기: {{ g.listen_for }}</div>
                <details class="mt-1 text-sm text-surface-500">
                  <summary class="cursor-pointer">예시 답</summary>
                  {{ g.example }}
                </details>
              </div>
              <span class="marks">
                <Button icon="pi pi-check" size="small" rounded :outlined="answers[g.id] !== true" severity="success" aria-label="맞음" @click="mark(g.id, true)" />
                <Button icon="pi pi-times" size="small" rounded :outlined="answers[g.id] !== false" severity="danger" aria-label="틀림" @click="mark(g.id, false)" />
              </span>
            </div>
          </div>
        </div>

        <h3 class="mb-2 mt-4 text-sm font-semibold text-surface-500">어휘 — 보여 주고 뜻을 말하거나 문장 만들기</h3>
        <div class="flex flex-wrap gap-2">
          <div v-for="v in section.vocab" :key="v.id" class="item" :class="itemClass(v.id)">
            <button class="show-btn" title="학생 화면에 보여 주기" @click="show(v.id)">
              <span class="font-semibold">{{ v.word }}</span>
              <span v-if="v.guide" class="ml-1 text-xs text-surface-400">{{ v.guide }}</span>
            </button>
            <span class="marks">
              <Button icon="pi pi-check" size="small" rounded :outlined="answers[v.id] !== true" severity="success" aria-label="맞음" @click="mark(v.id, true)" />
              <Button icon="pi pi-times" size="small" rounded :outlined="answers[v.id] !== false" severity="danger" aria-label="틀림" @click="mark(v.id, false)" />
            </span>
          </div>
        </div>
      </section>
    </div>

    <!-- 추천 결과 -->
    <aside class="lg:sticky lg:top-20 lg:self-start">
      <LevelTestResultCard v-if="saved" :result="saved" @changed="r => (saved = r)" />
      <section v-else class="rounded-xl border border-surface-200 bg-white p-4">
        <h2 class="mb-2 mt-0 text-base font-bold">추천 등급</h2>
        <div class="text-2xl font-bold" :class="result?.suggested_level == null ? 'text-surface-400' : 'text-primary-600'">
          {{ result?.suggested_level == null ? '아직 판정 전' : levelName(result.suggested_level) }}
        </div>
        <p class="mb-3 mt-1 text-sm text-surface-600">
          {{ result?.reason ?? `한 등급에서 ${test.min_answered}문항 이상 확인하면 추천해요.` }}
        </p>
        <ul v-if="result" class="m-0 mb-3 list-none space-y-1 p-0 text-sm">
          <li v-if="result.hangul_correct != null">한글 읽기 {{ result.hangul_correct }}/{{ test.hangul.words.length }}</li>
          <li v-for="l in result.levels.filter(l => l.status !== 'untested')" :key="l.level">
            {{ levelName(l.level) }} {{ l.correct }}/{{ l.answered }} · {{ STATUS_TEXT[l.status] }}
          </li>
        </ul>
        <label class="mb-1 block text-sm font-semibold text-surface-600" for="lt-note">관찰 메모 (학생 카드의 수준 세부 메모로 가요)</label>
        <Textarea id="lt-note" v-model="note" rows="3" auto-resize class="w-full" placeholder="예: 받침 발음 약함, -아요는 들어 봤지만 활용이 느림" />
        <Message severity="secondary" class="my-3 text-xs">저장하면 이 추천 등급과 문항별 결과가 남아요. 학생 카드에는 다음 단계에서 확인한 뒤 반영돼요.</Message>
        <Button label="결과 저장" icon="pi pi-save" class="w-full" :loading="saving" :disabled="result?.suggested_level == null" @click="save" />
      </section>
    </aside>
  </div>
</template>

<style scoped>
.item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 0.75rem;
  background: var(--p-surface-0);
}
.item.ok {
  border-color: var(--p-green-300);
  background: var(--p-green-50);
}
.item.ng {
  border-color: var(--p-red-300);
  background: var(--p-red-50);
}
/* 학생 화면에 지금 보이는 문항 */
.item.shown {
  outline: 3px solid var(--p-primary-400);
  outline-offset: 1px;
}
.show-btn {
  border: 0;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
  color: inherit;
}
.show-btn:hover {
  color: var(--p-primary-700);
}
.marks {
  display: inline-flex;
  gap: 0.25rem;
  flex-shrink: 0;
}
</style>
