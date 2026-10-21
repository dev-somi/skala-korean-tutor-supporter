<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { SCREEN_TEXT, openScreenChannel, type ScreenItem, type ScreenLang, type ScreenMessage } from '../levelTestScreen'

// 학생에게 보여 주는 레벨테스트 화면 (기획 ADR-0021). 선생님이 이 창을 화상수업에서 공유한다.
// 선생님 화면이 보낸 문항만 크게 보여 준다. 채점·등급·예시 답은 이 화면에 없다.

const lang = ref<ScreenLang>('ko')
const item = ref<ScreenItem | null>(null)
const done = ref(false)

const channel = openScreenChannel()
channel.onmessage = (e: MessageEvent<ScreenMessage>) => {
  const msg = e.data
  if (msg.type === 'show') {
    lang.value = msg.lang
    item.value = msg.item
    done.value = false
  } else if (msg.type === 'done') {
    lang.value = msg.lang
    done.value = true
  }
}
onMounted(() => {
  document.title = SCREEN_TEXT.ko.title
  channel.postMessage({ type: 'hello' } satisfies ScreenMessage)
})
onBeforeUnmount(() => channel.close())

/** 한국어 문장 + (학생 언어가 있으면) 그 언어 한 줄 */
const say = (key: 'waiting' | 'done' | 'hangul' | 'grammar' | 'vocab') => {
  const ko = SCREEN_TEXT.ko[key]
  return lang.value === 'ko' ? [ko] : [ko, SCREEN_TEXT[lang.value][key]]
}
const part = computed(() => {
  if (!item.value) return ''
  const t = SCREEN_TEXT[lang.value]
  return item.value.level == null ? t.partHangul : t.part(item.value.level)
})
</script>

<template>
  <div class="screen">
    <header class="flex items-center gap-3 px-8 py-5 text-surface-500">
      <img src="/favicon.svg" alt="" class="h-7 w-7" />
      <span class="font-semibold">{{ SCREEN_TEXT[lang].title }}</span>
      <div class="flex-1" />
      <span v-if="item && !done" class="text-lg">{{ part }}</span>
    </header>

    <main class="flex flex-1 flex-col items-center justify-center px-8 pb-16 text-center">
      <template v-if="done">
        <div class="text-5xl">🎉</div>
        <p v-for="(line, i) in say('done')" :key="i" :class="i ? 'sub' : 'lead'">{{ line }}</p>
      </template>

      <template v-else-if="!item">
        <p v-for="(line, i) in say('waiting')" :key="i" :class="i ? 'sub' : 'lead'">{{ line }}</p>
      </template>

      <template v-else>
        <div :key="item.text" class="appear w-full">
          <div :class="item.kind === 'grammar' ? 'question' : 'word'">{{ item.text }}</div>
          <div class="mt-10">
            <p v-for="(line, i) in say(item.kind)" :key="i" :class="i ? 'sub' : 'hint'">{{ line }}</p>
          </div>
        </div>
        <div class="dots mt-12" :aria-label="`${item.index} / ${item.total}`">
          <span v-for="n in item.total" :key="n" :class="{ on: n <= item.index }" />
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.screen {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--p-surface-0);
  color: var(--p-surface-900);
}
.word {
  font-size: clamp(4rem, 12vw, 9rem);
  font-weight: 700;
  line-height: 1.1;
}
.question {
  font-size: clamp(2rem, 5vw, 3.75rem);
  font-weight: 700;
  line-height: 1.35;
  word-break: keep-all;
}
.lead {
  margin: 0.5rem 0 0;
  font-size: 2.25rem;
  font-weight: 700;
}
.hint {
  margin: 0;
  font-size: 1.5rem;
  color: var(--p-surface-600);
}
.sub {
  margin: 0.35rem 0 0;
  font-size: 1.25rem;
  color: var(--p-surface-400);
}
.dots {
  display: flex;
  gap: 0.5rem;
}
.dots span {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 999px;
  background: var(--p-surface-200);
}
.dots span.on {
  background: var(--p-primary-500);
}
.appear {
  animation: appear 0.25s ease-out;
}
@keyframes appear {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}
</style>
