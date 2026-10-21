# ADR-0030: 출처의 원본 PDF는 로컬 ai-server가 선생님 컴퓨터에서 그 쪽으로 연다 — 등록부 pdfs.json + 인쇄 쪽→PDF 쪽 변환
- 상태: Accepted (2026-10-21)
- 관련 모듈: `ai-server/app/rag/pdfs.py`, `ai-server/app/api/materials.py`, `backend/.../material/MaterialController.java`, `frontend/src/components/SourceLink.vue`
- 기획: [기획 ADR-0027](../planning-adr/0027-open-source-pdf.md)
- 관련 ADR: [ADR-0006](0006-sse-proxy-path.md), [ADR-0008](0008-local-dev-runtime.md), [ADR-0014](0014-teaching-material-rag.md), [ADR-0020](0020-local-model-for-demo-too.md), [ADR-0025](0025-form-key-tags-and-merged-editions.md)
- 트러블슈팅: [TS-0002](../troubleshooting/0002-open-drops-page-fragment.md), [TS-0003](../troubleshooting/0003-printed-page-collision.md)

## 배경 (Context)
- 출처 글(`세종학당 한국어 1 교원용 지침서 3과 「문법 1」 52~53쪽`)은 코드가 만든다 ([ADR-0014](0014-teaching-material-rag.md) 결정 6). 그런데 화면에는 이 글만 가고 `book`, `pages`는 가지 않았다.
- `pages`는 **책에 인쇄된 쪽**이다. PDF 쪽과 다르다 (지침서 1권: 인쇄 33쪽 = PDF 36쪽).
- 원본 PDF 경로는 어디에도 저장되지 않았다. `ocr`, `textlayer`가 실행 인자로 받기만 한다.
- 지침서 PDF는 292쪽·424MB(스캔 이미지)다. 브라우저는 Spring만 부른다 ([ADR-0006](0006-sse-proxy-path.md)). 지금 Spring 내려받기는 `byte[]`로 한 번에 받는다.
- 브라우저는 http 페이지에서 `file://`을 열 수 없고 OS 명령도 못 쓴다. 하지만 ai-server는 선생님 컴퓨터에서 도는 로컬 프로세스다 ([ADR-0008](0008-local-dev-runtime.md), 데모도 로컬 [ADR-0020](0020-local-model-for-demo-too.md)).

## 결정 (Decision)
1. **여는 주체는 ai-server**: 화면 → Spring `POST /api/materials/open {book, page}` → ai-server가 macOS에서 PDF를 연다. 파일은 네트워크로 보내지 않는다. Spring은 JSON만 넘긴다.
2. **Chrome에 AppleScript로 URL 넣기**: `file:///…pdf#page=N`을 새 탭으로 연다. `open -a`는 `#page`를 버린다 ([TS-0002](../troubleshooting/0002-open-drops-page-fragment.md)). 미리보기는 명령으로 쪽을 못 정한다. 앱은 `PDF_VIEWER`(기본 `Google Chrome`)로 바꿀 수 있고, AppleScript가 안 되는 앱이면 `open`으로 첫 쪽부터 연다.
3. **등록부 `data/rag/pdfs.json`** = `{책 ID: 절대 경로}`. `ocr`·`textlayer`가 끝날 때 자동으로 적는다. 이미 색인한 책은 `python -m app.rag.pdfs scan <폴더>`로 찾는다. 짝짓기 기준은 PDF 쪽 수(OCR한 마지막 쪽 이상, 같으면 가산), 제목의 권 번호(1, 5A…)가 파일명에 있음, 핸드북은 판 언어(영어·일본어), 파일명과 제목의 유사도다. 등록부에 있는 책만 열고, API는 경로를 받지 않는다.
4. **인쇄 쪽 → PDF 쪽은 실행할 때 계산**: OCR JSON의 꼬리말 쪽 번호(`chunk.printed_page`)로 책마다 표를 만들어 캐시한다. 색인·임베딩을 다시 만들 필요가 없다. 쪽 번호가 없는 쪽은 인식된 쪽 번호와 겹치면 지고, 같은 인쇄 쪽에 PDF 쪽이 둘이면(OCR이 잘못 읽음) 책의 보통 차이(PDF − 인쇄)에 가까운 쪽을 쓴다 ([TS-0003](../troubleshooting/0003-printed-page-collision.md)). `text_page` 책은 같고, `culture1`은 PDF = 인쇄 + 1이다.
5. **언어판을 합친 핸드북**(`practicalN_handbook`, [ADR-0025](0025-form-key-tags-and-merged-editions.md))은 등록된 판(영어판 먼저)으로 연다.
6. **출처 응답에 `book`, `pages`를 붙인다**: 브리핑 `references`, 문화 후보, 문법 질문 근거. 화면의 `SourceLink`는 `GET /api/materials`의 목록에 있는 책일 때만 "원문" 버튼을 보인다. 예전에 저장된 브리핑처럼 값이 없으면 버튼을 숨긴다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 인용 쪽 발췌 PDF를 팝업으로 | ai-server가 인용 쪽 ±2쪽을 잘라 Spring을 거쳐 보낸다 | 서버가 원격이어도 된다, 브라우저 안에서 끝난다 | 자르고 보내는 시간이 든다. 앞뒤를 넘겨 볼 수 없다. 지금은 서버가 로컬이라 필요 없다 |
| 책 전체를 Spring으로 스트리밍 + `#page` | Range 요청 중계 | 브라우저 안에서 전체 책 | 424MB를 중계하려면 Spring 내려받기를 스트리밍으로 바꿔야 하고 첫 로딩이 느리다 |
| `file://` 링크를 화면에 둔다 | 버튼이 링크 | 서버 코드 없음 | 브라우저가 http 페이지의 `file://` 이동을 막는다 |
| `.env`에 폴더 하나 + `BOOKS`에 파일명 | `MATERIALS_DIR` | 단순 | 파일명을 바꾸면 못 찾는다. 판마다 파일명이 제각각이다 (사용자가 스캔 방식을 골랐다) |
| 청크에 PDF 쪽을 저장하고 다시 색인 | `Parent.pdf_pages` | 실행할 때 계산 없음 | 2,730개 청크를 다시 임베딩해야 한다. OCR JSON에서 바로 계산할 수 있다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 출처 옆 "원문"을 누르면 424MB 지침서도 1초 안에 그 쪽으로 열린다. 이미 색인한 24권이 `scan` 한 번에 등록됐다.
- 대가: **서버와 화면이 같은 컴퓨터일 때만** 된다. macOS + Chromium 계열 브라우저 기준이다.
- 대가: 처음 열 때 macOS가 "터미널(또는 VS Code)이 Google Chrome을 제어하려고 합니다" 권한을 물을 수 있다.
- 대가: OCR이 꼬리말 쪽 번호를 잘못 읽은 쪽은 한두 쪽 어긋나게 열릴 수 있다 (24권 중 2권에서 몇 쪽).

## 재검토 조건
- 서버를 원격에 배포하면 → 발췌 PDF를 내려보내는 방식으로 바꾼다 (Spring 중계, 브라우저 안 PDF 뷰어)
- Windows·Linux에서 쓰게 되면 → `start`/`xdg-open` + 브라우저 실행 파일에 URL 인자로 넘기기
- 쪽이 어긋난다는 지적이 잦으면 → 청크 단계에서 PDF 쪽을 함께 저장한다
