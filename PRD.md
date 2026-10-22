# PRD: 한국어 선생님을 위한 학생 학습관리 AI (가칭)

- 작성일: 2026-10-19 · 작성자: 박소미
- 상태: v1.7 (2026-10-21 과별 데이터를 자료에서 자동 생성(단원 시트, 검수 전 표시)·진도와 약점을 표준 항목 ID로 — 기획 ADR-0030, 기술 ADR-0032. 이전 v1.6: 2026-10-21 녹취록에서 항목별 이해도를 판정해 다음 수업 복습에 반영, 녹취록 3만 자 — 기획 ADR-0029, 기술 ADR-0033. 이전 v1.5: 2026-10-21 출처 옆 "원문"으로 원본 PDF 바로 열기 — 기획 ADR-0027, 기술 ADR-0030. 이전 v1.4: 2026-10-21 상단 메뉴 학생/수업 준비 분리·브리핑 먼저 — 기술 ADR-0029, 녹취록 .txt 올리기 — 기획 ADR-0026. 이전 v1.3: 2026-10-21 교재 근거 문법 질문 챗봇 P0 — 기획 ADR-0024, 기술 ADR-0024. 이전 v1.2: 2026-10-20 기획 재검토 반영: 교재 범위·개인화·PPT 제외·페르소나별 중심 교재·표준 등급 기준·예문 출처 — 기획 ADR 0013~0020, 기술 ADR 0013~0018)
- 마감: 2026-10-22(목) 캡스톤 제출
- 기반 코드: `korean-ppt-ai-agent` (수업 자료 생성 LangGraph 에이전트)를 "수업 준비" 모듈로 흡수해서 확장

---

## 1. 한 줄 요약

Preply·AmazingTalker에서 1:1로 한국어를 가르치는 한국인 선생님이 **학생마다 목표를 기준으로 수업을 준비하고, 수업이 끝난 뒤 기록·피드백·숙제를 정리하는 일**을 AI가 대신 초안으로 만들어 주는 **선생님 전용** 웹 서비스.
가르친 경험이 많지 않은 선생님도 "이 학생에게 무엇을, 어떻게 설명해야 하는가"를 세종학당 공식 교원용 지침서를 근거로 바로 알 수 있게 하는 것이 목표다.

**핵심 메시지: "학생이 떠나지 않게 하는 맞춤 수업 + 성장 기록"** ([기획 ADR-0020](docs/planning-adr/0020-primary-metric-draft-quality.md)). 수업료가 내려가고 학생 모집이 어려워진 시장에서 학생 유지가 곧 수입이다. 준비 시간 단축은 그 결과로 따라오는 보조 효과로 본다.

## 2. 배경과 문제 정의

예전에 일본인 학생에게 한국어를 가르친 경험에서 나온 문제다.

| # | 문제 | 지금 어떻게 하고 있나 | 왜 힘든가 |
|---|---|---|---|
| P1 | **수업 준비에 시간이 많이 든다** | 교재를 보고 PPT·설명·예문을 직접 만들고, 가르칠 문법을 따로 공부한다 | 학생마다 모국어·수준·목표가 달라 자료를 매번 새로 만든다. 경험이 적으면 "이 문법을 어떻게 설명하지?"를 공부하는 데도 시간이 든다 |
| P2 | **수업 후 정리가 귀찮다** | 수업 노트, 학생 피드백, 숙제를 따로 메모한다 (하거나 안 하거나) | 정리를 미루면 다음 수업 때 무엇을 배웠고 어디가 약했는지 기억나지 않는다 → P1이 더 심해진다 |

P1은 다시 둘로 나뉜다 ([기획 ADR-0014](docs/planning-adr/0014-personalization-scope.md), [기획 ADR-0016](docs/planning-adr/0016-persona-anchor-textbook-standard-levels.md)이 이어 감).
- **P1-A. 내용 익히기**: 이 과의 목표, 수업 절차, 문법의 공식 설명. 학생이 누구든 같다 → 세종학당 **교원용 지침서**가 이미 답을 갖고 있다. 서비스는 찾아서 보여 주고 출처를 붙인다 (RAG).
- **P1-B. 설명하기**: 이 문법을 **이 학생에게** 어떻게 설명할지 (모국어, 수준, 관심사, 문화·맥락). 서비스의 핵심 가치는 여기다.

현장 튜터들의 글(2026년 9~10월 Threads)에서도 같은 문제가 보인다. 튜터가 크게 늘고 50분 수업 단가가 4달러까지 내려가면서, 학생은 "설명을 잘하는지", "나를 기억하는지"로 튜터를 고르고 아니면 2~3회 만에 떠난다("한국인이라고 한국어를 잘 가르치는 건 아니다"). 그런데 수업 준비까지 하면 시간 대비 보수가 너무 적다. (통계가 아닌 일화로만 쓴다.)

**P1과 P2는 하나의 고리다.** 수업 후 기록이 잘 쌓여야 다음 수업 준비가 빨라지고 개인화된다.
그래서 이 서비스는 이 고리를 끊기지 않게 하는 데 집중한다.

```
학생 등록(목표·수준) → 수업 준비(자료 + 선생님 브리핑) → 수업 → 수업 후 기록 → 프로필 갱신 ─┐
        ▲                                                                                 │
        └─────────────────────────────── 다음 수업 준비 ◀────────────────────────────────┘
```

## 3. 대상 사용자

### 주 페르소나: 초보 온라인 한국어 선생님 (= 나)
- Preply / AmazingTalker에서 1:1 수업을 하는 한국인
- 학생: 일본어권·영어권 초급 학습자 3~10명
- 교재: 학생의 학습 목적(페르소나)에 따라 세종학당 교재 중 하나를 중심 교재로 쓴다 (체계·TOPIK → 세종학당 한국어 1~6([기획 ADR-0022](docs/planning-adr/0022-structured-persona-uses-sejong-korean-1-6.md)), 일상 회화 → 실용 한국어, 여행 → 여행 한국어, 업무 → 비즈니스 한국어). 지금 과별 데이터(단원 시트)가 있는 교재는 「세종학당 한국어」 1·2 (각 20과, 지침서에서)와 3A~6B (각 10과, 본책에서 — [기술 ADR-0040](docs/adr/0040-unit-sheets-from-textbook-3a-6b.md))다. 자동으로 만든 초안이고 1권 2~4과만 검수됐다 ([기획 ADR-0016](docs/planning-adr/0016-persona-anchor-textbook-standard-levels.md), [기획 ADR-0030](docs/planning-adr/0030-unit-sheets-from-materials.md))
- 공통 기준: 국립국어원 「국제 통용 한국어 표준 교육과정」 어휘·문법 등급 목록 (1~6급). 학생 수준, 진척도, 예문 수준을 이 기준으로 잰다
- 참고 자료: 교원용 지침서, 어휘와 문법 핸드북(영어판 1권, **일본어판 1·2권**: 문법마다 일본어 설명) 등 세종학당 공개 자료 ([기획 ADR-0013](docs/planning-adr/0013-sejong-public-materials.md), [0024](docs/planning-adr/0024-grammar-qa-chat-p0.md))
- 한국어 교육 경력이 길지 않아 문법 설명 방법, 학습자가 자주 틀리는 지점을 미리 공부해야 한다
- 예약·결제·화상수업은 플랫폼을 쓴다. **이 서비스는 플랫폼 밖에서 쓰는 선생님용 작업 도구**다

