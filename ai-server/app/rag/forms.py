"""
이 파일의 역할: 문법 형태를 "형태 키"로 바꾼다. 교재 청크의 태그와 질문을 같은 키로 맞추기 위한 것이다. (기술 ADR-0025)

  form_keys("-아서/-어서/-여서(1)")  → {"-어서"}
  form_keys("-(으)니까")              → {"-니까"}
  form_keys("한테, 한테(서)")         → {"한테", "한테서"}
  form_keys("이/가")                  → {"이"}
  form_keys("-아/어서")               → {"-어서"}  (줄임 표기)
  form_keys("-는/-은/-ㄴ 게 어때(요)?") → {"-는_게_어때요", "-ㄴ_게_어때요", …}

- 어미·표현은 "-"를 붙여 조사와 구분한다: "-는"(어미) ≠ "는"(조사, → "은").
- 이형태는 정규 키 하나로 모은다: 아/어/여 → 어, 앞의 "으" 빼기, 을/ㄹ → ㄹ, 은/ㄴ → ㄴ, 습니다/ㅂ니다 → ㅂ니다,
  조사 쌍(이/가, 을/를, 은/는, 과/와, 으로/로, 이나/나, 이랑/랑) → 앞쪽.
- 띄어쓰기는 "_"로 남긴다: "-는 데"(의존명사) ≠ "-는데"(어미). "(1)" 같은 번호는 지운다. 키는 화면에 보이지 않는다.
- "A/B/C 꼬리"처럼 꼬리가 마지막 조각에만 적혀 있으면 앞 조각에도 붙인다 ("-는/-은 게 어때" → "-는 게 어때", "-은 게 어때").
"""

import re
from functools import lru_cache

PARTICLE_PAIRS = {"가": "이", "를": "을", "는": "은", "와": "과", "로": "으로", "나": "이나", "랑": "이랑"}
OPTIONAL = re.compile(r"\(([가-힣]{1,2})\)")  # "(으)", "(서)" → 있는 모양과 없는 모양
NUMBERING = re.compile(r"\(\d\)|[?？.…]+$")
SHORTHAND = re.compile(r"-((?:[가-힣]/)+)([가-힣])([가-힣]+)")  # "-아/어서" → "-아서/-어서" (첫 음절만 바꿔 쓰는 줄임 표기)
VALID_KEY = re.compile(r"^-?[가-힣ㄱ-ㅎ]+(?:_[가-힣ㄱ-ㅎ]+){0,3}$")


def canonical(key: str) -> str:
    """이형태를 정규 키 하나로. key의 띄어쓰기는 "_"이고, 어미는 "-"로 시작한다."""
    if not key.startswith("-"):
        if key in PARTICLE_PAIRS:
            return PARTICLE_PAIRS[key]
        return key
    body = key[1:]
    if len(body) > 1 and body[0] == "으":
        body = body[1:]  # -으니까 → -니까, -으면 → -면, -으세요 → -세요
    body = re.sub(r"^[아여]", "어", body)  # -아서/-여서 → -어서
    body = re.sub(r"^[았였]", "었", body)
    body = re.sub(r"^을", "ㄹ", body)  # -을 거예요 / -ㄹ 거예요
    body = re.sub(r"^은", "ㄴ", body)  # -은 후에 / -ㄴ 후에 ("-는"은 그대로)
    body = re.sub(r"^습니", "ㅂ니", body)
    return "-" + body


def _expand_tails(label: str) -> list[str]:
    """"-는/-은/-ㄴ 게 어때" → ["-는 게 어때", "-은 게 어때", "-ㄴ 게 어때"]. 쉼표 묶음마다 따로 본다."""
    out = []
    for group in re.split(r"[,·]", label):
        parts = [p.strip() for p in group.split("/") if p.strip()]
        # 꼬리는 띄어쓰기가 있는 첫 조각에서 가져온다 (OCR이 "-ㄴ 데다"를 "L 데다"로 읽어 "-"가 빠져도)
        tail = next((p.split(None, 1)[1] for p in parts if len(p.split(None, 1)) == 2), None)
        for i, p in enumerate(parts):
            if tail and p.startswith("-") and " " not in p and any(" " in q for q in parts[i + 1 :]):
                p = f"{p} {tail}"
            out.append(p)
    return out


def form_keys(label: str) -> set[str]:
    """교재 제목·질문에 적힌 형태 → 정규 키 집합. 형태가 아닌 글(예: "단위 명사(개, 명…)")은 버린다."""
    label = NUMBERING.sub("", label.strip())
    label = SHORTHAND.sub(lambda m: "/".join(f"-{head}{m.group(3)}" for head in [*m.group(1).split("/")[:-1], m.group(2)]), label)
    keys = set()
    for part in _expand_tails(label):
        part = re.sub(r"\s+", "_", part.strip()).strip("'‘’\"“”「」_")
        if "-" in part[1:] and not part.startswith("-"):
            part = part[part.index("-"):]  # "...은_-기_나름이다" → "-기_나름이다"
        if not part:
            continue
        variants = {part}
        for match in OPTIONAL.finditer(part):
            variants = {v.replace(match.group(0), match.group(1)) for v in variants} | {
                v.replace(match.group(0), "") for v in variants
            }
        for v in variants:
            v = v.rstrip("-") if v.count("-") > 1 or (v.endswith("-") and len(v) > 2) else v  # "-으시-" → "-으시"
            if VALID_KEY.match(v):
                keys.add(canonical(v))
    return keys


QUOTED = re.compile(r"[‘'\"“]\s*([^’'\"”\n-]{0,6}-[^’'\"”\n]{1,16}?|[가-힣]{1,3}/[가-힣]{1,3})\s*[’'\"”]")  # '-어서', ‘...은 -기 나름이다’, '은/는'


def quoted_forms(text: str) -> set[str]:
    """본문에 따옴표로 적힌 문법 형태 ('-어서', ‘-기 나름이다’, '은/는') → 정규 키. mentions 태그에 쓴다."""
    keys = set()
    for match in QUOTED.finditer(text):
        keys |= form_keys(match.group(1))
    return keys


@lru_cache
def particle_keys() -> frozenset[str]:
    """표준 문법 목록에서 "-" 없이 쓰는 형태(조사, '이 아니다' 같은 표현)의 키. 따옴표 글('시간', '가영')이 문법인지 가릴 때 쓴다."""
    from app.standard.levels import grammar_items  # 순환 import 방지

    return frozenset(
        key for item in grammar_items() for form in [item["form"], *item["related"]] for key in form_keys(form) if not key.startswith("-")
    )


def is_grammar_key(key: str) -> bool:
    return key.startswith("-") or key in particle_keys()
