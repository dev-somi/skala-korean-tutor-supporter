# TS-0002: `open -a "Google Chrome" "file:///…pdf#page=60"`이 60쪽이 아니라 첫 쪽으로 열렸다
- 날짜: 2026-10-21
- 관련 모듈: `ai-server/app/rag/pdfs.py` (`open_pdf`)
- 관련 ADR: [기술 ADR-0030](../adr/0030-local-pdf-open-via-ai-server.md)

## 증상
출처의 원본 PDF를 그 쪽으로 열려고 macOS `open`으로 Chrome에 `#page=60`이 붙은 file URL을 넘겼다. 명령은 성공(rc=0)했지만 PDF가 첫 쪽에서 열렸다. 열린 탭의 URL을 AppleScript로 읽어 보니 `#page=60`이 없었다.

```
$ open -a "Google Chrome" "file:///Users/somi/Desktop/%ED%95%9C…%EC%84%9C.pdf#page=60"
$ osascript -e 'tell application "Google Chrome" to get URL of active tab of front window'
file:///Users/somi/Desktop/%E1%84%92%E1%85%A1…%E1%84%89%E1%85%A5.pdf      ← #page 없음, 한글도 NFD로 바뀜
```

## 원인
`open`은 file URL을 LaunchServices에 파일 경로로 바꿔 넘긴다. 이때 URL 조각(`#…`)이 버려진다. 한글 경로가 NFD로 바뀐 것도 URL이 아니라 파일 경로로 다시 만들어졌다는 뜻이다.

## 시도한 것
| 시도 | 결과 |
|---|---|
| `open -a "Google Chrome" "file:///…#page=60"` | 열리지만 `#page`가 버려져 첫 쪽 |
| AppleScript `tell application "Google Chrome" to make new tab with properties {URL: …}` | `#page=60`이 그대로 남고 60쪽으로 열림 |

## 해결
`open_pdf`가 `osascript`로 Chrome에 URL을 그대로 넣는다. URL은 `on run argv`로 인자를 넘겨, 경로의 따옴표·한글이 스크립트 문법을 깨지 않게 한다. AppleScript가 안 되는 앱(`PDF_VIEWER`)이면 `open <pdf>`로 첫 쪽부터 연다.

## 배운 점 / 다음에 주의할 것
- `open`의 rc=0은 "열렸다"일 뿐 "원하는 대로 열렸다"가 아니다. 결과(탭 URL)를 따로 읽어 확인한다.
- 처음 실행하면 macOS가 자동화 권한("…이 Google Chrome을 제어하려고 합니다")을 물을 수 있다. 거절하면 osascript가 실패하고 첫 쪽부터 열린다.