### 이용 범위
- **선생님만 쓴다.** 학생은 서비스에 접속하지 않는다. 학생에게 줄 결과물(피드백 메시지, 수업 자료)은 선생님이 확인한 뒤 플랫폼 메시지 등으로 직접 전달한다.
- 첫 사용자는 나 자신이다. 실제로 수업할 학생 몇 명의 정보를 **가상 데이터로 바꿔서** 사용한다.

## 4. 목표와 비목표

### 목표 (이번 마감까지)
1. 선생님이 학생을 등록하고(수동 입력 또는 자연어 → AI 채움) 대시보드에서 관리할 수 있다.
2. 학생의 목표·약점·지난 수업 기록을 바탕으로 **15장 슬라이드 구성안**(학생 화면 문구 + 교사 노트)과 **지침서 근거의 선생님 브리핑**을 만들 수 있다. PPT는 만들지 않는다 ([기획 ADR-0015](docs/planning-adr/0015-no-ppt-fixed-lesson-frame.md), [기획 ADR-0032](docs/planning-adr/0032-slide-plan-from-reference.md)).
3. 수업 후 짧은 메모만 쓰면 AI가 수업 기록·약점 갱신·숙제·학생 피드백 메시지 초안을 만들고, 선생님이 승인하면 프로필에 반영된다.
4. 대시보드 GUI와 채팅 둘 다로 위 기능을 쓸 수 있다.
5. **AI 초안을 그대로 승인한 비율(주 지표)**과 수업 준비·정리 시간(보조 지표)을 서비스가 직접 측정한다.

### 비목표 (이번에는 안 한다)
- 학생용 화면·로그인 (학생 포털, 숙제 제출, 단어 복습 앱). 레벨테스트 학생 화면은 선생님이 화면 공유로 보여 주는 창일 뿐, 학생이 접속하지 않는다 ([기획 ADR-0021](docs/planning-adr/0021-student-screen-level-test-saved-result.md))
- 예약·일정·결제·수익 모델 (플랫폼이 이미 제공)
- 「세종학당 한국어」 1~6B 외 교재(실용·여행·비즈니스 한국어 등)의 과별 진도 데이터 → 다음 단계 (결정은 [기획 ADR-0016](docs/planning-adr/0016-persona-anchor-textbook-standard-levels.md). 학습 목적 칸은 있지만 어떤 목적이든 진도는 「세종학당 한국어」 순서를 따른다)
- 선생님 자체 교재 업로드 → 확장 단계
- PPT·PDF 수업 자료 생성 → 하지 않는다 (내용만 내놓고, 선생님이 자기 자료에 붙여 넣는다)
- 일본어·영어 외 설명 언어 (예: 중국어 번체) → 확장 단계
- 실제 개인정보 처리 (실명·녹음 보관, 동의 절차) → MVP는 **가상 데이터만**
- 여러 선생님 계정·인증 (단일 사용자 로컬 서비스)

## 5. 핵심 사용자 시나리오

**S1. 새 학생 등록**
> 체험수업이 끝나고 채팅창에 "일본인 대학생 유이, 한글은 읽음, 드라마 좋아하고 내년에 서울 여행 가고 싶대. 받침 발음이 약함"이라고 쓴다.
> AI가 학생 카드(모국어 ja, 수준 세부 메모, 학습 목적 추천, 목표, 관심사, 약점 메모)를 채운 초안을 보여 준다. 메모에 등급이 없으므로 **현재 수준은 비어 있고**, 선생님이 체험수업 레벨테스트 결과로 고른다. 선생님은 틀린 칸을 고치고 **저장**을 누른다.
>
> (체험수업 중) [레벨테스트] 화면에서 [학생 화면 열기]로 새 창을 열어 화상수업에서 그 창만 공유한다. 한글 읽기 → 1급 → 2급 순서로 문항을 누르면 학생 창에 크게 뜨고, 맞음/틀림을 누르면 다음 문항으로 넘어간다. 오른쪽에 "표준 2급 — 2급 4/12개, 이 등급을 배울 차례"처럼 추천이 바로 바뀐다. [결과 저장]을 누르면 결과가 남고 학생 창은 "수고했어요"로 바뀐다. 결과 카드에서 등급을 확인하고 [새 학생으로 등록]을 누르면 등록 화면에 등급·날짜·관찰 메모가 채워진다 ([기획 ADR-0018](docs/planning-adr/0018-level-from-trial-test-persona-by-teacher.md), [0021](docs/planning-adr/0021-student-screen-level-test-saved-result.md)).

**S2. 다음 수업 준비**
> 상단 [수업 준비] 탭에서 다음 수업 순으로 놓인 학생 카드 중 유이 카드의 [수업 준비]를 누른다 (유이의 학생 화면에서 [다음 수업 준비]를 눌러도 같다). 결과 화면 맨 위에 유이 요약(일본어 · 표준 1급 · 약점)과 **선생님 브리핑**이 먼저 나오고, 그 아래에 AI가 **15장 슬라이드 구성안**(수업 목표·최종 미션, 안부 4 → 복습 3 → 목표와 대화 3 → 어휘 6 → 표현 6 → 연습 10 → 역할극 12 → 문장 고치기 3 → 마무리와 숙제 3분. 장마다 학생 화면 문구와 교사 노트)과 복습/새 어휘/새 문법/숙제 4개 범주를 보여 준다 ([기술 ADR-0029](docs/adr/0029-nav-student-prep-tabs.md)). 브리핑에는 "지침서 근거의 문법 설명 포인트(출처 쪽수), 일본어 화자가 자주 틀리는 점, 예상 질문과 답, 드라마를 소재로 한 워밍업 질문, 서울 여행 상황의 활용 활동"이 들어 있다.
> 선생님은 범주별로 승인·직접 수정·피드백을 한다. 모두 승인하면 수업안이 확정되고, [글로 복사]로 자기 수업 자료에 붙여 넣는다.

