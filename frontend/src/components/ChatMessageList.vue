<script setup lang="ts">
// 채팅 메시지 목록. 플로팅 위젯과 AI 채팅 탭이 같이 쓴다 (기술 ADR-0042). 이 요소가 스크롤된다.
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import GrammarSourcesPanel from './GrammarSourcesPanel.vue'
import { INTENT_NAMES, STAGE_NAMES, useChatStore, type ChatAction } from '../stores/chat'
import { useHandoffStore } from '../stores/handoff'
import type { GrammarSources, IntakeResult } from '../api/types'

// contentClass: 넓은 화면에서 글 폭을 줄여 가운데 둘 때 (AI 채팅 탭)
defineProps<{ wide?: boolean; contentClass?: string }>()
const emit = defineEmits<{ navigate: [] }>()

const chat = useChatStore()
const handoff = useHandoffStore()
const router = useRouter()
const copied = ref<number | null>(null)
const scroller = ref<HTMLElement | null>(null)

const examples = ["'사토 유이' 다음 수업 50분으로 준비해줘", '-아서랑 -(으)니까 뭐가 달라? 일본인 학생한테 어떻게 설명해?', '사는이랑 살던 차이 설명해줘']
// 설명 언어가 의미 있는 답에만 언어 태그를 단다
const LANG_INTENTS = new Set(['grammar_qa', 'general'])

async function copy(text: string, i: number) {
  await navigator.clipboard.writeText(text)
  copied.value = i
  setTimeout(() => (copied.value = null), 1500)
}

// 문법 답 복사: 비교표를 글로 펼치고 핵심 차이를 붙인다 (메신저·메모에 붙여 넣기 좋게)
function grammarCopyText(sources: GrammarSources, text: string) {
  const rows = sources.forms.map(f => {
    const level = f.level !== null ? ` (${f.level}급)` : ''
    const usage = f.grounded ? f.usage || f.meaning || '' : f.ai ? `${f.ai.usage} (AI 설명: ${f.ai.explanation})` : '교재 근거 없음'
    return `${f.form}${level}: ${usage}${f.example ? ` — 예) ${f.example}` : ''}`
  })
  return [...rows, ...(text ? ['', '핵심 차이', text] : [])].join('\n')
}

function runAction(action: ChatAction) {
  if (action.type === 'open_intake') {
    handoff.intake = action.intake as IntakeResult
    router.push({ name: 'student-new', query: { from: 'chat' } })
  } else if (action.type === 'open_prep' && action.lesson_id) {
    router.push({ name: 'lesson-review', params: { id: action.lesson_id } })
  } else if (action.type === 'open_record' && action.lesson_id) {
    if (action.note) handoff.notes[action.lesson_id] = action.note
    router.push({ name: 'lesson-record', params: { id: action.lesson_id } })
  } else if (action.type === 'open_student' && action.student_id) {
    router.push({ name: 'student', params: { id: action.student_id } })
  }
  emit('navigate')
}

watch(
  () => chat.messages.map(m => m.text.length + (m.sources ? 1 : 0)).join(),
  async () => {
    await nextTick()
    scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
  },
)
</script>

<template>
  <div ref="scroller" class="overflow-y-auto">
    <div class="space-y-3" :class="contentClass">
      <div v-if="chat.loading && !chat.messages.length" class="flex items-center gap-2 text-sm text-surface-500">
        <i class="pi pi-spin pi-spinner" /> 대화 불러오는 중…
      </div>
      <div v-else-if="!chat.messages.length" class="text-sm text-surface-500">
        <p class="mt-1">학생 조회, 학생 등록, 수업 준비, 수업 후 기록, 한국어 문법 질문을 할 수 있어요.</p>
        <div class="flex flex-col gap-2">
          <Button v-for="ex in examples" :key="ex" :label="ex" size="small" severity="secondary" outlined class="!justify-start text-left" @click="chat.send(ex)" />
        </div>
      </div>

      <div v-for="(m, i) in chat.messages" :key="i" :class="m.role === 'user' ? 'flex justify-end' : ''">
        <div v-if="m.role === 'user'" class="max-w-[85%] rounded-2xl rounded-br-sm bg-primary-600 px-3 py-2 text-white pre-line">{{ m.text }}</div>
        <div v-else class="group max-w-full rounded-2xl rounded-bl-sm bg-surface-100 px-3 py-2">
          <div v-if="m.intent" class="mb-1 flex flex-wrap items-center gap-1">
            <Tag :value="INTENT_NAMES[m.intent] ?? m.intent" severity="secondary" />
            <Tag v-if="m.studentName" :value="m.studentName" severity="info" />
            <Tag v-if="m.lang && LANG_INTENTS.has(m.intent)" :value="m.lang.toUpperCase()" severity="contrast" class="!text-[0.7rem]" />
            <span class="flex-1" />
            <Button
              v-if="!m.pending && m.text"
              :icon="copied === i ? 'pi pi-check' : 'pi pi-copy'"
              text
              rounded
              size="small"
              severity="secondary"
              class="!h-6 !w-6 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
              aria-label="답 복사"
              @click="copy(m.sources?.forms.length ? grammarCopyText(m.sources, m.text) : m.text, i)"
            />
          </div>
          <!-- 문법 질문은 표·핵심 차이·근거를 패널이 한 번에 그린다 (기술 ADR-0043) -->
          <GrammarSourcesPanel v-if="m.sources?.forms.length" :sources="m.sources" :text="m.text" />
          <div v-else class="pre-line text-[0.925rem] leading-relaxed">{{ m.text }}</div>
          <div v-if="m.pending && !m.text" class="mt-2 flex items-center gap-2 text-sm text-surface-500">
            <i class="pi pi-spin pi-spinner" /> {{ STAGE_NAMES[m.stage ?? 'routing'] }}…
          </div>
          <div v-if="m.actions.length" class="mt-2 flex flex-wrap gap-2">
            <Button v-for="(a, j) in m.actions" :key="j" :label="a.label" icon="pi pi-arrow-right" icon-pos="right" size="small" @click="runAction(a)" />
          </div>
          <div v-if="m.error" class="mb-0 mt-2 flex flex-wrap items-center gap-2 text-sm text-red-600">
            <span><i class="pi pi-exclamation-triangle" /> {{ m.error.message }}</span>
            <Button v-if="m.error.retryable && m.question" label="다시 보내기" icon="pi pi-refresh" size="small" severity="danger" outlined :disabled="chat.busy" @click="chat.retry(i)" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
