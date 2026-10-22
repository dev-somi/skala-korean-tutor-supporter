# ADR-0036: 등급 목록의 "교재" 칸은 단원 시트에서 거꾸로 찾는다 — 문법·어휘 모두, 「한국어 1·2」 전 과
- 상태: Accepted (2026-10-22)
- 관련 모듈: `ai-server/app/api/standard.py` (`_textbook_links`), `ai-server/app/curriculum/sheets.py` (`BOOK_SOURCES.short`), `frontend/src/pages/StandardPage.vue`, `frontend/src/components/TextbookTags.vue`, `frontend/src/api/types.ts` (`StandardTextbookLink`)
- 관련 ADR: [ADR-0016](0016-standard-level-list-and-item-ids.md) (대응표 `textbook_map.json`), [ADR-0032](0032-unit-sheets-and-standard-ids.md) (단원 시트, 항목 ID = 표준 ID)

## 배경 (Context)
- 등급 목록 화면(문법)의 "교재" 칸은 `textbook_map.json`을 거꾸로 읽어 만들었다. 이 파일은 손으로 만든 샘플 교재 「한국어 1」 2~4과의 문법 7개만 담고 있다. 그래서 「한국어 1」 2~4과만 보이고 「한국어 2」는 하나도 없었다.
- ADR-0032 이후 단원 시트(`data/curriculum/ko1` 1~20과, `ko2` 1~20과)에 문법은 `standard_ids`, 어휘는 표준 ID(`std-v-…`)가 이미 들어 있다. 등급 목록 API만 이 시트를 읽지 않았다.
- 어휘 목록에는 교재 칸이 아예 없었다.

## 결정 (Decision)
1. `GET /standard/grammar`, `GET /standard/vocab`의 `textbook`은 **단원 시트 전체**(`sheets.all_sheets()`)에서 만든다. 문법은 `standard_ids`(없으면 `id`), 어휘는 `id`. `std-`로 시작하지 않는 ID(표준 목록에 없는 표현 `…-x01`)는 건너뛴다. 한 과에 같은 ID가 두 번 있어도 한 번만 센다.
2. 연결 하나의 모양: `{book: "ko1", title: "세종학당 한국어 1", short: "한국어 1", unit_no, status}`. 이전의 `item_id`(교재 항목 ID)는 시트에서는 표준 ID와 같아서 뺐다. `short`는 `BOOK_SOURCES`에 둔다.
3. `status`(draft/reviewed)를 같이 내려서, 화면은 검수 전(draft) 시트 연결을 회색 태그로, 검수한 시트는 파란 태그로 보여 준다. draft도 숨기지 않는다 — 대부분의 과가 아직 draft라서 숨기면 다시 거의 비어 보인다.
4. 링크 표는 캐시하지 않는다. 시트 파일 읽기는 `all_sheets`가 수정 시각으로 캐시하므로, `build`로 시트를 다시 만들면 서버를 다시 띄우지 않아도 바로 반영된다.
5. `textbook_map.json`은 지우지 않는다. 손으로 만든 교재 JSON → reviewed 시트 변환(`convert_textbook`)과 `levels.standard_ids`(교재 항목 ID → 표준 ID)가 아직 쓴다. 등급 목록 화면만 더는 이 파일을 보지 않는다.

## 검토한 대안 (Alternatives)
| 대안 | 장점 | 기각 이유 |
|---|---|---|
| `textbook_map.json`에 「한국어 1·2」 전 과를 손으로 채운다 | 지금 코드 그대로 | 시트에 이미 있는 정보를 두 곳에 둔다. 시트를 다시 만들 때마다 어긋난다 |
| reviewed 시트만 연결 | 검수된 것만 보인다 | 지금은 「한국어 1」 2~4과만 reviewed라 고치기 전과 거의 같다 |
| 시트에서 대응표 파일을 생성하는 스크립트 | 파일 하나로 모인다 | 생성 단계를 잊으면 낡는다. 시트를 바로 읽는 편이 단순하다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 문법·어휘 모두 「한국어 1·2」 전 과가 보인다 (1급 문법 45개 전부 연결). 시트를 고치면 바로 반영된다.
- 대가: draft 시트의 연결은 코드 규칙으로 뽑은 것이라 틀릴 수 있다. 회색 태그와 툴팁("단원 시트 검수 전")으로만 알린다.
- 대가: 단원 시트는 저장소에 넣지 않으므로(.gitignore) 시트가 없는 환경에서는 교재 칸이 비어 있다. 테스트는 가짜 시트로 본다.

- 이후: 3A~6B 시트가 생겨([ADR-0040](0040-unit-sheets-from-textbook-3a-6b.md)) 코드 수정 없이 교재 칸에 함께 나온다.

## 재검토 조건
- 시트 수가 많아져 요청마다 링크 표를 만드는 비용이 보이면 → 시트 수정 시각 묶음을 키로 캐시
- 교재가 늘어 태그가 너무 많아지면 → 교재 필터를 화면에 추가