**S3. 수업 후 정리**
> 수업이 끝나고 "3과 1~10 단어 함. '-습니다' 잘함. '을/를' 받침 구분 계속 틀림. 숙제는 연습문제 2번"이라고 메모를 쓴다. 수업 녹음을 받아쓰기 앱으로 텍스트로 바꿔 두었다면 [녹취록 파일 불러오기 (.txt)]로 그 파일을 올려도 된다 ([기획 ADR-0026](docs/planning-adr/0026-transcript-text-upload.md)).
> AI가 ① 이번 수업에서 다룬 교재 항목 ID ② 잘한 점·틀린 점 ③ 약점 목록 변경안 ④ 숙제 ⑤ 학생에게 보낼 일본어 피드백 메시지 초안을 만든다.
> 선생님이 항목별로 확인하고 승인하면 학생 프로필과 수업 이력에 반영된다. 메시지는 복사해서 플랫폼으로 보낸다.

**S5. 진도·향상 리포트** ([기획 ADR-0019](docs/planning-adr/0019-progress-report-for-retention.md))
> 한 달이 지나 유이 화면에서 [진도 리포트]를 누른다. "수업 4회, 새 문법 3개·단어 15개, 극복한 것: 이/가 구분, 다음에 연습할 것: 을/를 받침" 같은 숫자와, 표준 1급 문법·어휘를 얼마나 배웠는지가 보인다.
> 아래에 학생에게 보낼 일본어 메시지 초안이 있다. 잘한 점을 일본어로 고친 뒤 복사해서 플랫폼으로 보낸다.

**S4. 채팅으로 조회와 작업 요청**
> "유이 요즘 약한 거 뭐야?" → 프로필을 보고 바로 답한다.
> "Jay 다음 수업 30분으로 준비해줘" → S2 흐름을 실행하고 진행 상황을 단계별로 보여 준다.

## 6. 기능 요구사항

우선순위: **P0 = 목요일 제출에 반드시 포함**, P1 = 시간이 되면, P2 = 확장 단계

### F1. 학생 관리 (P0)
| ID | 요구사항 | 우선 |
|---|---|---|
| F1-1 | 학생 엔티티(7장)를 폼으로 직접 입력·수정·삭제 | P0 |
| F1-2 | 자연어 설명 → AI가 엔티티 칸을 채운 초안 생성 → **선생님 확인 후 저장 (HITL)** | P0 |
| F1-3 | 정형 칸 외에 자유 메모 칸 제공 (성격, 수업 스타일 선호 등 아무거나) | P0 |
| F1-4 | 약점은 교재 항목 ID(예: `u03-g02`)와 자유 서술을 둘 다 받는다 | P0 |
| F1-5 | 기존 학생 정보에 자연어로 추가·수정 ("유이 이번 달부터 주 2회로 늘림") → 변경 내용(diff)을 보여 주고 승인 | P1 |
| F1-6 | **현재 수준(표준 등급, 0=입문~6급)은 필수**, 레벨테스트 날짜·세부 메모와 함께 적는다. AI는 메모에 등급이 분명할 때만 채운다 ([기획 ADR-0018](docs/planning-adr/0018-level-from-trial-test-persona-by-teacher.md)) | P0 (완료) |
| F1-7 | 학습 목적(체계·TOPIK / 일상 회화 / 여행 / 업무)과 목표 수준은 선생님이 고른다. AI는 자연어 등록 때 학습 목적 추천만, 중심 교재는 코드가 정한다 ([기획 ADR-0016](docs/planning-adr/0016-persona-anchor-textbook-standard-levels.md), [0018](docs/planning-adr/0018-level-from-trial-test-persona-by-teacher.md)) | P0 (완료, 진도 데이터는 「한국어 1」만) |
| F1-8 | **체험수업 레벨테스트**: 한글 읽기 + 1~6급 문법 질문·어휘 (표준 항목에 묶임), 맞음/틀림 → 코드 판정으로 추천 등급. 문항은 Claude 초안, 검수 필요 | P0 (완료) |
| F1-9 | 레벨테스트 **학생 화면**: 화면 공유용 별도 창에 지금 문항과 안내(한국어 + 영어/일본어)만 보인다. 예시 답·판정은 숨긴다 ([기획 ADR-0021](docs/planning-adr/0021-student-screen-level-test-saved-result.md)) | P0 (완료) |
| F1-10 | 레벨테스트 **결과 저장**: 저장할 때 코드가 등급을 판정해 남기고, 선생님이 확인하면 새 학생 등록 또는 기존 학생 카드에 반영. 확인 대기는 대시보드 할 일에 뜬다 ([기획 ADR-0021](docs/planning-adr/0021-student-screen-level-test-saved-result.md)) | P0 (완료) |

### F2. 표준 등급 기준과 학습 방향 ([기획 ADR-0016](docs/planning-adr/0016-persona-anchor-textbook-standard-levels.md))
| ID | 요구사항 | 우선 |
|---|---|---|
| F2-0 | 국립국어원 표준 교육과정 등급 목록(문법 336, 어휘 10,635, 1~6급)을 데이터로 두고, 교재 항목을 표준 항목에 잇는다 (대응표) | P0 (완료: 등급 목록, 「한국어」 1~6B 단원 시트의 문법·어휘 대응 — 기술 ADR-0036·0040) |
| F2-1 | 학생 진척도: 배운 교재 항목 → 표준 항목 → "표준 1급 문법 45개 중 N개" | P1 |
| F2-2 | 목표 등급까지 남은 문법·어휘 목록과, 중심 교재에서 그 항목이 나오는 과 | P1 |
| F2-5 | 상단 메뉴 [커리큘럼·페르소나]의 두 탭에 온라인 세종학당 커리큘럼(입문 → 초급 1·2급 → 중급 3·4급 → 고급 5·6급, 특별 과정)과 페르소나별 중심 교재·해당 학생을 보여 준다 | P0 (완료) |
| F2-4 | 등급 목록 찾아보기: 문법·어휘를 등급·문법 분류(원본의 형태 기준: 조사·어미·표현)·품사·검색어로 걸러 보고, 문법마다 이어진 교재 과를 보여 준다 (선생님 공부용 체크리스트) | P0 (완료) |
| F2-3 | **학습 계획**: 목표(문장·목표 등급·기한 선택) + 경로(책·과 순서, 기본은 중심 교재 순서, 선생님이 빼기·회차 더하기·교재 바꾸기) + 속도 + 위치. 기한이 있으면 계획 대비 진도를 코드가 계산한다. 수업 기록 승인 때 이해도·표준 ID 진도로 "천천히 / 빨리 / 계획 다시 보기"를 코드가 제안하고 선생님이 승인한다. 수업 준비 탭 카드에 상태 배지. AI가 경로를 짜지 않는다 ([기획 ADR-0031](docs/planning-adr/0031-learning-plan-and-pace-suggestions.md)) | P1 (단원 시트 "책 + 과" 전환 뒤) |

