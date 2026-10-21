# ADR-0023: 문화 후보는 의미 검색 + LLM 1회 정리, 선택은 화면에서만 (저장 안 함)
- 상태: Accepted (2026-10-20)
- 관련 모듈: `ai-server/app/rag/textlayer.py`, `app/rag/chunk.py` (`culture1`, `text_pages`), `app/agent/lesson_prep/nodes.py` (`collect_culture`, `briefing`), `lesson_frame.py`, `prompts/briefing_culture.md`, `frontend/src/components/LessonFrame.vue`
- 관련 ADR: [기획 ADR-0023](../planning-adr/0023-culture-point-from-sejong-materials.md), [ADR-0014](0014-teaching-material-rag.md), [ADR-0015](0015-lesson-prep-ends-at-approval.md), [ADR-0022](0022-l1-notes-data.md)

## 배경 (Context)
기획 ADR-0023으로 매 수업 문화 포인트를 세종학당 자료에서 찾아 넣기로 했다. 기술적으로 정할 것:
- 「세종한국문화 1」은 글자 층이 있는 PDF다 (지침서·핸드북과 다르다). 주제 제목은 단원 끝 정리 쪽에만 모여 있고, 본문 쪽에는 이야기와 설명이 섞여 있다.
- 「한국어 1」 과와 문화 주제의 대응표가 없다.
- 선생님 선택을 어디에 저장할지. 수업안 검토 API(`PrepReviewRequest`)는 범주 4개만 받는다.

## 결정 (Decision)
1. **추출**: 글자 층 PDF는 OCR 없이 `pdftotext -layout`으로 쪽마다 저장한다 (`app.rag.textlayer`, `data/rag/text/<book>/`). 청크 방식 `text_pages`: 펼친 두 쪽 = parent, 과 번호는 꼬리말에서. 본문 13~138쪽만 (머리말·정답·색인 제외).
2. **후보 찾기 (코드)**: `collect_culture(unit)`이 과 제목 + 대화문 + 어휘 10개로 질의를 만들어 **의미 경로**로 검색한다 ([ADR-0014](0014-teaching-material-rag.md)). 「세종한국문화 1」에서 2개, 지침서 같은 과에서 1개(질의에 "문화 예절 인사 호칭"을 더함). 출처와 원문(걸린 child)은 코드가 붙인다. 임베딩 서버가 없으면 빈 목록이고 수업 준비는 계속한다.
3. **정리 (LLM 1회)**: `briefing_culture` 호출 하나로 후보마다 요약 1~2문장(원문 안의 내용만), 비교 질문(쉬운 한국어 + 학생 모국어)을 만든다. **요약이 빈 후보는 버린다.** 문법 설명·연습 지시처럼 문화가 아닌 후보를 LLM이 걸러 내는 역할이다. 브리핑의 다른 호출과 함께 동시에 돈다.
4. **틀에 연결**: 결과는 `briefing.culture`(목록)에 넣고, 7단계 틀의 "새 내용 도입" 단계에 `culture` = 기본 후보 번호(0) 또는 `null`(못 찾음)을 둔다. 내용을 복사하지 않고 번호만 둔다 ([ADR-0015](0015-lesson-prep-ends-at-approval.md)의 범주 키와 같은 방식).
5. **선택은 화면에서만**: `LessonFrame`이 후보를 바꿔 보여 주고, [글로 복사]에도 고른 후보가 들어간다. 서버에 저장하지 않는다.
6. 테스트는 `collect_culture`를 가짜 후보로 바꾸고(임베딩 서버를 부르지 않게), 요약이 빈 후보가 빠지는지, 못 찾았을 때 LLM을 부르지 않고 `null`이 되는지 확인한다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 문화 교재도 Vision OCR | 다른 책과 같은 경로 | 경로가 하나 | 글자 층이 있으면 그 글자가 OCR보다 정확하다 |
| 주제 단위 청크 | 32개 주제마다 parent | 후보가 깔끔하다 | 주제 제목이 본문 쪽에 일정하게 없어 경계를 찾기 어렵다. 펼친 두 쪽이면 이야기 하나가 대개 들어간다 |
| 점수 기준으로 후보 거르기 | 유사도 0.5 미만 버리기 | LLM 판단 불필요 | 2026-10-20 검색에서 문화가 아닌 지침서 구역도 0.5 이상이었다. 점수로는 "문화인가"를 가를 수 없다 |
| 선택을 저장 (검토 API에 `culture` 키 추가) | Spring DTO·검증·DB 반영 | 확정본에 남는다 | Spring·ai-server 그래프 재개 경로를 함께 바꿔야 한다. 마감 안에서는 화면 선택 + 복사로 충분하다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 대응표 없이 과마다 문화 후보가 나온다. LLM 호출은 하나 늘지만 다른 브리핑 호출과 동시에 돈다.
- 대가: 수업 준비마다 임베딩 질의가 2번 든다 (bge-m3, 로컬).
- 대가: 고른 후보가 저장되지 않아, 확정된 수업안을 다시 열면 1순위로 보인다.
- 대가: 지침서 후보는 대부분 문화가 아니어서 버려진다 (2~4과 확인). 언어 문화가 잘 안 나오는 이유다.

## 재검토 조건
- 선생님이 고른 후보를 다시 봐야 하는 일이 잦으면 → 검토 API에 `culture` 선택을 더하고 `lesson.briefing`에 반영한다
- 지침서 후보가 계속 버려지면 → 지침서 쪽 검색을 빼거나, 참고 상자(`[참고]`)만 따로 뽑은 청크를 만든다
