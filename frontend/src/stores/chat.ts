import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi, chatHistoryApi } from '../api/endpoints'
import type { ChatAction, ChatConversation, ChatLang, ChatRouting, GrammarSources, StoredChatMessage } from '../api/types'

export type { ChatAction, ChatConversation, ChatLang, GrammarForm, GrammarSource, GrammarSources } from '../api/types'

/** 답을 기다리는 동안 보여 줄 단계. 문법 질문은 RAG 검색이 길어서 단계를 나눠 보여 준다 */
export type ChatStage = 'routing' | 'searching' | 'writing' | 'answering'

export const STAGE_NAMES: Record<ChatStage, string> = {
  routing: '질문 분류 중',
  searching: '교재에서 근거 찾는 중',
  writing: '요점 정리 중',
  answering: '답 쓰는 중',
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  intent?: string
  studentName?: string | null
  /** 이 답에 쓴 설명 언어 */
  lang?: 'ja' | 'en'
  actions: ChatAction[]
  sources?: GrammarSources
  error?: { message: string; retryable: boolean }
  pending?: boolean
  stage?: ChatStage
  /** 이 답을 만든 질문 (다시 보내기용) */
  question?: string
}

export const INTENT_NAMES: Record<string, string> = {
  lookup: '조회',
  student_upsert: '학생 등록',
  lesson_prep: '수업 준비',
  post_lesson: '수업 후 기록',
  grammar_qa: '문법 질문',
  general: '일반 질문',
}

export const LANG_OPTIONS: { label: string; value: ChatLang }[] = [
  { label: '자동', value: 'auto' },
  { label: '日本語', value: 'ja' },
  { label: 'English', value: 'en' },
]

const newConversationId = () => 'c' + Math.random().toString(36).slice(2, 10)

// 마지막 대화와 언어 토글은 브라우저에 기억한다. 막힌 환경에서는 그냥 기억하지 않는다
const LAST_KEY = 'chat.conversationId'
const LANG_KEY = 'chat.lang'
function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
function writeStorage(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    // 기억하지 못해도 채팅은 된다
  }
}

/** 저장된 메시지를 화면용으로. 답의 question은 바로 앞 질문 (다시 보내기용) */
function fromStored(stored: StoredChatMessage[]): ChatMessage[] {
  return stored.map((m, i) =>
    m.role === 'user'
      ? { role: 'user', text: m.text, actions: [] }
      : {
          role: 'assistant',
          text: m.text,
          intent: m.meta.intent,
          studentName: m.meta.studentName,
          lang: m.meta.lang,
          sources: m.meta.sources,
          actions: m.meta.actions ?? [],
          error: m.meta.error,
          question: stored[i - 1]?.role === 'user' ? stored[i - 1].text : undefined,
        },
  )
}

/**
 * 플로팅 채팅과 AI 채팅 탭이 같은 대화를 쓴다 (기술 ADR-0042). 기록은 Spring이 답이 끝날 때 저장한다 (기술 ADR-0041).
 */
export const useChatStore = defineStore('chat', () => {
  const open = ref(false)
  const messages = ref<ChatMessage[]>([])
  const busy = ref(false)
  const conversationId = ref(readStorage(LAST_KEY) ?? newConversationId())
  const lang = ref<ChatLang>((readStorage(LANG_KEY) as ChatLang | null) ?? 'auto')
  const conversations = ref<ChatConversation[]>([])
  const loading = ref(false)
  /** messages가 어느 대화를 담고 있는지. 처음 열 때 기록을 한 번 불러온다 */
  let loadedId: string | null = null
  let controller: AbortController | null = null

  function setLang(value: ChatLang) {
    lang.value = value
    writeStorage(LANG_KEY, value)
  }

  async function refreshList() {
    try {
      conversations.value = await chatHistoryApi.list()
    } catch {
      // 목록을 못 불러와도 지금 대화는 계속한다
    }
  }

  /** 대화 하나를 불러온다. 없는 대화(아직 저장 전, 지워짐)면 빈 대화로 둔다 */
  async function load(id: string) {
    if (busy.value) return
    conversationId.value = id
    loadedId = id
    loading.value = true
    try {
      const stored = await chatHistoryApi.messages(id)
      if (conversationId.value === id) messages.value = fromStored(stored)
      writeStorage(LAST_KEY, id)
    } catch {
      if (conversationId.value === id) messages.value = []
    } finally {
      loading.value = false
    }
  }

  /** 위젯이나 탭을 처음 열 때: 마지막 대화를 아직 안 불러왔으면 불러온다 */
  async function ensureLoaded() {
    if (loadedId !== conversationId.value) await load(conversationId.value)
  }

  async function send(text: string) {
    if (!text.trim() || busy.value) return
    messages.value.push({ role: 'user', text, actions: [] })
    messages.value.push({ role: 'assistant', text: '', actions: [], pending: true, stage: 'routing', question: text })
    // reactive 프록시를 통해 고쳐야 화면이 바로 바뀐다
    const reply = messages.value[messages.value.length - 1]
    busy.value = true
    controller = new AbortController()
    try {
      await chatApi.stream(
        text,
        conversationId.value,
        lang.value,
        (event, data) => {
          if (event === 'routing_decided') {
            const routing = data as ChatRouting
            reply.intent = routing.intent
            reply.studentName = routing.student_name
            reply.lang = routing.lang
            reply.stage = routing.intent === 'grammar_qa' ? 'searching' : 'answering'
          } else if (event === 'token') {
            reply.text += data.text
          } else if (event === 'sources') {
            reply.sources = data as GrammarSources
            reply.stage = 'writing'
          } else if (event === 'action') {
            reply.actions.push(data as ChatAction)
          } else if (event === 'error') {
            reply.error = { message: data.message, retryable: data.retryable }
          }
        },
        controller.signal,
      )
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        if (!reply.text) reply.text = '(중단했어요)'
      } else {
        reply.error = { message: (e as Error).message, retryable: true }
      }
    } finally {
      reply.pending = false
      busy.value = false
      controller = null
      loadedId = conversationId.value
      writeStorage(LAST_KEY, conversationId.value)
      // 새 대화가 목록 맨 위에 뜨게. Spring이 스트림을 닫은 직후 저장하므로 조금 기다린다
      setTimeout(refreshList, 300)
    }
  }

  function stop() {
    controller?.abort()
  }

  /** 오류 난 답을 지우고 같은 질문을 다시 보낸다 */
  async function retry(index: number) {
    const question = messages.value[index]?.question
    if (!question || busy.value) return
    messages.value.splice(index - 1, 2)
    await send(question)
  }

  /** 새 대화. 서버에는 첫 질문을 보낼 때 생긴다 */
  function reset() {
    stop()
    messages.value = []
    conversationId.value = newConversationId()
    loadedId = conversationId.value
    writeStorage(LAST_KEY, null)
  }

  async function rename(id: string, title: string) {
    const updated = await chatHistoryApi.rename(id, title)
    conversations.value = conversations.value.map(c => (c.id === id ? updated : c))
  }

  async function remove(id: string) {
    await chatHistoryApi.remove(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (id === conversationId.value) reset()
  }

  return {
    open, messages, busy, conversationId, lang, conversations, loading,
    setLang, refreshList, load, ensureLoaded, send, stop, retry, reset, rename, remove,
  }
})
