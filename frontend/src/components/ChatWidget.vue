<script setup lang="ts">
// 오른쪽 아래 떠 있는 채팅 창. 페이지를 가리지 않아 대시보드를 보면서 물어볼 수 있다 (비모달).
// 좁은 화면에서는 화면 전체를 덮는다. 크게 보고 싶으면 같은 대화를 AI 채팅 탭에서 연다 (기술 ADR-0042).
import { nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ChatMessageList from './ChatMessageList.vue'
import ChatComposer from './ChatComposer.vue'
import { useChatStore } from '../stores/chat'
import { CHAT_MOCK } from '../api/endpoints'

const chat = useChatStore()
const router = useRouter()

function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape' && chat.open) chat.open = false
}
onMounted(() => window.addEventListener('keydown', onEsc))
onBeforeUnmount(() => window.removeEventListener('keydown', onEsc))

function openInTab() {
  chat.open = false
  router.push({ name: 'chat', params: { id: chat.conversationId } })
}

watch(
  () => chat.open,
  async open => {
    if (!open) return
    chat.ensureLoaded()
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
      class="fixed inset-0 z-40 flex flex-col overflow-hidden bg-white md:inset-auto md:bottom-24 md:right-5 md:h-[min(40rem,calc(100vh-8rem))] md:w-[26rem] md:rounded-2xl md:border md:border-surface-200 md:shadow-2xl"
    >
      <header class="flex items-center gap-2 border-b border-surface-200 bg-surface-50 px-4 py-2.5">
        <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary-600 text-white"><i class="pi pi-comments text-sm" /></span>
        <span class="font-semibold">채팅</span>
        <Tag v-if="CHAT_MOCK" value="MOCK" severity="warn" class="!text-[0.7rem]" />
        <span class="flex-1" />
        <Button v-if="chat.messages.length" v-tooltip.bottom="'새 대화'" icon="pi pi-plus" text rounded size="small" severity="secondary" aria-label="새 대화" @click="chat.reset()" />
        <Button v-tooltip.bottom="'AI 채팅 탭에서 크게 보기'" icon="pi pi-external-link" text rounded size="small" severity="secondary" aria-label="AI 채팅 탭에서 크게 보기" @click="openInTab" />
        <Button icon="pi pi-times" text rounded size="small" severity="secondary" aria-label="닫기" @click="chat.open = false" />
      </header>

      <ChatMessageList class="flex-1 px-4 py-3" />

      <ChatComposer input-id="chat-input" class="border-t border-surface-200 px-3 py-3" />
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
