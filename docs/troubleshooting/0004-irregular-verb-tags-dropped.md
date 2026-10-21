# TS-0004: "춥습니다"·"더워요"의 춥다·덥다가 예문 어휘 등급 계산에서 빠졌다
- 날짜: 2026-10-21
- 관련 모듈: `ai-server/app/standard/levels.py` (`content_words`, `sentence_level`)
- 관련 ADR: [기술 ADR-0016](../adr/0016-standard-level-list-and-item-ids.md), [기술 ADR-0032](../adr/0032-unit-sheets-and-standard-ids.md)

## 증상
단원 시트 어휘에서 "맑습니다"는 "맑다"의 활용형으로 걸러졌는데 "춥습니다"는 남았다. 활용형 판정은 `content_words`로 사전형을 얻어 비교한다.

```
content_words('춥습니다') → []
content_words('맑습니다') → [('맑다', '형용사')]
```

## 원인
Kiwi는 불규칙 활용 용언에 `-I`를 붙인 태그를 쓴다 (`춥/VA-I`, `덥/VA-I`, `듣/VV-I`, `걷/VV-I`, `맵/VA-I`). `content_words`는 `CONTENT_TAGS`에 `VA`·`VV`만 있어서 이 토큰을 모두 버렸다.

이 함수는 예문 등급 판정(`sentence_level`, 기획 ADR-0017)에도 쓰인다. 그래서 "날씨가 더워요" 같은 예문에서 덥다(1급)가 빠졌고, 등급이 더 높은 불규칙 용언이 있는 문장은 실제보다 낮게 판정될 수 있었다.

## 시도한 것
| 시도 | 결과 |
|---|---|
| 단원 시트 쪽에서 "…습니다"로 끝나는 낱말을 따로 거르기 | 증상만 가린다. 등급 판정 버그가 남는다 |
| `content_words`에서 태그의 `-` 뒷부분을 떼고 비교 (`VA-I` → `VA`) | 불규칙 용언이 사전형으로 잡힌다. `VX-I`(보조용언)는 원래대로 빠진다 |

## 해결
`levels.content_words`: `tag = token.tag.split("-")[0]`로 비교한다. 테스트 `tests/test_standard_levels.py::test_irregular_predicates_are_counted` (덥다·듣다·맵다).

## 배운 점 / 다음에 주의할 것
- 형태소 분석기 태그는 기본 태그에 꼬리(`-I`, `-R`)가 붙을 수 있다. 태그 비교는 기본 태그로 한다.
- 예문 등급 테스트에 불규칙 용언(ㅂ·ㄷ·르 불규칙) 문장을 하나씩 넣어 둔다.
