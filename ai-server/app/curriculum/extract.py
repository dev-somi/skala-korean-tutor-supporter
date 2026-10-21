"""
이 파일의 역할: 교원용 지침서(layout "sections")에서 과마다 가르칠 문법·어휘를 코드 규칙으로 뽑는다. (기술 ADR-0032)

지침서 1·2권은 과마다 모양이 같다 (OCR 결과에서 확인):
  - 쪽 머리말 "3과 • 저도 드라마를 좋아합니다" → 과 제목
  - 학습 목표·수업 개요: "그림과 보기 대화를 통해 '-어요'의 의미를 설명한다" (문법마다 한 줄)
                          "학습 내용 … 문법 / 습니다/습니까, 을, 도"
  - 어휘 및 표현 구역: "노래 song" (낱말 + 영어 뜻), "따라 하세요. 노래, 노래, 노래." (세 번 따라 읽기)
뽑은 형태는 표준 목록(국립국어원)에 맞춰 ID를 붙인다. 목록에 없는 낱말은 진도에 세지 않는 "표현"이 된다.
"""

import re
from functools import lru_cache

from app.agent.grammar_qa import _standard_by_key, excerpt, match_forms, standard_forms
from app.rag import index as rag_index
from app.rag.chunk import UNIT_HEADER, load_pages
from app.rag.forms import form_keys
from app.standard.levels import _vocab_by_word, content_words

EXPLAIN = re.compile(r"['‘’]([^'‘’]{1,20})['‘’]\s*의\s*의미를\s*설명")
GLOSS = re.compile(r"^([가-힣]{1,8}(?: [가-힣]{1,6})?)\s+[A-Za-z(0-9][A-Za-z ()'0-9.,/-]*$")
REPEAT = re.compile(r"따라\s*하세요\.?\s*([가-힣]{1,8}(?: [가-힣]{1,6})?)\s*[,.]\s*\1")
SHORT_WORD = re.compile(r"^[가-힣]{1,6}(?: [가-힣]{1,5})?$")
GLOSS_WORDS = re.compile(r"^[A-Za-z][A-Za-z ()'.,/-]*$")


@lru_cache
def unit_titles(guide: str) -> dict[int, str]:
    """쪽 머리말 "3과 • 저도 드라마를 좋아합니다"에서 과 제목을 얻는다."""
    titles: dict[int, str] = {}
    for page in load_pages(guide):
        for line in page["lines"]:
            if match := UNIT_HEADER.match(line["text"]):
                titles.setdefault(int(match.group(1)), re.split(r"[•·]", line["text"], maxsplit=1)[1].strip())
    return titles


def exact(part: str) -> bool:
    """형태가 글자 그대로 맞는가. match_forms는 뒤를 잘라 가며 맞추므로 "-어휘 및 표현"도 "-어"로 맞춘다."""
    found = match_forms([part])
    return bool(found) and found[0]["form"] == part


def with_hyphen(candidate: str) -> list[str]:
    """"습니다/습니까" → ["-습니다", "-습니까"]. 어미인데 붙임표가 빠졌으면 붙여 본다."""
    out = []
    for part in candidate.strip().strip("'‘’").split("/"):
        part = part.strip()
        if not part:
            continue
        if not exact(part) and exact(f"-{part.lstrip('-')}"):
            part = f"-{part.lstrip('-')}"
        out.append(part)
    return out


def grammar_candidates(parents: list[dict]) -> list[str]:
    """
    문법 형태 후보 (순서 = 지침서에 나온 순서). 세 곳을 합친다. 한 곳만 보면 OCR 읽는 순서에 따라 빠진다.
      ① 수업 개요 "'…'의 의미를 설명한다"  ② 학습 내용 "문법" 칸 앞뒤 줄  ③ 문법 N 구역의 teaches 태그
    """
    cands: list[str] = []
    for parent in parents:
        if not parent["section"].startswith("학습"):
            continue
        for match in EXPLAIN.finditer(" ".join(parent["text"].split())):
            cands += with_hyphen(match.group(1))
        lines = [line.strip() for line in parent["text"].splitlines()]
        for i, line in enumerate(lines):
            if line == "문법":
                for near in lines[max(0, i - 1) : i + 2]:
                    parts = [p for c in re.split(r"[,，]", near) for p in with_hyphen(c)]
                    if parts and all(exact(p) for p in parts):
                        cands += parts
    for parent in parents:
        if parent["section"].startswith("문법"):
            cands += parent["teaches"]
    return list(dict.fromkeys(cands))


def headword_item(key: str) -> dict:
    """키에 맞는 표준 항목 하나. 표제어가 그 형태인 항목을 먼저 (에서부터 → "에서부터" 2급, "부터"의 관련형 1급이 아니라),
    그다음 등급이 가장 낮은 것."""
    items = _standard_by_key()[key]
    own = [i for i in items if key in {k for f in standard_forms(i["form"]) for k in form_keys(f)}]
    return (own or items)[0]


