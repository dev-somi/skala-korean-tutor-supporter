"""
이 파일의 역할: 지침서 규칙이 맞지 않는 교재(「세종학당 한국어」 3A~6B)에서 과마다 문법·어휘를 본책 쪽으로 뽑는다. (기술 ADR-0040)

3A~6B 지침서는 1·2권과 모양이 달라 extract.py 규칙이 하나도 맞지 않는다. 대신 본책이 과마다 같은 모양이다 (OCR에서 확인):
  3A~4B  학습목표 "•'-으려면'을 사용하여 문장을 구성할 수 있다."
         문법 쪽 "Grammar" 다음 줄이 형태 ("-으려면", "- 으면 되다 / 안 되다")
         어휘 쪽 "Vocabulary" … 낱말 줄 다음에 "• 예문" 줄 ("동아리" / "• 우리 동아리는 …")
  5A~6B  문형 쪽 "문형을 배워 봅시다." 다음 줄이 형태 ("...에 따르면")
         어휘 쪽 "어휘를 배워 봅시다." … "• 안정적이다" 다음 줄이 예문
과 번호는 색인의 unit 값이 6A·6B에서 엉켜 있어서, 쪽 머리말("1과 • 약속 시간에 늦으면 안 돼요")로 다시 정한다.
"""

import re
from collections import Counter
from functools import lru_cache

from app.agent.grammar_qa import _standard_by_key, match_forms
from app.curriculum.extract import headword_item, standard_vocab, with_hyphen
from app.rag import index as rag_index

HEADER = re.compile(r"^(\d{1,2})과(?:\s*[•·ㆍ.]\s*(\S.*))?$")  # "1과 • 제목", "1과" (과 첫 쪽)
GRAMMAR_HEAD = re.compile(r"^\W{0,3}(?:Grammar|문형을 배워 봅시다\.?)$")  # "✓ 어휘를 배워 봅시다."처럼 앞에 기호가 붙기도 한다
VOCAB_HEAD = re.compile(r"^\W{0,3}(?:Vocabulary|어휘를 배워 봅시다\.?)$")
VOCAB_END = re.compile(r"^(?:Grammar|문형을 배워 봅시다|어휘를 연습해 봅시다|알맞은 것끼리)")
COMPOUND = re.compile(r"\.{2,}|…|\S\s+-")  # "...은 -는다는 것이다", "-게끔 -어야 하다", "과연 -을까"
GOAL = re.compile(r"['‘’]([^'‘’]{1,40})['‘’]\s*(?:을|를)?\s*사용하여")
WORD = re.compile(r"^[가-힣]{1,8}(?: [가-힣]{1,6})?(?: ?\(하다\))?$")  # "동아리", "회원 가입", "가입 (하다)"
BULLET = re.compile(r"^[•·●]\s*")
PARTICLE = re.compile(r"(?:이|가|을|를|에|의|과|와|으로|로|에서)$")
SENTENCE = re.compile(r"[가-힣].*(?:[.?!]|요|다)$")
MAX_EXAMPLES = 4
MIN_FRAGMENT_LEVEL = 3  # 조각으로만 맞은 항목이 이보다 낮으면 버린다 ("과연 -을까"의 1급 "-을까"는 5A의 학습 목표가 아니다)
SECTION_LABELS = {"듣기", "말하기", "읽기", "쓰기", "문법", "어휘", "부가 문법"}  # 학습목표 쪽의 "듣기 / • … 이해할 수 있다"
NOT_EXAMPLE = ("사용하여", "나타내", "사용한다", "결합한다", "'", "’", "/")  # 문법 설명·지시문 줄


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


@lru_cache
def book_pages(book: str) -> list[dict]:
    """[{page, text}] 쪽 순서. 색인은 한 쪽에 parent가 여럿일 수 있어(구역이 겹친 쪽) 글을 합친다."""
    by_page: dict[int, list[str]] = {}
    for parent in rag_index.load_index()["parents"].values():
        if parent["book"] == book:
            texts = by_page.setdefault(parent["pages"][0], [])
            if parent["text"] not in texts:
                texts.append(parent["text"])
    return [{"page": page, "text": "\n".join(texts)} for page, texts in sorted(by_page.items())]


def _page_headers(text: str) -> set[int]:
    """그 쪽 머리말의 과 번호들. 둘 이상이면 목차다."""
    return {int(m.group(1)) for line in _lines(text) if (m := HEADER.match(line))}


@lru_cache
def page_units(book: str) -> dict[int, int]:
    """
    {쪽: 과}. 머리말은 홀수 쪽에만 있어서, 머리말이 없는 쪽은 다음 머리말 쪽의 과를 따른다.
    목차 쪽(과 번호가 여럿)에서 끊는다. 안 끊으면 앞쪽 구성표가 1과에 붙는다.
    """
    out, following = {}, None
    for page in reversed(book_pages(book)):
        units = _page_headers(page["text"])
        if len(units) > 1:
            following = None
            continue
        following = units.pop() if units else following
        if following:
            out[page["page"]] = following
    return out


