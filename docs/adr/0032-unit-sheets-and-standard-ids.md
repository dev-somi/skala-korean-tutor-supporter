# ADR-0032: 단원 시트 — 지침서에서 코드 규칙으로 뽑은 과별 데이터(draft/reviewed) + 문법·어휘 ID는 표준 ID
- 상태: Accepted (2026-10-21)
- 관련 모듈: `ai-server/app/curriculum/` (`schemas.py`, `sheets.py`, `extract.py`, `build.py`, `convert_textbook.py`, `evaluate.py`), `ai-server/data/curriculum/` (git 밖)
- 기획: [기획 ADR-0030](../planning-adr/0030-unit-sheets-from-materials.md)
- 관련 ADR: [ADR-0014](0014-teaching-material-rag.md), [ADR-0016](0016-standard-level-list-and-item-ids.md) (결정 4를 대체할 예정), [ADR-0025](0025-form-key-tags-and-merged-editions.md), [ADR-0031](0031-catalog-batch-and-embed-cache.md)
- 트러블슈팅: [TS-0004](../troubleshooting/0004-irregular-verb-tags-dropped.md)

## 배경 (Context)
- 수업 준비 그래프는 `TextbookUnit`(어휘·문법·대화·읽기·연습) 모양의 과 데이터를 읽는다. 지금은 손으로 만든 `data/textbook/unit_02~04.json`뿐이다.
- 지침서 1·2권(OCR, layout `sections`)은 과마다 모양이 같다: 쪽 머리말 "3과 • 제목", 수업 개요의 "'-어요'의 의미를 설명한다", 학습 내용의 "문법 / 습니다/습니까, 을, 도", 어휘 구역의 "노래 song"·"따라 하세요. 노래, 노래, 노래."(1권) 또는 낱말 목록 + 같은 낱말 제목(2권).
- 표준 목록(`data/standard/grammar.json`, `vocab.json`)과 형태 키(`app.rag.forms`, ADR-0025)로 형태 → 표준 ID를 맞출 수 있다 (`grammar_qa.match_forms`).

## 결정 (Decision)
1. **단원 시트** `data/curriculum/<book>/unit_NN.json` (`UnitSheet`). `TextbookUnit`과 칸 이름이 같아서 그래프 코드를 거의 그대로 쓴다. 더한 칸: `book`, `status`(draft | reviewed), `notes`, 항목마다 `source {book, pages}`(원문 버튼, ADR-0030), 문법·어휘 `level`, 문법 `standard_ids`. 교재 발췌가 들어 있어 git에 넣지 않는다.
2. **ID**: 문법 = 첫 표준 ID(`std-g-030`) + `standard_ids` 전부, 어휘 = 표준 어휘 ID. 표준 목록에 없는 표현은 `ko1-u02-x01`, 대화·읽기·연습은 `ko1-u02-d01`. 진도는 `std-` ID만 센다.
3. **뽑기는 코드 규칙** (`extract.py`, LLM 없음):
   - 문법: ① 수업 개요 "'…'의 의미를 설명" ② 학습 내용 "문법" 칸 앞뒤 줄 ③ 문법 N 구역 teaches 태그를 합친다 (하나만 보면 OCR 읽는 순서에 따라 빠진다). 형태는 **글자 그대로** 맞을 때만 받는다 (`match_forms`가 뒤를 잘라 맞추므로 "-어휘 및 표현"이 "-어"가 됐다). 붙임표가 빠진 어미("습니다")는 붙여 본다. 키마다 **표제어가 그 형태인 표준 항목**을 먼저 고른다 (에서부터 → 2급 "에서부터", 1급 "부터"의 관련형이 아니라).
   - 어휘: 낱말 + 영어 뜻 줄, "따라 하세요. X, X, X"(줄을 이어 붙여서 찾음), 그리고 앞의 둘이 거의 못 찾은 구역에서만 "혼자 두 번 이상 나온 짧은 줄 + 표준 목록에 있음". 이미 뽑은 낱말의 활용형("맑습니다")은 버린다. 어휘 구역이 없는 과(구역 나누기가 안 된 과)는 과 전체에서 찾는다.
   - 예문: 그 구역에서 존댓말로 끝나는 짧은 문장만 (교사용 지시문 "…들려준다."는 빠진다). 괄호 속 지시("(빵 사진을 보여 주며)")는 지운다. 목표 형태의 글자가 보이는 문장을 앞에 둔다.