> 커리큘럼 순서는 새로 짜지 않는다. 중심 교재의 과 순서를 따르고, 등급 목록은 잴 때만 쓴다.
> 화면에는 "표준 N급"으로 쓴다. TOPIK 급수와 거의 맞물리지만 공식적으로 같은 기준은 아니다.

### F3. 수업 준비 (P0, 기존 에이전트 확장)
| ID | 요구사항 | 우선 |
|---|---|---|
| F3-1 | 그래프(구성안(코드 규칙) → 개인화 설명 → 대본 → 자동 검토 → 브리핑 → 선생님 검토)를 API로 실행 | P0 |
| F3-1b | **단원 시트**: 교재·과마다 가르칠 문법·어휘·예문을 색인된 지침서에서 코드 규칙으로 뽑는다 (초안 = "검수 전" 표시, 선생님 확인 = 검수됨). 수업 준비 화면은 시트가 있는 과만 고를 수 있다 ([기획 ADR-0030](docs/planning-adr/0030-unit-sheets-from-materials.md), [ADR-0032](docs/adr/0032-unit-sheets-and-standard-ids.md)) | P0 (완료: 「한국어」 1·2 각 20과, 3A~6B 각 10과(본책에서, 기술 ADR-0040). 3A~6B 대화는 아직) |
| F3-2 | **선생님 브리핑**: 교원용 지침서에서 이번 과의 학습 목표·문법 구역을 가져와(RAG 필터 경로) 문법 설명 포인트를 만들고 **출처(책·쪽)**를 붙인다. 모국어 화자가 자주 틀리는 점, 예상 질문과 답, 설명 팁은 **문법×모국어 검수 데이터**(`l1_notes.json`, Claude 초안 + 선생님 검수)에서 꺼내고, 데이터에 없는 문법만 LLM이 만든다 ([ADR-0022](docs/adr/0022-l1-notes-data.md)). 워밍업 질문, 활용 활동, 맞춤 팁은 작은 LLM 호출로 만든다 | P0 |
| F3-2a | **15장 슬라이드 구성안**: 번호·단계·시간은 코드에 고정(수업 길이에 비례 조정), 학생 화면 문구와 교사 노트 7칸(목표·진행·질문/답·어려워하면·잘하면·출처)은 LLM 한 번. 장마다 수업에서 그대로 읽을 **대본**(한국어 발화 + 모국어 보조, 학생 예상 답, 어려워할 때 바꿔 말하기)을 이어서 만든다 ([기획 ADR-0033](docs/planning-adr/0033-per-slide-teaching-script.md), [기술 ADR-0035](docs/adr/0035-slide-script-node.md)). 교재에 없는 숙제 쪽수·음원은 "확인 필요" ([기획 ADR-0032](docs/planning-adr/0032-slide-plan-from-reference.md), [기술 ADR-0034](docs/adr/0034-slide-plan-node.md)) | P0 |
| F3-2b | **문화 포인트 (필수)**: 구성안 아래에 같이 보인다. 과 주제로 「세종한국문화 1」·지침서를 검색해 후보 2~3개(출처 쪽수 포함), LLM이 원문 안에서 요약 + 학생 나라 비교 질문(단정하지 않고 묻기). 선생님이 후보를 고른다. 못 찾으면 "선생님이 채워 주세요" ([기획 ADR-0023](docs/planning-adr/0023-culture-point-from-sejong-materials.md)) | P0 |
| F3-3 | 범주별 승인 / 직접 수정 / 피드백 (기존 HITL을 GUI로 옮김) | P0 |
| F3-4 | 확정한 수업안(15장 구성안 + 브리핑)을 학생별로 보관하고, 글로 복사할 수 있다. PPT/PDF는 만들지 않는다 | P0 |
| F3-6 | 채팅 질문("을/를 헷갈리는 학생 연습 방법")에 교수 자료 의미 검색(Parent-Child)으로 근거를 붙인다. 문법 비교 질문은 F6-4가 맡는다 | P1 |
| F3-7 | **원문 바로 열기**: 브리핑 근거 자료·문화 포인트 출처·문법 질문 교재 근거 옆의 "원문" 버튼을 누르면 선생님 컴퓨터의 원본 PDF가 출처 쪽으로 열린다 (인쇄 쪽→PDF 쪽은 코드가 바꾼다). PDF 위치는 폴더 스캔으로 한 번 등록한다 ([기획 ADR-0027](docs/planning-adr/0027-open-source-pdf.md), [ADR-0030](docs/adr/0030-local-pdf-open-via-ai-server.md)) | P1 |
| F3-5 | **예문은 만들지 않고 찾는다**: 교재·세종학당 공개 자료에서 예문을 찾고(RAG), 학생 등급을 넘는 단어가 있는 예문은 이유를 붙여 접어 두고, 관심사에 맞는 예문을 앞에 둔다 ([기획 ADR-0017](docs/planning-adr/0017-examples-from-materials-not-generated.md)). 등급 판정 함수는 완료, 설명 노드 연결은 다음 단계 | P1 |

