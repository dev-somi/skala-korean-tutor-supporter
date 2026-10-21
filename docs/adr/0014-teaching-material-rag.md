# ADR-0014: 교수 자료 RAG — Vision OCR + Parent-Child 청크 + ai-server 소유 파일 색인
- 상태: Accepted (2026-10-20)
- 관련 모듈: `ai-server/app/rag/`, `ai-server/scripts/ocr_vision.swift`, `ai-server/data/rag/`
- 관련 ADR: [ADR-0005](0005-data-access-ownership.md), [ADR-0013](0013-process-over-model.md), [기획 ADR-0013](../planning-adr/0013-sejong-public-materials.md)

## 배경 (Context)
세종학당 공개 PDF(교재, 교원용 지침서, 핸드북)를 수업 준비의 근거로 쓰기로 했다. 확인한 사실:
- PDF에 글자 층이 없다 (스캔·이미지). `pdftotext` 결과가 비어 있다. 지침서는 292쪽, 424MB다.
- 지침서는 계층 구조다: 책 → 과 → 구역(학습 목표, 수업 개요, 도입, 어휘 및 표현, 문법 1·2, 듣고 말하기, 읽고 쓰기, 마무리, 지도의 유의점) → 단락.
- 쓰는 경로가 둘이다. 브리핑은 **무엇이 필요한지 이미 안다**(3과, 문법 `을`). 채팅 질문은 **열린 질문**이다("받침 뒤 조사를 헷갈리는 학생 연습 방법").
- [ADR-0005](0005-data-access-ownership.md)에 따라 Postgres는 Spring만 다룬다.

## 결정 (Decision)
1. **OCR**: macOS Vision(`VNRecognizeTextRequest`, ko-KR/en-US)으로 쪽마다 OCR하고 줄 단위 좌표와 함께 `data/rag/ocr/<book>/p-NNN.json`에 저장한다. 한 번만 돌리고 결과를 캐시한다.
2. **Parent-Child 청크**: parent = 과 안의 구역 하나, child = parent를 단락 단위로 나눈 조각. 메타데이터는 `{book, unit, section, pages}`.
3. **임베딩**: Ollama `bge-m3`(다국어, 로컬). child만 임베딩한다.
4. **저장**: ai-server가 소유하는 파일 색인 `data/rag/index/` (청크 JSONL + 벡터). 정적 참고 자료라 앱 데이터가 아니고, 교재 JSON과 같은 위치에 둔다.
5. **검색 경로 두 개**
   - **필터 경로** (브리핑): `book`, `unit`, `section`으로 parent를 바로 가져온다. 임베딩을 쓰지 않아 결정적이다.
   - **의미 경로** (채팅·보충): 질문으로 child를 검색하고, 걸린 child의 parent를 돌려준다. 같은 parent는 한 번만.
6. 결과에는 항상 `book`과 `pages`를 붙여서 출처를 보여 준다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| OCR: tesseract | 오픈소스 | OS 무관 | 2단 편집·표에서 품질이 낮다 |
| OCR: Claude 비전 | 쪽 이미지를 모델에 넣기 | 표 구조까지 가장 정확 | 292쪽 × 여러 책이면 비용이 크다. Vision 결과로 시험한 1과가 충분히 정확했다 |
| 저장: pgvector | 기존 Postgres에 벡터 | 인프라 하나로 | ADR-0005 위반(ai-server가 DB 접근), Postgres 이미지 교체 필요 |
| 저장: Chroma 등 벡터 DB | 전용 라이브러리 | 기능이 많다 | 청크가 수천 개 수준이라 파일 + 선형 검색으로 충분하다. 의존성만 는다 |
| 고정 크기 청크 | 500자씩 자르기 | 구현이 단순하다 | 구역 경계를 무시해 표·절차가 잘리고, 과·구역 필터를 쓸 수 없다 |
| 의미 검색만 | 브리핑도 질문으로 검색 | 경로가 하나 | 필요한 걸 이미 아는데 검색 오차를 들일 이유가 없다. 작은 모델은 엉뚱한 조각에 약하다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 브리핑이 지침서 근거와 쪽수를 갖는다. 새 PDF는 같은 파이프라인(`ocr → chunk → index`)에 넣기만 하면 된다.
- 대가: OCR은 macOS에서만 돈다. 결과 JSON을 공유하면 다른 OS에서도 색인은 만들 수 있다.
- 대가: 데모 때도 임베딩을 위해 Ollama가 떠 있어야 한다 (Anthropic에는 임베딩 API가 없다).
- 대가: 구역 경계는 OCR 줄의 제목 글자로 추정한다. 제목 인식이 틀리면 parent가 섞인다.
- 대가: parent가 길면 프롬프트가 길어진다. 로컬 모델 `num_ctx` 16384 안에 들어가도록 parent 길이를 제한한다.

## 재검토 조건
- 청크가 수만 개를 넘어 검색이 느려지면 → 벡터 DB(또는 sqlite-vec)로 옮긴다
- 다른 교재를 진도 기준으로 쓰게 되면 → 메타데이터에 교재와 무관한 학습 항목 ID를 붙인다 (기획 ADR-0013 재검토 조건)
- OCR 오류로 브리핑이 틀리는 일이 잦으면 → 표가 많은 쪽만 Claude 비전으로 다시 읽는다
