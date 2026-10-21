import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('./pages/DashboardPage.vue') },
    { path: '/students', name: 'students', component: () => import('./pages/StudentsPage.vue') },
    { path: '/students/new', name: 'student-new', component: () => import('./pages/StudentNewPage.vue') },
    { path: '/students/:id/report', name: 'student-report', component: () => import('./pages/StudentReportPage.vue'), props: r => ({ id: Number(r.params.id) }) },
    { path: '/students/:id', name: 'student', component: () => import('./pages/StudentDetailPage.vue'), props: r => ({ id: Number(r.params.id) }) },
    { path: '/prep', name: 'prep', component: () => import('./pages/PrepPage.vue') },
    { path: '/lessons/:id/review', name: 'lesson-review', component: () => import('./pages/LessonReviewPage.vue'), props: r => ({ id: Number(r.params.id) }) },
    { path: '/lessons/:id/record', name: 'lesson-record', component: () => import('./pages/LessonRecordPage.vue'), props: r => ({ id: Number(r.params.id) }) },
    { path: '/metrics', name: 'metrics', component: () => import('./pages/MetricsPage.vue') },
    { path: '/traces', name: 'traces', component: () => import('./pages/TracesPage.vue') },
    { path: '/level-test', name: 'level-test', component: () => import('./pages/LevelTestPage.vue') },
    // 학생에게 화면 공유로 보여 주는 창. 선생님용 메뉴·채팅을 숨긴다 (기획 ADR-0021)
    { path: '/level-test/screen', name: 'level-test-screen', component: () => import('./pages/LevelTestScreenPage.vue'), meta: { bare: true } },
    { path: '/level-test/results/:id', name: 'level-test-result', component: () => import('./pages/LevelTestResultPage.vue'), props: r => ({ id: Number(r.params.id) }) },
    { path: '/standard', name: 'standard', component: () => import('./pages/StandardPage.vue') },
    { path: '/curriculum', name: 'curriculum', component: () => import('./pages/CurriculumPage.vue') },
    { path: '/personas', redirect: { path: '/curriculum', query: { tab: 'persona' } } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
