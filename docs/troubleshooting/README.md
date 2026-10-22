# 트러블슈팅 기록

해 봤는데 안 됐고, 원인을 찾아서 고친 일을 남긴다. 쓰는 기준과 템플릿은 [CLAUDE.md](../../CLAUDE.md) "막혔다가 풀리면 트러블슈팅 기록을 쓴다".

| 번호 | 제목 | 날짜 | 관련 ADR |
|---|---|---|---|
| [0001](0001-grammar-qa-shorthand-and-invented-form.md) | 문법 질문이 질문에 없던 -어/아서를 "근거 없음"으로 돌려줬다 | 2026-10-21 | 기술 0025, 0027 |
| [0002](0002-open-drops-page-fragment.md) | `open -a`로 넘긴 PDF URL의 `#page`가 버려져 첫 쪽으로 열렸다 | 2026-10-21 | 기술 0030 |
| [0003](0003-printed-page-collision.md) | 인쇄 33쪽이 PDF 33쪽(과 표지)으로 바뀌어 엉뚱한 쪽이 열렸다 | 2026-10-21 | 기술 0030 |
| [0004](0004-irregular-verb-tags-dropped.md) | 불규칙 용언(춥다·덥다·듣다)이 Kiwi 태그 VA-I·VV-I라서 예문 어휘 등급에서 빠졌다 | 2026-10-21 | 기술 0016, 0032 |
| [0005](0005-listed-conjugations-and-related-form-evidence.md) | "너라면, 너라서, 너니까"는 형태를 못 찾았고, "-라면, -라서"는 관련형이라 교재 근거가 없다고 나왔다 | 2026-10-22 | 기술 0037 |
| [0006](0006-compound-patterns-matched-to-beginner-items.md) | 5~6급 문형 "과연 -을까", "-게끔 -어야 하다"가 1·2급 항목("-을까", "-게")으로 잡혔다 | 2026-10-22 | 기술 0040 |
| [0007](0007-eullaeya-no-evidence-despite-indexed-text.md) | "-을래야"가 색인 글에 3번 나오는데 태그·따옴표가 빠져 "교재 근거 없음"이었다 | 2026-10-22 | 기술 0044 |
| [0008](0008-ollama-runaway-generation.md) | 로컬 Ollama로 유이 3과 수업 준비를 돌리면 "개인화 설명 쓰기"에서 10분 넘게 멈췄다 | 2026-10-22 | 기술 0012 |
