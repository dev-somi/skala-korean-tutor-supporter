<script setup lang="ts">
// 오른쪽 아래 떠 있는 채팅 창. 페이지를 가리지 않아 대시보드를 보면서 물어볼 수 있다 (비모달).
// 좁은 화면에서는 화면 전체를 덮는다. 문법 근거 카드를 볼 때는 [넓게 보기]로 키운다.
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import GrammarSourcesPanel from './GrammarSourcesPanel.vue'
import { INTENT_NAMES, STAGE_NAMES, useChatStore, type ChatAction } from '../stores/chat'
import { useHandoffStore } from '../stores/handoff'
import { CHAT_MOCK } from '../api/endpoints'
import type { IntakeResult } from '../api/types'

const chat = useChatStore()
const handoff = useHandoffStore()
const router = useRouter()
const input = ref('')
const wide = ref(false)
const copied = ref<number | null>(null)
const scroller = ref<HTMLElement | null>(null)

const examples = ["'사토 유이' 다음 수업 50분으로 준비해줘", '-아서랑 -(으)니까 뭐가 달라? 일본인 학생한테 어떻게 설명해?', '사는이랑 살던 차이 설명해줘']

async function send(text = input.value) {
  if (!text.trim()) return
  input.value = ''
  await chat.send(text)
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape' && chat.open) chat.open = false
}
onMounted(() => window.addEventListener('keydown', onEsc))
onBeforeUnmount(() => window.removeEventListener('keydown', onEsc))

async function copy(text: string, i: number) {
  await navigator.clipboard.writeText(text)
  copied.value = i
  setTimeout(() => (copied.value = null), 1500)
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
}

watch(
  () => chat.messages.map(m => m.text.length + (m.sources ? 1 : 0)).join(),
  async () => {
    await nextTick()
    scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
  },
)

watch(
  () => chat.open,
  async open => {
    if (!open) return
    await nextTick()
    document.getElementById('chat-input')?.focus()
  },
)
</script>

<template>
  <Transition name="chat-pop">
    <section
      v-if="chat.open"
      role="dialog"
      aria-label="채팅"
      class="fixed inset-0 z-40 flex flex-col overflow-hidden bg-white md:inset-auto md:bottom-24 md:right-5 md:rounded-2xl md:border md:border-surface-200 md:shadow-2xl"
      :class="wide ? 'md:h-[calc(100vh-8rem)] md:w-[44rem]' : 'md:h-[min(40rem,calc(100vh-8rem))] md:w-[26rem]'"
    >
      <header class="flex items-center gap-2 border-b border-surface-200 bg-surface-50 px-4 py-2.5">
        <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary-600 text-white"><i class="pi pi-comments text-sm" /></span>
        <span class="font-semibold">채팅</span>
        <Tag v-if="CHAT_MOCK" value="MOCK" severity="warn" class="!text-[0.7rem]" />
        <span class="flex-1" />
        <Button v-if="chat.messages.length" v-tooltip.bottom="'새 대화'" icon="pi pi-refresh" text rounded size="small" severity="secondary" aria-label="새 대화" @click="chat.reset()" />
        <Button
          v-tooltip.bottom="wide ? '작게 보기' : '넓게 보기'"
          :icon="wide ? 'pi pi-window-minimize' : 'pi pi-window-maximize'"
          text
          rounded
          size="small"
          severity="secondary"
          class="!hidden md:!inline-flex"
          :aria-label="wide ? '작게 보기' : '넓게 보기'"
          @click="wide = !wide"
        />
        <Button icon="pi pi-times" text rounded size="small" severity="secondary" aria-label="닫기" @click="chat.open = false" />
      </header>

      <div ref="scroller" class="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        <div v-if="!chat.messages.length" class="text-sm text-surface-500">
          <p class="mt-1">학생 조회, 학생 등록, 수업 준비, 수업 후 기록, 한국어 문법 질문을 할 수 있어요.</p>
          <div class="flex flex-col gap-2">
            <Button v-for="ex in examples" :key="ex" :label="ex" size="small" severity="secondary" outlined class="!justify-start text-left" @click="send(ex)" />
          </div>
        </div>

        <div v-for="(m, i) in chat.messages" :key="i" :class="m.role === 'user' ? 'flex justify-end' : ''">
          <div v-if="m.role === 'user'" class="max-w-[85%] rounded-2xl rounded-br-sm bg-primary-600 px-3 py-2 text-white pre-line">{{ m.text }}</div>
          <div v-else class="group max-w-full rounded-2xl rounded-bl-sm bg-surface-100 px-3 py-2">
            <div v-if="m.intent" class="mb-1 flex flex-wrap items-center gap-1">
              <Tag :value="INTENT_NAMES[m.intent] ?? m.intent" severity="secondary" />
              <Tag v-if="m.studentName" :value="m.studentName" severity="info" />
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
                @click="copy(m.text, i)"
              />
            </div>
            <div v-if="m.sources && m.text" class="mb-1 text-xs text-surface-500">아래 교재 근거로 정리한 요점이에요.</div>
            <div class="pre-line text-[0.925rem] leading-relaxed">{{ m.text }}</div>
            <div v-if="m.pending && !m.text" class="flex items-center gap-2 text-sm text-surface-500">
              <i class="pi pi-spin pi-spinner" /> {{ STAGE_NAMES[m.stage ?? 'routing'] }}…
            </div>
            <GrammarSourcesPanel v-if="m.sources" :sources="m.sources" :wide="wide" />
            <div v-if="m.actions.length" class="mt-2 flex flex-wrap gap-2">
              <Button v-for="(a, j) in m.actions" :key="j" :label="a.label" icon="pi pi-arrow-right" icon-pos="right" size="small" @click="runAction(a)" />
            </div>
            <div v-if="m.error" class="mb-0 mt-2 flex flex-wrap items-center gap-2 text-sm text-red-600">
              <span><i class="pi pi-exclamation-triangle" /> {{ m.error.message }}</span>
              <Button v-if="m.error.retryable" label="다시 보내기" icon="pi pi-refresh" size="small" severity="danger" outlined :disabled="chat.busy" @click="chat.retry(i)" />
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-end gap-2 border-t border-surface-200 px-3 py-3">
        <Textarea id="chat-input" v-model="input" rows="1" auto-resize class="max-h-32 flex-1" placeholder="메시지 (Enter 보내기, Shift+Enter 줄바꿈)" @keydown="onKey" />
        <Button v-if="chat.busy" icon="pi pi-stop-circle" severity="secondary" aria-label="중단" @click="chat.stop()" />
        <Button v-else icon="pi pi-send" :disabled="!input.trim()" aria-label="보내기" @click="send()" />
      </div>
    </section>
  </Transition>

  <button
    type="button"
    class="fixed bottom-5 right-5 z-40 h-14 w-14 items-center justify-center rounded-full bg-primary-600 text-white shadow-lg transition hover:scale-105 hover:bg-primary-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-primary-200"
    :class="chat.open ? 'hidden md:flex' : 'flex'"
    :aria-label="chat.open ? '채팅 닫기' : '채팅 열기'"
    @click="chat.open = !chat.open"
  >
    <i class="pi text-xl" :class="chat.open ? 'pi-chevron-down' : 'pi-comments'" />
    <span v-if="chat.busy && !chat.open" class="absolute right-0.5 top-0.5 h-3.5 w-3.5 animate-pulse rounded-full border-2 border-white bg-amber-400" />
  </button>
</template>

<style scoped>
.chat-pop-enter-active,
.chat-pop-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
  transform-origin: bottom right;
}
.chat-pop-enter-from,
.chat-pop-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
}
</style>