### F4. 수업 후 기록 (P0)
| ID | 요구사항 | 우선 |
|---|---|---|
| F4-1 | 수업 후 자유 형식 텍스트 메모 입력. 녹취록 텍스트 파일(.txt)을 불러와 메모 칸에 넣을 수 있다 (30,000자까지 — 50분 녹취 전체, STT는 서비스 밖, [기획 ADR-0026](docs/planning-adr/0026-transcript-text-upload.md), [0029](docs/planning-adr/0029-understanding-from-transcript-drives-review.md)) | P0 |
| F4-2 | AI가 메모를 구조화: 다룬 교재 항목 ID, 잘한 점, 오류(학생 발화 → 교정, 관련 항목 ID), 약점 추가·해제안, 숙제, 다음 수업 메모 | P0 |
| F4-3 | 학생에게 보낼 피드백 메시지 초안을 학생 언어(ja/en)로 생성 + 한국어 번역 병기 | P0 |
| F4-4 | **항목별 승인 후에만** 프로필·수업 이력에 반영 (HITL). 반영 전에는 "미처리 기록"으로 남는다 | P0 |
| F4-8 | **항목별 이해도 → 다음 수업 복습**: 다룬 항목마다 AI가 메모·녹취록에서 학생 반응 장면(틀림·다시 물어봄·망설임·다시 설명함·스스로 고침·바로 맞힘)을 원문 인용과 함께 찾고, 코드가 장면 점수로 헷갈림 / 조금 헷갈림 / 괜찮음을 정한다. 원문에 없는 인용은 버린다. 선생님이 확인·수정해 승인하면, 다음 수업 복습이 헷갈림 → 조금 헷갈림 → 약점 → 직전 수업 항목 순서가 되고 헷갈림이 있으면 복습 시간이 두 배가 된다 ([기획 ADR-0029](docs/planning-adr/0029-understanding-from-transcript-drives-review.md), [ADR-0033](docs/adr/0033-observe-judge-understanding.md)) | P0 |
| F4-5 | 수업 준비 때 만든 구성안을 기본값으로 불러와 "계획 대비 실제로 한 것"만 고치게 한다 | P1 |
| F4-6 | 음성 메모 입력 (브라우저 녹음 → STT) | P1 |
| F4-7 | 수업 녹화·녹음 오디오 파일 업로드 → 서버 STT → 분석 (녹취 텍스트는 F4-1로 받는다) | P2 |

### F5. 대시보드 (P0)
| ID | 요구사항 | 우선 |
|---|---|---|
| F5-1 | 학생 목록 카드: 이름, 모국어, 수준, 다음 과, 마지막 수업일, 주요 약점. 상단 메뉴 [학생](이름 검색, 상태·모국어·학습 목적 필터)에 같은 카드를 쓴다 | P0 (완료) |
| F5-2 | 학생 상세: 프로필, 수업 이력 타임라인, 약점 변화, 만든 자료 | P0 |
| F5-3 | 대시보드는 **월간 수업 달력**: 칸마다 수업(학생 이름 + 준비 상태 색), 날짜를 누르면 그날 수업의 준비 체크와 지금 할 버튼 하나. 지난 수업은 기록 여부로 표시 ([기획 ADR-0034](docs/planning-adr/0034-dashboard-calendar.md)) | P0 (완료) |
| F5-4 | 시간 측정 요약 (F7) — 대시보드에서 빼고 [더보기 › 지표]에서 본다 ([기획 ADR-0034](docs/planning-adr/0034-dashboard-calendar.md)) | P0 |
| F5-5 | 상단 메뉴는 대시보드 · 학생 · 수업 준비 · 어휘·문법, 나머지는 [더보기] ([기술 ADR-0038](docs/adr/0038-nav-standard-tab.md)). [수업 준비] 탭은 학생 프로필 카드를 다음 수업 일정 순으로 보여 주고, 카드마다 상태에 맞는 버튼(수업 준비 / 이어서 준비 / 수업안 보기) 하나를 둔다 ([기술 ADR-0029](docs/adr/0029-nav-student-prep-tabs.md)) | P0 (완료) |
| F5-6 | **학습자별 진도·향상 리포트**: 기간별 수업 횟수, 새로 배운 문법·단어와 누적, 표준 등급별 배운 양(선생님용), 목표까지 남은 문법, 잘한 점, 해결한 약점, 반복 오류 상위 3개, 학생에게 보낼 메시지 초안(한국어 + 학생 언어, 템플릿). 숫자와 문장은 코드가 만든다 ([기획 ADR-0019](docs/planning-adr/0019-progress-report-for-retention.md)) | P0 (완료) |

### F6. 채팅 (P0)
| ID | 요구사항 | 우선 |
|---|---|---|
| F6-1 | **라우팅 게이트(저가 모델)**: 조회 질문 / 학생 등록·수정 / 수업 준비 / 수업 후 기록 / 문법 질문 / 일반 질문으로 분류 | P0 |
| F6-2 | 조회 질문은 DB를 읽어 바로 답한다 | P0 |
| F6-3 | 작업 요청은 해당 화면으로 연결하고, 그 화면에서 그래프를 실행하며 SSE로 진행 단계를 보여 준다 ([ADR-0010](docs/adr/0010-chat-work-requests-handoff.md)) | P0 |
| F6-4 | **교재 근거 문법 질문** ("-아서랑 -(으)니까 뭐가 달라?", "사는이랑 살던 차이", "너라면, 너라서, 너니까 차이"): 형태를 표준 문법 항목에 맞추고, 학생 모국어판 핸드북(설명 원문·예문·쪽수)·지침서·모국어 노트를 근거로 요점을 보여 준다. 학생을 지정하면 등급을 넘는 문법은 "아직 안 배움", 교재에 없는 문법은 AI가 한국어 설명·예문을 만들어 "AI 설명 · 검수 필요"로 따로 보여 준다([기획 ADR-0036](docs/planning-adr/0036-ai-explanation-when-no-textbook-evidence.md)). 학생용 일본어 설명은 만들지 않고 원문을 보여 준다 ([기획 ADR-0024](docs/planning-adr/0024-grammar-qa-chat-p0.md), [ADR-0024](docs/adr/0024-japanese-handbook-and-grammar-qa.md), 관련형은 대표형 교재 근거: [ADR-0037](docs/adr/0037-listed-conjugations-and-head-form-evidence.md), 답은 비교표 → 핵심 차이 → 접힌 근거: [ADR-0043](docs/adr/0043-grammar-answer-comparison-table.md)) | P0 |
| F6-5 | **AI 채팅 탭 + 대화 기록**: 주 메뉴의 AI 채팅 탭에서 대화 목록과 큰 대화 화면을 본다. 플로팅 창과 같은 대화를 쓰고, 답(글·근거 카드·이동 버튼)을 저장해 다시 연다. 제목은 첫 질문 앞 30자, 이름 바꾸기·삭제 ([기획 ADR-0035](docs/planning-adr/0035-chat-tab-history-and-language-toggle.md), [ADR-0041](docs/adr/0041-chat-history-in-postgres.md), [ADR-0042](docs/adr/0042-nav-chat-tab-shared-conversation.md)) | P0 |
| F6-6 | **설명 언어 토글** (자동 / 日本語 / English): 문법 질문은 그 언어판 근거를, 일반 질문은 답 끝에 학생에게 말해 줄 그 언어 설명을 붙인다. 자동은 학생 모국어, 학생이 없으면 일본어 ([기획 ADR-0035](docs/planning-adr/0035-chat-tab-history-and-language-toggle.md)) | P0 |