def grammar_items(parents: list[dict]) -> list[dict]:
    """후보 → [{form, keys, standard_ids, level, section}]. 같은 표준 항목은 한 번만."""
    found, seen = [], set()
    for cand in grammar_candidates(parents):
        matched = match_forms([cand])
        if not matched:
            continue
        keys = set(matched[0]["keys"])
        std = [headword_item(k) for k in sorted(keys) if _standard_by_key().get(k)]
        ids = [item["id"] for item in std if item["id"] not in seen]
        if not ids:
            continue
        seen.update(ids)
        section = next((p for p in parents if p["section"].startswith("문법") and keys & set(p["teaches"] + p["mentions"])), None)
        found.append({"form": matched[0]["form"], "keys": keys, "standard_ids": ids, "level": min(i["level"] for i in std), "section": section})
    return found


def vocab_words(parents: list[dict]) -> list[tuple[str, str, dict]]:
    """[(낱말, 영어 뜻, 나온 구역)]. 어휘 구역이 없으면(구역 나누기가 안 된 과) 과 전체에서 찾는다."""
    sections = [p for p in parents if p["section"].startswith("어휘 및 표현")] or parents
    words: dict[str, tuple[str, dict]] = {}
    for parent in sections:
        before = len(words)
        for line in parent["text"].splitlines():
            if match := GLOSS.match(line.strip()):
                gloss = line.strip()[len(match.group(1)) :].strip()
                words.setdefault(match.group(1), (gloss if GLOSS_WORDS.match(gloss) else "", parent))
        for match in REPEAT.finditer(" ".join(parent["text"].split())):
            words.setdefault(match.group(1), ("", parent))
        # 지침서 2권: 구역 맨 위 낱말 목록 + 같은 낱말이 설명 제목으로 다시 나온다 → 혼자 두 번 이상 나온 짧은 줄 (표준 목록에 있는 것만)
        # 앞의 두 규칙이 거의 못 찾은 구역에만 쓴다. 1권에서는 설명 속 낱말("의자")까지 잡아 정밀도가 떨어졌다
        if len(words) - before >= 2:
            continue
        lines = [line.strip() for line in parent["text"].splitlines()]
        for line in dict.fromkeys(lines):
            if SHORT_WORD.match(line) and lines.count(line) >= 2 and standard_vocab(line):
                words.setdefault(line, ("", parent))
    return [(word, gloss, parent) for word, (gloss, parent) in words.items()]


def standard_vocab(word: str) -> dict | None:
    """표준 어휘 항목 (같은 글자가 여럿이면 등급이 가장 낮은 것)"""
    items = _vocab_by_word().get(word, [])
    return min(items, key=lambda i: i["level"]) if items else None


def is_inflection(word: str, listed: set[str]) -> bool:
    """"맑습니다", "춥습니다"처럼 이미 뽑은 낱말의 활용형인가"""
    if " " in word:
        return False
    return any(lemma in listed and lemma != word for lemma, _ in content_words(word))


def unit_parents(guide: str, unit_no: int) -> list[dict]:
    return rag_index.get_sections(guide, unit_no)


def grammar_description(item: dict) -> str:
    return excerpt(item["section"]["text"], item["keys"]) if item["section"] else ""


# 예문 = 학생에게 하는 말(존댓말 끝). 교사용 지시문("…들려준다.")은 평서형이라 걸러진다
POLITE_END = re.compile(r"(요|니다|니까|세요|시오)\s*[.?!]?$")
SPEAKER_MARK = re.compile(r"^(?:[•·]|[교고연학를록다]\s|\(?[0-9①-⑩]\)?\s)+")  # 글머리표, OCR이 읽은 교사·학생 아이콘
MAX_EXAMPLES = 4


def example_lines(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        sentence = SPEAKER_MARK.sub("", re.sub(r"\([^)]*\)", "", line).strip()).strip()  # "(빵 사진을 보여 주며)" 같은 지시를 지운다
        if 4 <= len(sentence) <= 40 and re.search(r"[가-힣]", sentence) and POLITE_END.search(sentence) and "따라 하세요" not in sentence:
            out.append(sentence)
    return list(dict.fromkeys(out))


def grammar_examples(item: dict) -> list[str]:
    """그 문법 구역에서 목표 형태가 나온 뒤의 예문"""
    if not item["section"]:
        return []
    # 목표 형태의 글자가 보이는 문장을 앞에 둔다 ("-고 싶다" → "고 싶")
    surface = item["form"].lstrip("-").split("/")[0]
    surface = surface[:-1].rstrip() if surface.endswith("다") and len(surface) > 2 else surface
    lines = example_lines(grammar_description(item))
    return sorted(lines, key=lambda line: surface not in line)[:MAX_EXAMPLES]


def vocab_example(word: str, parent: dict) -> str:
    """어휘 구역에서 그 낱말이 들어간 첫 예문 ("케이 팝은 한국 노래예요.")"""
    stem = word[:-1] if word.endswith("다") and len(word) > 2 else word
    return next((s for s in example_lines(parent["text"]) if stem in s), "")
