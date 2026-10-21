<script setup lang="ts">
// [어휘·문법] 화면의 설명 탭: 문법 분류와 어휘 품사가 각각 무엇인지.
// 분류·품사 값은 국립국어원 원본 엑셀 그대로이고, 예시는 그 목록에서 실제로 고른 것이다 (괄호 안은 등급).

const GRAMMAR = [
  {
    name: '조사',
    what: '명사 같은 말 뒤에 붙어서 문장에서의 역할(주어, 목적어, 장소 등)을 나타내거나 뜻을 더해요.',
    examples: '이/가 · 을/를 · 에서 · 도 · 부터/까지 (1급)',
    note: "학교문법을 따라서 '이다'도 조사(서술격 조사)로, 존댓말 '요'도 조사(3급)로 들어 있어요.",
  },
  {
    name: '선어말어미',
    what: '동사·형용사의 어간과 맨 끝 어미 사이에 들어가서 시제나 높임을 나타내요.',
    examples: '-었- (과거) · -겠- · -으시- (높임) (1급)',
    note: '목록 전체에 4개뿐이에요.',
  },
  {
    name: '연결어미',
    what: '앞 문장을 뒤 문장에 이어요. 이유, 조건, 대조, 나열 같은 관계를 나타내요.',
    examples: '-고 · -어서 · -지만 · -으니까 (1급), -으면 · -는데 (2급)',
    note: '-어서와 -으니까는 둘 다 이유지만 같은 분류 안에서도 쓰임이 달라서, 차이를 따로 설명해야 해요.',
  },
  {
    name: '종결어미',
    what: '문장을 끝내요. 문장 종류(말하기, 묻기, 시키기, 같이 하자고 하기)와 높임 정도가 여기서 정해져요.',
    examples: '-습니다 · -습니까 · -으세요 · -읍시다 (1급), -을게 · -네 (2급)',
    note: '-아요/어요는 1급 종결어미 -어의 관련형으로 들어 있어요.',
  },
  {
    name: '전성어미',
    what: '동사·형용사를 다른 품사처럼 쓰게 바꿔요. 명사를 꾸미는 말(관형사형)이나 명사(명사형)로 만들어요.',
    examples: '-는/-은/-을 (명사 꾸미기: 먹는 음식) · -기 · -음 (명사로: 먹기) (2급)',
    note: '목록 전체에 7개뿐이지만 2급 문법의 바탕이 되는 중요한 항목이에요.',
  },
  {
    name: '표현',
    what: '여러 형태가 굳어져서 하나의 뜻으로 쓰이는 덩어리예요. 한국어 교육에서는 하나의 문법 항목으로 가르쳐요.',
    examples: '-고 싶다 · -을 수 있다 · -지 않다 · -기 전에 (1급), -게 되다 (2급)',
    note: '예를 들어 -고 싶다는 연결어미 -고 + 싶다지만, 학생에게는 통째로 가르쳐요. 목록에서 가장 많은 분류예요 (136개).',
  },
]

const POS = [
  { name: '명사', what: '사람, 물건, 장소, 개념의 이름이에요.', examples: '학교 · 친구 · 날씨 · 주말 (1급)', note: '' },
  {
    name: '의존명사',
    what: '혼자 쓰지 못하고 앞에 꾸며 주는 말이 있어야 하는 명사예요. 세는 단위도 여기에 들어가요.',
    examples: '것 · 때 (어릴 때) · 개 · 명 · 마리 · 권 (1급)',
    note: "-은 적이 있다의 '적'처럼 문법 표현 안에 들어가는 것도 많아요.",
  },
  { name: '대명사', what: '이름 대신 사람이나 사물, 장소를 가리켜요.', examples: '나 · 너 · 누구 · 무엇 · 거기 (1급)', note: '' },
  { name: '수사', what: '수나 순서를 나타내요.', examples: '둘 · 넷 · 다섯 · 마흔 · 백 (1급)', note: "'다섯'처럼 관형사로도 쓰이는 수가 많아요 (다섯이 왔어요 / 다섯 명)." },
  { name: '동사', what: '움직임이나 동작을 나타내요.', examples: '가다 · 먹다 · 배우다 (1급)', note: '' },
  {
    name: '형용사',
    what: '성질이나 상태를 나타내요.',
    examples: '크다 · 비싸다 · 깨끗하다 (1급)',
    note: "영어와 달리 'be' 없이 그대로 서술어가 되고, 동사처럼 활용해요 (비싸다 → 비싸요). 영어권 학생에게 짚어 줄 만한 점이에요.",
  },
  { name: '부사', what: '동사, 형용사 등을 꾸며서 정도나 방법을 더해요.', examples: '아주 · 빨리 · 같이 (1급)', note: '' },
  {
    name: '관형사',
    what: '명사 앞에서 명사를 꾸며요. 모양이 바뀌지 않아요.',
    examples: '그 · 다른 · 두 · 몇 (1급)',
    note: "'새'(관형사, 2급)와 '새로운'(형용사 새롭다 + -ㄴ, 2급)처럼 뜻이 비슷해도 품사가 다를 수 있어요.",
  },
  { name: '감탄사', what: '느낌, 부름, 대답을 나타내요.', examples: '네 · 아니요 · 여보세요 · 글쎄요 (1급)', note: '' },
  {
    name: '접사',
    what: '단어 앞이나 뒤에 붙어 새 단어를 만들어요. 혼자 쓰이지 않아요.',
    examples: '-하다 (건강하다) · -되다 (2급), -님 (선생님) · 불- (불가능) (3급)',
    note: '',
  },
  { name: '줄어든말', what: '두 말을 줄여서 쓴 형태예요.', examples: '걔 (그 아이) · 얘 · 쟤 · 제 (저의) (3급)', note: '목록 전체에 9개뿐이에요.' },
]
</script>