4. **검수**: `build`는 `status: reviewed` 시트를 덮어쓰지 않는다. 손으로 만든 교재 JSON은 `convert_textbook`으로 reviewed 시트가 된다 (문법 = `textbook_map.json`, 어휘 = 표준 낱말).
5. **정확도는 정답과 비교해 잰다** (`evaluate.py`, 테스트 `test_curriculum.py::test_draft_matches_hand_made_units`): 2~4과 문법 정밀도·재현율 100%, 어휘 정밀도 100% / 재현율 91·100·62%. 빠진 어휘는 지침서에 거의 안 나오는 교실 사물 등이다.
6. 표준 목록의 뜻 번호·다른 꼴("-다가1(1)", "에서부터(서부터)")을 형태 키로 바꿀 수 있게 정리한다 (`grammar_qa.standard_forms`). 문법 질문의 등급 표시도 같이 고쳐진다 ("-다가"가 "등급 모름" → 2급).
7. 대응표 수정: `u02-g02`(이 아니다)를 "이 + 아니다(어휘)"에서 표준 표현 `std-g-037`로 고쳤다. 모국어 노트도 같은 ID로 옮겼다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| LLM이 지침서 쪽을 읽고 시트를 만든다 | 쪽 글 → JSON | 규칙을 안 만들어도 된다 | 작은 로컬 모델은 형태를 지어낸다 (TS-0001). 지침서 모양이 일정해서 규칙이 정확하다. 대화·연습 구조화에는 나중에 쓸 수 있다 |
| 표준 ID 대신 교재 ID 유지 (`u05-g01`) | 지금 방식 | 이전이 필요 없다 | 교재가 둘 이상이면 같은 문법이 다른 ID가 되어 진도·약점이 끊긴다 (ADR-0016의 재검토 조건) |
| 문법 하나 = 표준 ID 하나로 쪼갠다 | -습니다/-습니까를 두 항목 | 단순하다 | 손으로 만든 교재 항목(한 상자에 둘)과 맞지 않는다 → `standard_ids` 목록으로 둔다 |
| 시트를 DB(Spring)에 둔다 | 앱 데이터처럼 | 화면에서 고치기 쉽다 | 정적 참고 자료라 ai-server 파일 데이터다 (ADR-0005, 교재 JSON과 같음). 검수 화면이 생기면 다시 본다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: ko1·ko2 40과 시트가 생겼다 (ko1 2~4과는 reviewed). 뽑은 항목에 출처 쪽이 붙어 원문 버튼이 된다.
- (2026-10-21 추가) **대화·읽기·연습** (`materials.py`, 본책·익힘책 OCR 쪽, LLM 없음):
  - 대화: 본책 뒤 정답·지문 부록의 "듣고 말하기 지문". 지문은 1과부터 차례로 실려 있어서, 과는 앞의 "N과 제목" 줄로 정하고 제목 줄을 OCR이 못 읽었으면 앞 지문의 과 + 1. 말하는 사람은 "앞 줄이 문장으로 끝난 뒤 줄 맨 앞에 두 번 이상 나온 낱말"만 인정한다 (한 번이면 줄이 바뀐 문장의 첫 낱말일 수 있다). ko1·ko2 40과 모두 대화가 나오고, ko1 2~4과는 손으로 만든 정답과 같다.
  - 읽기: "글을 잘 읽으세요." 다음 문장들. 연습: 한국어 지시문 + 다음 줄 영어 번역이 붙은 곳 (듣기·읽기·말하기 지시문은 뺀다). 익힘책 연습을 앞에 둔다 (숙제 = 앞에서부터 문법 수만큼).
  - 과 번호를 잘못 읽은 앞쪽 쪽(목차 등)은 그 과 쪽들의 가운데에서 40쪽 넘게 떨어지면 버린다.
  - 해 봤다가 뺀 것: 본책 쪽에서 어휘를 더 뽑기. 본책의 "그 과" 쪽에 다음 과 첫 쪽(어휘 미리 보기)이 섞여 있어 2과에 3과 낱말이 들어갔다 (2~4과에서 맞은 것 6개, 틀린 것 50개 이상). 어휘는 지침서에서만 뽑는다.
- 대가: 대화·연습은 OCR 글이라 빈칸·보기가 섞인다 (`notes`에 적고 원문 쪽을 붙인다).
- 대가: ko2 몇 과(14·19·20과)는 어휘가 5개 미만이다 → `notes`에 적어 두고 화면에 보인다.
- **DB 이전 (2026-10-21 적용)**: Flyway `V6__standard_item_ids.sql` (`app.curriculum.migrate_ids`가 만든다). `weakness.item_id`, `lesson.covered_item_ids`(순서 유지), `lesson.understanding`(키)을 새 ID로 바꾸고 `student.next_book`·`lesson.book`(기본 ko1)을 더했다. 적용 전 `pg_dump` 백업(`backups/`, git 밖)을 받았고, 백업을 복원한 임시 DB에서 먼저 시험했다.
- **새 ID와 옛 ID를 함께 받는다**: 형식 검사(`StudentDtos.ITEM_ID_PATTERN`, `shared/constraints.json` `item_id_pattern`, 프론트)는 옛 교재 ID도 통과시키고, ai-server가 들어온 옛 ID를 `to_new`로 바꾼다 (프로필 `load_profile`, 수업 후 기록의 구성안). 이전 전에 만든 기록·샘플이 깨지지 않는다.
- **항목 목록 하나로**: `textbook.load_all_items()`가 단원 시트 전체를 읽는다 (파일 수정 시각으로 캐시). 학생 등록·수업 후 기록의 ID 검사, 화면 이름표(`/textbook/items`), 리포트, 모국어 노트가 모두 이 목록을 쓴다. 학생 등록 프롬프트에는 문법만 넣는다 (어휘까지 넣으면 수백 줄).
- **수업 준비**: `load_textbook`이 `(book, unit_no)` 시트를 읽는다 (실행 값 → 프로필 `next_book`·`next_unit`). 시트가 없으면 `MissingUnitSheet`(다시 해도 같은 오류). 근거 지침서는 교재마다 (`ko1 → ko1_guide`). 브리핑에 `unit_sheet {status, notes}`를 붙여 화면이 "검수 전 단원"을 보여 준다. 화면의 과 고르기는 `GET /api/curriculum` 목록에서만.
- 남은 일: 검수 화면, 학생 화면에서 다음 교재(`nextBook`) 바꾸기, 3급 이상 교재(매뉴얼·지침서 모양이 다름).

## 재검토 조건
- 다른 지침서(3~6급 매뉴얼·지침서)는 모양이 달라서 → 책마다 규칙을 따로 만들거나 LLM 구조화를 쓴다
- 검수 화면이 생기면 → 시트를 어디에 둘지(파일 vs DB) 다시 정한다