### F7. 시간 측정 (P0, 성공 지표용)
| ID | 요구사항 | 우선 |
|---|---|---|
| F7-1 | 수업 준비 세션: [준비 시작] 시점 ~ 모든 범주 승인(수업안 확정) 시점을 자동 기록 | P0 |
| F7-2 | 수업 후 정리 세션: 메모 입력 시작 ~ 기록 승인 완료 시점을 자동 기록 | P0 |
| F7-3 | 그중 AI 대기 시간과 선생님 작업 시간(검토·수정)을 나눠 기록 | P1 |
| F7-4 | AI 없이 했을 때의 기준 시간(baseline)을 선생님이 직접 입력 → 지표 화면에서 비교 | P0 |

## 7. 데이터 모델 (초안)

기존 `src/schemas.py`의 `StudentProfile`, `LessonRecord`를 확장한다. 단일 선생님 기준이라 Teacher 엔티티는 두지 않는다.

```
Student
  id, name(가명), native_language("ja"|"en"), level(텍스트: 수준 세부 메모)
  goals: list[str]                # 학생이 말한 목표
  interests: list[str]            # 찾은 예문의 정렬 기준 (드라마, 여행, K-pop …) — 예문을 만들지 않는다 (ADR-0017)
  standard_level: int             # 지금 배울 표준 등급 0(입문)~6. API 필수, DB는 기존 학생 때문에 nullable (ADR-0018)
  level_assessed_on: date | None  # 체험수업 레벨테스트 날짜
  persona: str | None             # 학습 목적 → 중심 교재 (ADR-0016, 0018)
  target_level: int | None        # 목표 표준 등급 1~6
  weaknesses: list[Weakness]      # 아래 참고
  next_unit: int
  lesson_minutes_default: int     # 기본 50
  notes: str                      # 자유 메모 (무엇이든)
  status: "active" | "paused"
  created_at, updated_at

Weakness
  item_id: str | None             # 항목 ID (있으면): 표준 ID std-g-007 / 표준에 없는 표현 ko1-u02-x01 (기술 ADR-0032)
  description: str                # 자유 서술 ("받침 발음")
  since_lesson_id, resolved: bool

Lesson                            # 수업 1회
  id, student_id, lesson_no, date, minutes, unit_no
  status: "planned" | "prepared" | "done" | "recorded"
  prep_thread_id                  # 수업 준비 그래프의 LangGraph thread
  plan: LessonPlan                # 승인된 구성안
  understanding: {item_id: "confused"|"shaky"|"ok"}  # 승인한 항목별 이해도 → 다음 수업 복습 순서 (ADR-0033)
  briefing: TeacherBriefing
  briefing.slide_plan            # 15장 슬라이드 구성안 + 장별 대본 slides[i].script (ADR-0034·0035, 별도 칼럼 없이 briefing JSON 안. 예전 수업은 lesson_frame 7단계)
  briefing.references            # 지침서 출처
  pptx_path, pdf_path             # (사용 안 함, 항상 null)

LessonRecord                      # 수업 후 기록 (Lesson 1:1)
  lesson_id, raw_note: str
  covered_item_ids: list[str]
  strengths: list[str]
  errors: list[{student_said, correction, item_id?, note}]
  weakness_changes: list[{action: "add"|"resolve", weakness}]
  homework: list[{item_id?, description}]
  next_lesson_note: str
  feedback_message: {target_lang_text, korean_text}
  approved_at: datetime | None    # None = 미처리

TimeLog
  id, student_id, lesson_id, kind: "prep" | "post"
  started_at, finished_at, ai_wait_seconds?, teacher_seconds?

Baseline
  kind: "prep" | "post", minutes: int, note

LevelTestResult                   # 저장한 레벨테스트 결과 (ADR-0021)
  id, answers: {문항 ID: bool}, score (판정 근거), suggested_level
  note, status: "pending" | "applied" | "dismissed"
  student_id?, applied_level?    # 선생님이 확인해 반영한 학생과 등급
  taken_at, decided_at?
```

- 과별 데이터(단원 시트 `ai-server/data/curriculum/<교재>/unit_NN.json`)는 ai-server 파일로 두고, 위 엔티티는 DB에 저장한다. 손으로 만든 `data/textbook/*.json`(「한국어 1」 2~4과)은 검수된 시트로 바뀌었고 이제 수업 준비가 읽지 않는다.
- 규칙(기존 설계 원칙 유지): **교재 원문은 바꾸지 않고 ID로만 참조**한다. 예문은 자료에서 찾고, 선생님이 요청해서 AI가 만든 예문만 `is_new: true`로 표시한다 ([기획 ADR-0017](docs/planning-adr/0017-examples-from-materials-not-generated.md)).
- 표준 등급 목록(`ai-server/data/standard/grammar.json`, `vocab.json`)과 교재 → 표준 대응표(`textbook_map.json`)는 ai-server가 가진 파일 데이터다. 약점·배운 항목 `item_id`는 2026-10-21에 표준 ID로 옮겼다 (Flyway V6, [기술 ADR-0032](docs/adr/0032-unit-sheets-and-standard-ids.md)). 교재가 바뀌어도 진도가 이어진다.

## 8. 에이전트 설계

### 8-1. 그래프 구성
> 구현 결과: router는 Spring AI, student_intake는 그래프 없이 함수 두 개, post_lesson은 interrupt 없이 그래프 밖에서 승인한다 ([ADR-0009](docs/adr/0009-graph-split-and-hitl-location.md)).

