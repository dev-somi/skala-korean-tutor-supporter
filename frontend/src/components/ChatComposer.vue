<script setup lang="ts">
// 채팅 입력창 + 설명 언어 토글 (기획 ADR-0035). 플로팅 위젯과 AI 채팅 탭이 같이 쓴다.
import { ref } from 'vue'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import { LANG_OPTIONS, useChatStore } from '../stores/chat'

defineProps<{ inputId: string }>()

const chat = useChatStore()
const input = ref('')

async function send() {
  const text = input.value
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
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center gap-2 text-xs text-surface-500">
      <span>설명 언어</span>
      <SelectButton
        :model-value="chat.lang"
        :options="LANG_OPTIONS"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        size="small"
        aria-label="설명 언어"
        @update:model-value="chat.setLang"
      />
    </div>
    <div class="flex items-end gap-2">
      <Textarea :id="inputId" v-model="input" rows="1" auto-resize class="max-h-40 flex-1" placeholder="메시지 (Enter 보내기, Shift+Enter 줄바꿈)" @keydown="onKey" />
      <Button v-if="chat.busy" icon="pi pi-stop-circle" severity="secondary" aria-label="중단" @click="chat.stop()" />
      <Button v-else icon="pi pi-send" :disabled="!input.trim()" aria-label="보내기" @click="send()" />
    </div>
  </div>
</template>
