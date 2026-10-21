<script setup lang="ts">
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import Menu from 'primevue/menu'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ChatWidget from './components/ChatWidget.vue'

const route = useRoute()
const router = useRouter()

// 주 메뉴는 매일 쓰는 학생 / 수업 준비만 두고, 나머지는 더보기에 묶는다 (기술 ADR-0029)
const moreItems = [
  { label: '레벨테스트', icon: 'pi pi-check-square', path: '/level-test' },
  { label: '커리큘럼·페르소나', icon: 'pi pi-book', path: '/curriculum' },
  { label: '어휘·문법', icon: 'pi pi-list', path: '/standard' },
  { label: '지표', icon: 'pi pi-chart-bar', path: '/metrics' },
  { label: 'AI 추적', icon: 'pi pi-sitemap', path: '/traces' },
].map(i => ({ ...i, command: () => router.push(i.path) }))
const moreMenu = ref<InstanceType<typeof Menu> | null>(null)

const isPrep = computed(() => route.path.startsWith('/prep') || /^\/lessons\/\d+\/review/.test(route.path))
const isStudents = computed(() => route.path.startsWith('/students') || /^\/lessons\/\d+\/record/.test(route.path))
const isMore = computed(() => moreItems.some(i => route.path.startsWith(i.path)))
</script>

<template>
  <RouterView v-if="$route.meta.bare" />
  <template v-else>
    <Toast />
    <ConfirmDialog />
    <header class="sticky top-0 z-20 border-b border-surface-200 bg-white/90 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2.5">
        <RouterLink to="/" class="mr-4 flex shrink-0 items-center gap-2 font-bold text-surface-900 no-underline">
          <img src="/favicon.svg" alt="" class="h-7 w-7" />
          <span>수업 노트 AI</span>
        </RouterLink>
        <!-- 좁은 화면에서는 가로로 밀어서 본다 -->
        <nav class="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
          <RouterLink to="/" class="nav-link">대시보드</RouterLink>
          <RouterLink to="/students" class="nav-link" :class="{ 'router-link-exact-active': isStudents }">학생</RouterLink>
          <RouterLink to="/prep" class="nav-link" :class="{ 'router-link-exact-active': isPrep }">수업 준비</RouterLink>
          <button type="button" class="nav-link more-button ml-auto" :class="{ 'router-link-exact-active': isMore }" aria-haspopup="true" @click="e => moreMenu?.toggle(e)">
            더보기 <i class="pi pi-angle-down text-xs" />
          </button>
          <Menu ref="moreMenu" :model="moreItems" popup />
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-6xl px-4 py-6">
      <RouterView :key="$route.fullPath" />
    </main>
    <ChatWidget />
  </template>
</template>

<style scoped>
.nav-link {
  white-space: nowrap;
  padding: 0.35rem 0.75rem;
  border-radius: 0.5rem;
  color: var(--p-surface-600);
  text-decoration: none;
  font-size: 0.925rem;
}
.more-button {
  border: 0;
  background: none;
  cursor: pointer;
  font: inherit;
  font-size: 0.925rem;
}
.nav-link:hover {
  background: var(--p-surface-100);
}
.nav-link.router-link-exact-active {
  color: var(--p-primary-700);
  background: var(--p-primary-50);
  font-weight: 600;
}
</style>