@lru_cache
def unit_titles(book: str) -> dict[int, str]:
    """쪽 머리말에서 가장 많이 나온 제목 (OCR이 띄어쓰기를 다르게 읽은 줄이 섞여 있다)"""
    counts: Counter = Counter()
    for page in book_pages(book):
        for line in _lines(page["text"]):
            if (m := HEADER.match(line)) and m.group(2) and "지문" not in m.group(2):
                counts[(int(m.group(1)), m.group(2).strip())] += 1
    titles: dict[int, str] = {}
    for (unit, title), _ in counts.most_common():
        titles.setdefault(unit, title)
    return titles


def unit_pages(book: str, unit_no: int) -> list[dict]:
    """그 과의 본문 쪽. 부록(듣기 지문·정답)도 머리말이 있으므로 본문에서 가장 많이 몰린 덩어리만 남긴다."""
    units = page_units(book)
    pages = [p for p in book_pages(book) if units.get(p["page"]) == unit_no]
    if not pages:
        return []
    runs, run = [], [pages[0]]
    for prev, page in zip(pages, pages[1:]):
        if page["page"] - prev["page"] > 2:
            runs.append(run)
            run = []
        run.append(page)
    runs.append(run)
    return max(runs, key=len)


# ── 문법 ──────────────────────────────────────────────────────────────


def _clean_form(text: str) -> list[str]:
    """"- 으면 되다 / 안 되다" → ["-으면 되다", "안 되다"], "...에 따르면" → ["에 따르면"]"""
    text = re.sub(r"^[•·.…\s]+|[?？]$", "", text.strip()).strip()
    text = re.sub(r"-\s+", "-", text)
    return [part for part in with_hyphen(text) if part]


def _forms(text: str) -> list[str]:
    """머리 줄 → 형태 후보. 여러 조각 문형("...은 -는다는 것이다")은 나누지 않고 통째로 둔다 (match_standard가 조각으로 맞춘다)."""
    raw = re.sub(r"^[•·\s]+|[?？]$", "", text.strip()).strip()
    if COMPOUND.search(raw):
        return [re.sub(r"-\s+", "-", raw)]
    return _clean_form(raw)


def grammar_candidates(pages: list[dict]) -> list[tuple[str, dict | None]]:
    """[(형태, 그 문법 쪽)] — 문법(문형) 쪽 머리 + 학습목표 줄. 학습목표에만 있는 것(부가 문법)은 쪽이 없다."""
    cands: list[tuple[str, dict | None]] = []
    for page in pages:
        lines = _lines(page["text"])
        for i, line in enumerate(lines[:-1]):
            if GRAMMAR_HEAD.match(line):
                cands += [(form, page) for form in _forms(lines[i + 1])]
    for page in pages:
        for match in GOAL.finditer(" ".join(_lines(page["text"]))):
            cands += [(form, None) for form in _forms(match.group(1))]
    return cands


def fragments(form: str) -> list[str]:
    """
    5~6급 문형은 여러 조각이다: "...은 -는다는 것이다" → ["-는다는 것이다"], "-게끔 -어야 하다" → ["-게끔", "-어야 하다"],
    "...은 ...에 비해 -는다는 장점/단점이 있다" → ["에 비해", "-는다는 장점이 있다", …]. "..." 자리와 그 뒤 조사는 버린다.
    """
    out = []
    for segment in re.split(r"\.{2,}|…", form):
        segment = re.sub(r"^(?:은|는|을|를|이|가)\s+", "", segment.strip())
        for piece in re.split(r"\s+(?=-)", segment):
            out += _clean_form(piece)
    return [f for f in dict.fromkeys(out) if f and f != form]


def _standard(cand: str) -> tuple[str, list[dict]] | None:
    matched = match_forms([cand])
    if not matched:
        return None
    std = [headword_item(k) for k in sorted(set(matched[0]["keys"])) if _standard_by_key().get(k)]
    return (matched[0]["form"], std) if std else None


def match_standard(cand: str) -> tuple[str, list[dict]] | None:
    """
    형태 → (대표형, 표준 항목들). 여러 조각 문형은 조각으로 맞추고, 조각에서 찾은 것 중 등급이 가장 높은 하나만 쓴다.
    통째로 맞추지 않는 이유: match_forms는 뒤를 잘라 가며 맞추고 앞 낱말을 버려서 "-게끔 -어야 하다"를 "-게"로,
    "과연 -을까"를 "-을까"로 맞춘다.
    """
    if not COMPOUND.search(cand):
        return _standard(cand)
    parts = [found for piece in fragments(cand) if (found := _standard(piece))]
    parts = [p for p in parts if max(i["level"] for i in p[1]) >= MIN_FRAGMENT_LEVEL]
    if not parts:
        return None
    form, std = max(parts, key=lambda p: max(i["level"] for i in p[1]))
    return cand, std