| 그래프 | 흐름 | HITL 지점 |
|---|---|---|
| `router` | 입력 → 분류(저가 모델, 구조화 출력) → 해당 핸들러 | – |
| `student_intake` | 자연어 → 엔티티 추출 → **코드 검증**(언어 값, 항목 ID가 실제로 있는지) → 선생님 확인 → 저장 | 저장 전 |
| `lesson_prep` | load → plan(코드) → explain → script → auto_review(1회, 참고) → **briefing**(지침서 근거 + LLM 3호출) → **write_slides**(15장 구성안, LLM 1호출) → **write_slide_scripts**(장별 대본, LLM 15호출) → human_review → END (승인 때 초안이 달라졌으면 write_slides·write_slide_scripts 한 번 더) | 범주별 검토 + 브리핑 확인 |
| `grammar_qa` | 그래프 없이 함수: 형태 뽑기(코드, 못 찾으면 저가 모델 → 코드 검증) → 근거(핸드북 필터 경로 + 모국어 노트 + 지침서 의미 검색) → 등급 확인(코드) → 요점(LLM 1회) → 근거에 없는 예문 거르기(코드) | – (읽기만) |
| `post_lesson` | 메모 + 수업 계획 → 구조화 추출 → **코드 검증**(ID 존재, 약점 변경이 기존 약점과 맞는지) → 피드백 메시지 작성 → Validator → 선생님 검토 → DB 반영 | 반영 전 (항목별) |

### 8-2. 참고노트에서 가져오는 패턴
- **정형화 우선** ([ADR-0013](docs/adr/0013-process-over-model.md)): 정답이 있는 건 코드(구성안, 시간 배분, 수업 틀, 출처), 지식은 자료(지침서 RAG), LLM은 작은 칸만 채운다. 로컬 8B 모델로도 돌아가게 하는 것이 목표다.
- **라우팅 게이트 우선**: 단순 조회에 무거운 그래프를 돌리지 않는다.
- **권위 게이트**: LLM이 만든 교재 ID·약점 변경은 코드가 다시 검사한다. 없는 ID는 지우고 경고를 띄운다.
- **루프 상한**: Validator 재작성 최대 2회. auto_review는 다시 만들지 않는다 (코드 점검은 경고, LLM 점검은 참고 의견 — [ADR-0021](docs/adr/0021-auto-review-llm-advisory.md)).
- **Validator (LLM-as-Judge)**: 피드백 메시지를 관련성 / 완전성 / 명확성 / **학습자 수준 적합성** 4가지 기준으로 한 번에 평가한다.
- **모델 티어링**: 라우팅·추출 검증은 저가 모델(Haiku), 설명·대본·브리핑·메시지는 고품질 모델(Sonnet). `.env`로 교체. 2026-10-20부터 개발·데모·평가 모두 로컬 qwen3:8b 하나로 한다 ([ADR-0020](docs/adr/0020-local-model-for-demo-too.md)).
- **Checkpointer**: SQLite (`AsyncSqliteSaver`, lesson_prep만). HITL에서 멈췄다가 다시 이어 가려면 필요하다. 앱 데이터는 PostgreSQL ([ADR-0002](docs/adr/0002-app-database.md)).

### 8-3. HITL 원칙
> **AI는 DB에 직접 쓰지 않는다. 모든 쓰기는 선생님 승인을 거친다.**

학생 정보 저장, 약점 변경, 수업 이력 반영, 수업안 확정은 모두 "초안 → 선생님 확인(승인/수정/피드백) → 반영" 순서로 한다. 조회와 자료 미리보기만 승인 없이 한다.

## 9. 시스템 구성

```
Frontend (Vue 3 + Vite + TS + Pinia + PrimeVue + Tailwind)            :5173
  ├─ 대시보드: 월간 수업 달력 + 날짜별 준비 상태,  학생 상세: 프로필 · 약점 변화 · 수업 이력 · 자료
  ├─ 검토 화면: 수업안 범주별 검토(브리핑 포함), 수업 후 기록 항목별 승인, 학생 등록 초안 확인
  └─ 채팅 패널 (SSE)
        ⇅ REST + SSE (/api, 브라우저는 backend만 호출)
Backend (Spring Boot 4 + Spring AI 2, Java 21)                        :8080
  ├─ /api/students (CRUD), /api/students/intake (자연어 → 초안, 저장 안 함)
  ├─ /api/lessons/{id}/prep, /prep/review, /prep/state, /files/{pptx|pdf}(이전 수업만)
  ├─ /api/lessons/{id}/record, /record/approve (항목별 승인 → 프로필 반영)
  ├─ /api/dashboard/todos, /api/metrics/time, /api/baselines/{kind}, /api/traces (LangSmith 실행 기록 조회)
  ├─ /api/chat/stream (라우팅 게이트 Haiku → 조회 Tool Calling / 화면 연결 / 문법 질문 ai-server / 일반 답변 Sonnet)
  └─ PostgreSQL (Flyway) — DB를 읽고 쓰는 유일한 서비스 (ADR-0005)
        ⇅ REST + SSE (요청에 필요한 데이터를 담아 보냄)
AI server (FastAPI + LangGraph, lifespan에서 그래프 1회 생성)          :8000
  ├─ /intake, /prep/start, /prep/{thread}/resume, /prep/{thread}/state, /post-lesson, /grammar-qa, /files, /traces
  ├─ lesson_prep (interrupt + SQLite checkpointer), post_lesson, intake
  └─ 교수 자료 RAG (app/rag): Vision OCR(일본어판은 ko·ja 두 번 읽어 합침) → Parent-Child 청크(핸드북 문법 항목엔 표준 ID) → bge-m3 임베딩 → 파일 색인 data/rag/ (ADR-0014, 0024)
Observability: 구조화 JSON 로그 (student_id · lesson_id · thread_id 고정), LangSmith는 .env로 켬 → 앱 "AI 추적" 탭 (/api/traces, ADR-0028)
```

- 3계층으로 나눈 이유와 경계: [ADR-0001](docs/adr/0001-service-role-split.md), [ADR-0005](docs/adr/0005-data-access-ownership.md), [ADR-0006](docs/adr/0006-sse-proxy-path.md)
- 기존 `korean-ppt-ai-agent/src/`는 `ai-server/app/agent/lesson_prep/`으로 옮겼다 ([ADR-0004](docs/adr/0004-monorepo-layout.md)).

## 10. 성공 지표

주 지표는 [기획 ADR-0020](docs/planning-adr/0020-primary-metric-draft-quality.md)으로 바꿨다 (이전: 수업 준비 시간, [ADR-0010](docs/planning-adr/0010-success-metric-prep-time.md)). 승인 비율은 품질의 대리 지표라 시간과 함께 본다. 학생 지속 수강(리텐션)은 실제 학생 데이터가 쌓이면 다시 본다.

