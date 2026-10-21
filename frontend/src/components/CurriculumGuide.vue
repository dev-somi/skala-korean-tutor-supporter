<script setup lang="ts">
// 온라인 세종학당 교육과정 (세종학당재단 누리집, 2026-10-20 확인).
// 과정·교재·과 수·설명은 누리집 내용을 옮긴 것이다. "표준 등급" 칸은 과정 설명에 적힌 범위다 (단계별 1:1 대응은 누리집에 없다).

const SOURCE = 'https://www.iksi.or.kr/lms/main/curriculum.do'
const CHECKED = '2026-10-20'

const BASIC = [
  {
    course: '초급 (Beginner)',
    levels: '표준 1·2급',
    stages: 'Beginner 1 · Beginner 2',
    books: '세종학당 한국어 1, 2 · 세종 한국어 회화 1, 2',
    lessons: '40과 (20과 + 20과)',
    desc: '표준 교육과정 초급(1·2급)의 목표 어휘와 문법 표현을 바탕으로, 한국 일상생활의 실용적 의사소통을 연습',
    langs: '설명 언어 15개 (영어, 일본어, 중국어 등)',
  },
  {
    course: '중급 (Intermediate)',
    levels: '표준 3·4급',
    stages: 'Intermediate 1 · Intermediate 2',
    books: '세종학당 한국어 3, 4 · 세종 한국어 회화 3, 4',
    lessons: '40과 (20과 + 20과)',
    desc: '표준 교육과정 중급(3·4급)의 목표 어휘와 문법 표현을 바탕으로 일상생활의 실용적 의사소통을 연습',
    langs: '한국어',
  },
  {
    course: '고급 (Advanced)',
    levels: '표준 5·6급',
    stages: 'Advanced 1 · Advanced 2',
    books: '세종학당 한국어 5, 6',
    lessons: '40과 (20과 + 20과)',
    desc: '표준 교육과정 고급(5·6급)의 목표 어휘와 문법 표현을 바탕으로 고급 한국어 능력을 기르는 연습 활동',
    langs: '한국어',
  },
]

const SPECIAL = [
  { course: '입문 (Introductory)', books: '세종학당 한국어 입문', lessons: '12과', desc: '한국어를 처음 배우는 학습자를 위해 한글과 기초 어휘에 집중', langs: '설명 언어 15개' },
  { course: '비즈니스 한국어', books: '비즈니스 한국어 1, 2', lessons: '24과 (12과 + 12과)', desc: '한국 기업에서 쓰는 표현에 집중한 업무 목적 과정', langs: '한국어, 영어, 중국어, 스페인어' },
  { course: '읽기·쓰기', books: '세종학당 한국어 읽기, 쓰기', lessons: '30과 (읽기 15과 + 쓰기 15과)', desc: '사회, 문화, 과학, 경제, 역사 등 여러 분야의 글로 읽기·쓰기를 기르는 고급 학습자 과정', langs: '한국어' },
  { course: '외국인 근로자를 위한 한국어', books: '외국인 근로자를 위한 한국어 1, 2', lessons: '-', desc: '기타 목적 과정 (누리집에 상세 설명 없음)', langs: '-' },
]
</script>

<template>
  <div class="space-y-4">
    <section class="guide">
      <h2>한눈에 보기</h2>
      <div class="ladder">
        <div class="step intro"><b>입문</b><span>한글 · 기초 어휘</span><small>이 서비스의 "입문 (한글부터)"</small></div>
        <div class="step"><b>초급</b><span>세종학당 한국어 1 · 2</span><small>표준 1·2급</small></div>
        <div class="step"><b>중급</b><span>세종학당 한국어 3 · 4</span><small>표준 3·4급</small></div>
        <div class="step"><b>고급</b><span>세종학당 한국어 5 · 6</span><small>표준 5·6급</small></div>
      </div>
      <p class="lead">
        온라인 세종학당의 기본 과정은 <b>국립국어원 표준 교육과정의 등급별 목표 어휘·문법</b>을 바탕으로 짜여 있어요. 이 화면의 문법·어휘 탭이 바로 그 기준이에요.
        교재 이름의 숫자(한국어 1, 2…)와 표준 등급이 나란히 가지만, 과 단위로 몇 급인지는 누리집에 나와 있지 않아요.
      </p>
    </section>

    <section class="guide">
      <h2>기본 교육과정</h2>
      <div class="overflow-x-auto">
        <table>
          <thead><tr><th>과정</th><th>표준 등급</th><th>교재</th><th>분량</th><th>설명</th></tr></thead>
          <tbody>
            <tr v-for="c in BASIC" :key="c.course">
              <th>{{ c.course }}<div class="note">{{ c.stages }}</div></th>
              <td class="whitespace-nowrap font-semibold">{{ c.levels }}</td>
              <td>{{ c.books }}</td>
              <td class="whitespace-nowrap">{{ c.lessons }}</td>
              <td>{{ c.desc }}<div class="note">{{ c.langs }}</div></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="note mt-2">강의 지원형·학습 지원형은 단계마다 A, B 두 권(예: Beginner 1A, 1B), 자기주도형은 「세종학당 한국어 1~6」(중급부터는 3A, 3B처럼 나뉨)을 써요.</p>
    </section>

    <section class="guide">
      <h2>특별 교육과정 <small class="font-normal text-surface-500">학습자의 특정 목적(취업, 업무 등)에 맞춘 과정</small></h2>
      <div class="overflow-x-auto">
        <table>
          <thead><tr><th>과정</th><th>교재</th><th>분량</th><th>설명</th></tr></thead>
          <tbody>
            <tr v-for="c in SPECIAL" :key="c.course">
              <th>{{ c.course }}</th>
              <td>{{ c.books }}</td>
              <td class="whitespace-nowrap">{{ c.lessons }}</td>
              <td>{{ c.desc }}<div v-if="c.langs !== '-'" class="note">{{ c.langs }}</div></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="note mt-2">한국문화 과정으로 "세종문화아카데미"도 있어요.</p>
    </section>

    <p class="text-xs text-surface-500">
      출처: 세종학당재단, <a :href="SOURCE" target="_blank" rel="noopener">온라인 세종학당 교육과정</a> ({{ CHECKED }} 확인). 수업 시간(분)은 누리집에 없고 과 수만 있어요.
    </p>
  </div>
</template>

<style scoped>
.guide {
  padding: 1rem 1.25rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 0.75rem;
  background: var(--p-surface-0);
}
.guide h2 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 700;
}
.lead {
  margin: 0.75rem 0 0;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--p-surface-700);
}
.ladder {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}
.step {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.75rem;
  border-radius: 0.6rem;
  background: var(--p-primary-50);
  border: 1px solid var(--p-primary-100);
  font-size: 0.85rem;
}
.step.intro {
  background: var(--p-surface-50);
  border-color: var(--p-surface-200);
}
.step b {
  font-size: 1rem;
}
.step small {
  color: var(--p-surface-500);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
th,
td {
  padding: 0.55rem 0.6rem;
  border-top: 1px solid var(--p-surface-200);
  text-align: left;
  vertical-align: top;
}
thead th {
  border-top: 0;
  font-size: 0.8rem;
  color: var(--p-surface-500);
  font-weight: 600;
}
tbody th {
  white-space: nowrap;
}
.note {
  margin-top: 0.2rem;
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--p-surface-500);
}
@media (max-width: 640px) {
  .ladder {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