<template>
  <div class="space-y-4">
    <section class="guide">
      <h2>먼저 알아 둘 것</h2>
      <ul>
        <li>이 목록은 국립국어원 「국제 통용 한국어 표준 교육과정 적용 연구(4단계)」(2017)의 <b>등급 목록</b>이에요. 1~6급으로 나뉘어요.</li>
        <li>
          <b>"표준 N급"은 TOPIK 급수와 같은 6단계라 거의 맞물리지만, 공식적으로 같은 기준은 아니에요.</b> 학생에게는 "1급 수준"처럼 말하고 "TOPIK 1급"이라고 단정하지 않는 게 안전해요.
        </li>
        <li>분류와 품사 이름은 원본 엑셀 그대로이고, 아래 예시는 그 목록에서 실제로 고른 거예요 (괄호 안은 등급).</li>
        <li>
          단어 옆 작은 숫자는 <b>동음이의어 번호</b>예요. 같은 글자가 목록에 여러 번 있을 때만 보여요 (예: 장 — 한 장 2급 / 장을 담그다 5급). 뜻은 길잡이말 칸을 보면 돼요.
        </li>
      </ul>
    </section>

    <section class="guide">
      <h2>문법·표현의 분류</h2>
      <p class="lead">
        <b>형태 기준</b>이에요 (학교문법의 조사·어미 구분 + 덩어리 "표현"). "이유", "추측" 같은 <b>기능 기준이 아니라서</b>, 이유를 나타내는 -어서(연결어미)와 -기 때문에(표현)가
        서로 다른 분류에 들어가요. 기능은 표의 "의미" 칸에 일부만 적혀 있어요.
      </p>
      <table>
        <thead><tr><th>분류</th><th>무엇인가</th><th>예</th></tr></thead>
        <tbody>
          <tr v-for="g in GRAMMAR" :key="g.name">
            <th>{{ g.name }}</th>
            <td>{{ g.what }}<div v-if="g.note" class="note">{{ g.note }}</div></td>
            <td class="ex">{{ g.examples }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="guide">
      <h2>어휘의 품사</h2>
      <p class="lead">
        원본에는 <b>"부사/명사"(내일, 그저께), "관형사/대명사"(그)</b>처럼 품사가 둘인 단어가 있어요. 품사 필터에서는 이런 단어를 양쪽에 다 세서, 품사별 개수를 다 더하면 전체보다 커요.
      </p>
      <table>
        <thead><tr><th>품사</th><th>무엇인가</th><th>예</th></tr></thead>
        <tbody>
          <tr v-for="p in POS" :key="p.name">
            <th>{{ p.name }}</th>
            <td>{{ p.what }}<div v-if="p.note" class="note">{{ p.note }}</div></td>
            <td class="ex">{{ p.examples }}</td>
          </tr>
        </tbody>
      </table>
    </section>
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
  margin: 0 0 0.6rem;
  font-size: 1rem;
  font-weight: 700;
}
.guide ul {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.9rem;
  line-height: 1.6;
}
.lead {
  margin: 0 0 0.75rem;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--p-surface-700);
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
  width: 6.5rem;
}
.ex {
  width: 38%;
  color: var(--p-surface-700);
}
.note {
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: var(--p-surface-500);
}
@media (max-width: 640px) {
  .ex {
    width: auto;
  }
}
</style>