def grammar_items(pages: list[dict]) -> list[dict]:
    """[{form, standard_ids, level, page}] — 표준 문법 목록에 맞춘다. 같은 표준 항목은 한 번만."""
    found, seen = [], set()
    for cand, page in grammar_candidates(pages):
        matched = match_standard(cand)
        if not matched:
            continue
        form, std = matched
        ids = [item["id"] for item in std if item["id"] not in seen]
        if not ids:
            # 학습목표에서 먼저 찾았으면 문법 쪽은 나중에 붙인다
            if page:
                for item in found:
                    if item["page"] is None and set(item["standard_ids"]) & {i["id"] for i in std}:
                        item["page"] = page
            continue
        seen.update(ids)
        found.append({"form": form, "standard_ids": ids, "level": min(i["level"] for i in std), "page": page})
    return found


def grammar_examples(form: str, page: dict | None) -> list[str]:
    """문법 쪽에서 목표 형태의 글자가 보이는 문장 ("명동에 가려면 몇 번 버스를 타야 해요?")"""
    if not page:
        return []
    surface = max(form.replace("-", " ").split(), key=len)  # "-는 한이 있어도" → "있어도" (짧은 "는"은 아무 문장에나 있다)
    surface = surface[:-1] if surface.endswith("다") and len(surface) > 1 else surface
    surface = surface[1:] if surface[0] in "으을은" and len(surface) > 2 else surface  # "-으려면" → "려면" (가려면)
    out = []
    for line in _lines(page["text"]):
        sentence = BULLET.sub("", line)
        if any(word in sentence for word in NOT_EXAMPLE):
            continue
        if 6 <= len(sentence) <= 80 and not sentence.startswith("-") and SENTENCE.search(sentence) and surface in sentence and "세요" not in sentence[-4:]:
            out.append(sentence)
    return list(dict.fromkeys(out))[:MAX_EXAMPLES]


def grammar_description(page: dict | None) -> str:
    """문법 쪽의 한국어 설명 줄 (영어 번역 줄은 뺀다)"""
    if not page:
        return ""
    return "\n".join(line for line in _lines(page["text"]) if re.search(r"[가-힣]", line))[:600]


# ── 어휘 ──────────────────────────────────────────────────────────────


def vocab_regions(pages: list[dict]) -> list[dict]:
    """어휘 머리("Vocabulary", "어휘를 배워 봅시다.")가 있는 쪽부터 문법·어휘 연습 쪽 앞까지"""
    out, inside = [], False
    for page in pages:
        lines = _lines(page["text"])
        if any(VOCAB_HEAD.match(line) for line in lines):
            inside = True
        elif any(VOCAB_END.match(line) for line in lines[:3]):
            inside = False
        if inside:
            out.append(page)
    return out


def lookup_words(entry: str) -> list[tuple[str, dict | None]]:
    """
    교재 표제 → [(낱말, 표준 어휘)]. 표제가 통째로 목록에 있으면 그것 하나.
    "가입 (하다)" → 가입하다 / "정규직/비정규직" → 둘 다 / "연봉이 높다" → 연봉 (마지막 서술어는 이 과의 새 낱말이 아니다)
    """
    entry = entry.strip()
    if m := re.fullmatch(r"(.+?)\s*\(하다\)", entry):
        word = m.group(1)
        return [(f"{word}하다", standard_vocab(f"{word}하다"))] if standard_vocab(f"{word}하다") else [(word, standard_vocab(word))]
    if std := standard_vocab(entry):
        return [(entry, std)]
    tokens = entry.split()
    heads = tokens[:-1] if len(tokens) > 1 else tokens
    out = []
    for token in heads:
        for part in token.split("/"):
            part = part.strip()
            for cand in (part, PARTICLE.sub("", part), re.sub(r"이다$", "", part)):
                if cand and (std := standard_vocab(cand)):
                    out.append((cand, std))
                    break
    return out or [(entry, None)]


def vocab_entries(pages: list[dict]) -> list[tuple[str, str, dict]]:
    """[(교재 표제, 예문, 쪽)] — 3A~4B "낱말 줄 + • 예문 줄", 5A~6B "• 표제 줄 + 예문 줄"."""
    out, seen = [], set()
    for page in vocab_regions(pages):
        lines = _lines(page["text"])
        for i, line in enumerate(lines[:-1]):
            nxt = lines[i + 1]
            if WORD.match(line) and BULLET.match(nxt):  # 3A~4B
                entry, example = line, BULLET.sub("", nxt)
            elif BULLET.match(line) and not BULLET.match(nxt) and len(BULLET.sub("", line)) <= 20 and SENTENCE.search(nxt) and len(nxt) > 10:  # 5A~6B
                entry, example = BULLET.sub("", line), nxt
            else:
                continue
            if entry not in seen and entry not in SECTION_LABELS and not entry.endswith("어휘"):
                seen.add(entry)
                out.append((entry, example, page))
    return out