| 지표 | 측정 방법 | 목표 (가설) |
|---|---|---|
| **수업안 첫 검토 승인 비율** (주 지표) | 수업·범주마다 첫 검토 결정이 '승인'인 비율 (`review_decision`, `/api/metrics/quality`) | **70% 이상** |
| **수업 후 기록 초안 유지 비율** (주 지표) | AI 초안 항목 중 고치거나 빼지 않고 승인된 비율 (초안 vs 승인본 비교) | **80% 이상** |
| 수업 준비 시간 (보조) | F7-1 자동 측정 vs 기준 시간(F7-4) | 기준 대비 50% 이상 감소 |
| 수업 후 정리 시간 (보조) | F7-2 자동 측정 vs 기준 시간 | 5분 이내 |
| 수업 후 기록 추출 정확도 | 평가 데이터셋(아래)에서 항목 ID·약점 변경 일치율 | 80% 이상 |

**평가 데이터셋**: `ai-server/eval/dataset.json` (가상 메모 16개, 함정 케이스 포함). 실행: `cd ai-server && uv run python -m eval.run_eval`.
2026-10-19 첫 실행(검수 전 데이터): 항목 ID·약점 변경 일치율 **0.969**, 다룬 항목 F1 1.0, 숙제 1.0, 약점 변경 0.938.
원래 계획: 가상 수업 메모 15~20개와 기대 추출 결과를 직접 만든다. 휴리스틱(ID 일치) + LLM-judge(피드백 메시지 품질)로 채점하고, LangSmith Dataset으로 프롬프트를 바꾸기 전후를 비교한다.

**기준 시간 측정**: 제출 전에 AI 없이 3과 수업 1회를 직접 준비해 보고 걸린 시간을 기록한다. 시간이 없으면 과거 경험의 추정치를 쓰되 "추정"이라고 표시한다.

## 11. 일정 (2026-10-19 월 ~ 10-22 목)

| 날짜 | 할 일 | 완료 기준 |
|---|---|---|
| 10/19 (월) | PRD 확정, 데이터 모델 확정, ADR 2~3개 (프론트 스택, 저장소, 그래프 분리) | 이 문서 v1.0 |
| 10/20 (화) | 폴더 구조 재편, SQLite 모델 + 학생 CRUD API, `student_intake` 그래프, `lesson_prep` API화 + 브리핑 노드 | API로 학생 등록 → 수업 준비 → PPT까지 동작 |
| 10/21 (수) | `post_lesson` 그래프, 프론트 대시보드·검토 화면, 채팅(router + SSE) | 화면에서 S1~S3 시나리오 동작 |
| 10/22 (목) | 시간 측정(F7), 평가 데이터셋 + 테스트, 데모 시나리오 녹화, README, 제출 | 제출 |

**시간이 모자랄 때 빼는 순서**: F6-3 SSE 진행 표시 → 채팅의 작업 실행(조회만 남김) → F7-3 → LangSmith 평가 자동화 (수동 표로 대체)
**끝까지 지키는 것**: F1-1·F1-2, F3, F4-1~F4-4, F5-1·F5-3, F7-1·F7-2·F7-4

## 12. 리스크

| 리스크 | 대응 |
|---|---|
| 4일 안에 혼자 풀스택 구현 | P0 범위 고정, 빼는 순서를 미리 정해 둠. 프론트가 막히면 대체 스택 사용 (열린 질문 1) |
| LLM이 없는 교재 ID나 틀린 약점을 만든다 | 권위 게이트(코드 검증) + HITL |
| 자유 메모가 너무 짧거나 모호해서 추출이 부정확하다 | 수업 준비 구성안을 기본값으로 쓰고(F4-5), 모르는 부분은 비워 두게 프롬프트로 지시 |
| 피드백 메시지의 일본어·영어 품질 | Validator + 한국어 번역 병기로 선생님이 의미를 확인 |
| 일본어판 핸드북의 일본어 설명 안 한국어(「」)가 OCR로 깨진다 | 첫 번째는 항목 이름으로, 나머지는 「…」로 가리고 출처 쪽수를 보여 준다 ([ADR-0024](docs/adr/0024-japanese-handbook-and-grammar-qa.md)) |
| 문법 질문의 요점에 로컬 모델이 근거 없는 예문을 지어낸다 (2026-10-21 확인: "좋아니까") | 인용 예문이 근거에 없으면 코드가 그 요점을 빼서 "검수 필요"로 보여 준다 |
| OCR 오류·구역 경계 오인으로 지침서 근거가 틀린다 | 출처 쪽수를 함께 보여 줘 선생님이 원문을 확인. 표가 많은 쪽은 Claude 비전으로 다시 읽기 (ADR-0014 재검토 조건) |
| 모국어별 실수·예상 질문을 로컬 모델이 틀리게 만든다 (2026-10-20 qwen3:8b에서 확인) | 문법×모국어 검수 데이터로 바꿈 ([ADR-0022](docs/adr/0022-l1-notes-data.md)). 2~4과 7개 × ja/en 초안 작성, 일본어는 선생님 검수 필요. 데이터에 없는 문법만 LLM 생성 + "검수 필요" 표시 |
| 교재 저작권 | 저장소 공개 시 `data/textbook/` 제외 (기존 원칙 유지). 국립국어원 등급 목록은 공공누리 제1유형이라 출처를 적고 저장소에 둔다 |
| 교재 → 표준 대응이나 예문 등급 판정이 틀린다 (동음이의어, 목록에 없는 단어) | 대응표는 선생님 검수. 등급을 모르면 올리지 않고 `unknown`으로 보여 준다. 「한국어 1」 2~4과 예문 53개로 회귀 검사 (52개 1급) |

## 13. 열린 질문

1. ~~**프론트 스택**: React + Vite vs Streamlit~~ → **결정됨**: Vue 3 + Spring AI + FastAPI 3계층으로 변경 ([ADR-0001](docs/adr/0001-service-role-split.md), [ADR-0003](docs/adr/0003-frontend-stack.md))
2. **음성 메모(F4-6)를 P0로 올릴지**: 실제로 쓸 때는 수업 직후 말로 남기는 게 가장 편하다. 브라우저 Web Speech API면 반나절 정도 걸린다.
3. **숙제 채점**: 학생이 숙제를 플랫폼 메시지로 보내면 선생님이 붙여넣어 AI가 채점하는 기능을 넣을지 (현재 범위 밖)
4. **수업 시간 기본값**: 50분 고정 vs 학생별 설정 (데이터 모델에는 학생별로 넣어 둠)
5. **캡스톤 제출 형식**: 데모 영상, 발표 자료, 코드 저장소 중 필수 항목 확인 필요
