<script setup lang="ts">
// AI 채팅 탭: 큰 화면 채팅 + 대화 목록 (기획 ADR-0035, 기술 ADR-0042).
// 플로팅 위젯과 같은 스토어를 써서, 위젯에서 하던 대화를 여기서 이어 간다.
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import ChatMessageList from '../components/ChatMessageList.vue'
import ChatComposer from '../components/ChatComposer.vue'
import { useChatStore, type ChatConversation } from '../stores/chat'
import { CHAT_MOCK } from '../api/endpoints'
import { formatDateTime, toUiError } from '../utils'

const props = defineProps<{ id?: string }>()

const chat = useChatStore()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const showList = ref(false) // 좁은 화면에서 목록 열기
const editingId = ref<string | null>(null)
const editingTitle = ref('')

const currentTitle = computed(() => chat.conversations.find(c => c.id === chat.conversationId)?.title ?? '새 대화')

onMounted(async () => {
  chat.open = false
  chat.refreshList()
  if (props.id && props.id !== chat.conversationId) await chat.load(props.id)
  else await chat.ensureLoaded()
  await nextTick()
  document.getElementById('chat-page-input')?.focus()
})

function select(c: ChatConversation) {
  showList.value = false
  if (c.id !== chat.conversationId) router.push({ name: 'chat', params: { id: c.id } })
}

function newChat() {
  showList.value = false
  chat.reset()
  router.push({ name: 'chat' })
  nextTick(() => document.getElementById('chat-page-input')?.focus())
}

function startRename(c: ChatConversation) {
  editingId.value = c.id
  editingTitle.value = c.title
  nextTick(() => document.getElementById(`rename-${c.id}`)?.focus())
}

async function saveRename() {
  const id = editingId.value
  const title = editingTitle.value.trim()
  editingId.value = null
  if (!id || !title) return
  try {
    await chat.rename(id, title)
  } catch (e) {
    toast.add({ severity: 'error', summary: '이름을 바꾸지 못했어요', detail: toUiError(e).message, life: 4000 })
  }
}

function askRemove(c: ChatConversation) {
  confirm.require({
    message: `'${c.title}' 대화를 지울까요? 되돌릴 수 없어요.`,
    header: '대화 삭제',
    acceptProps: { label: '삭제', severity: 'danger' },
    rejectProps: { label: '취소', severity: 'secondary', text: true },
    accept: async () => {
      const wasCurrent = c.id === chat.conversationId
      try {
        await chat.remove(c.id)
        if (wasCurrent) router.push({ name: 'chat' })
      } catch (e) {
        toast.add({ severity: 'error', summary: '지우지 못했어요', detail: toUiError(e).message, life: 4000 })
      }
    },
  })
}
</script>

<template>
  <!-- 메뉴 아래 공간을 다 쓴다 (App.vue가 높이를 준다) -->
  <div class="relative flex min-h-0 flex-1 overflow-hidden bg-white">
    <!-- 대화 목록: 넓은 화면은 왼쪽 고정, 좁은 화면은 버튼으로 덮어 연다 -->
    <aside
      class="absolute inset-y-0 left-0 z-10 w-72 flex-col border-r border-surface-200 bg-surface-50 md:static md:flex"
      :class="showList ? 'flex shadow-xl' : 'hidden'"
    >
      <div class="flex items-center gap-2 p-3">
        <Button label="새 대화" icon="pi pi-plus" size="small" class="flex-1" :disabled="chat.busy" @click="newChat" />
        <Button icon="pi pi-times" text rounded size="small" severity="secondary" class="md:!hidden" aria-label="목록 닫기" @click="showList = false" />
      </div>
      <nav class="flex-1 overflow-y-auto px-2 pb-3" aria-label="대화 목록">
        <p v-if="!chat.conversations.length" class="px-2 text-sm text-surface-500">아직 저장된 대화가 없어요.</p>
        <div
          v-for="c in chat.conversations"
          :key="c.id"
          class="group mb-0.5 flex items-center gap-1 rounded-lg px-2 py-1.5"
          :class="c.id === chat.conversationId ? 'bg-primary-50 text-primary-700' : 'hover:bg-surface-100'"
        >
          <InputText
            v-if="editingId === c.id"
            :id="`rename-${c.id}`"
            v-model="editingTitle"
            size="small"
            class="min-w-0 flex-1"
            maxlength="100"
            @keydown.enter="saveRename"
            @keydown.esc="editingId = null"
            @blur="saveRename"
          />
          <button
            v-else
            type="button"
            class="min-w-0 flex-1 cursor-pointer border-0 bg-transparent p-0 text-left text-inherit"
            :disabled="chat.busy"
            @click="select(c)"
          >
            <span class="block truncate text-sm" :class="{ 'font-semibold': c.id === chat.conversationId }">{{ c.title }}</span>
            <span class="block text-xs text-surface-500">{{ formatDateTime(c.updatedAt) }}</span>
          </button>
          <template v-if="editingId !== c.id">
            <Button icon="pi pi-pencil" text rounded size="small" severity="secondary" class="!h-7 !w-7 opacity-0 group-hover:opacity-100 focus:opacity-100" aria-label="이름 바꾸기" @click="startRename(c)" />
            <Button icon="pi pi-trash" text rounded size="small" severity="secondary" class="!h-7 !w-7 opacity-0 group-hover:opacity-100 focus:opacity-100" aria-label="삭제" :disabled="chat.busy" @click="askRemove(c)" />
          </template>
        </div>
      </nav>
    </aside>

    <section class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center gap-2 border-b border-surface-200 px-4 py-2.5">
        <Button icon="pi pi-bars" text rounded size="small" severity="secondary" class="md:!hidden" aria-label="대화 목록" @click="showList = true" />
        <h1 class="m-0 min-w-0 truncate text-base font-semibold">{{ currentTitle }}</h1>
        <Tag v-if="CHAT_MOCK" value="MOCK" severity="warn" class="!text-[0.7rem]" />
      </header>

      <ChatMessageList wide class="min-h-0 flex-1 px-4 py-4 md:px-8" content-class="mx-auto max-w-4xl" />

      <div class="border-t border-surface-200 px-4 py-3 md:px-8">
        <ChatComposer input-id="chat-page-input" class="mx-auto max-w-4xl" />
      </div>
    </section>
  </div>
</template>
