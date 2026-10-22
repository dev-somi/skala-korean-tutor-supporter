"""
이 파일의 역할: 문법 질문 답변 (PRD F6-4). "-아서랑 -(으)니까 뭐가 달라?" → 교재 근거 + 차이 정리.

흐름은 코드가 정한다 (기술 ADR-0013, 0025). LLM은 형태를 못 찾았을 때 한 번, 정리할 때 한 번만 부른다.
  1. 형태 뽑기   질문 → 형태 키 (app.rag.forms). 색인 태그·표준 목록에 있는 키만 인정한다.
                 못 찾으면 저가 모델 → 다시 코드로 확인 (권위 게이트)
  2. 근거 모으기 형태 키 → 핸드북(teaches 필터, 학생 모국어 설명) + 지침서(teaches 필터, 비교 대상을 언급한 구역 먼저.
                 없으면 의미 검색 중 그 형태를 언급한 구역) + 모국어 노트(l1_notes)
  3. 등급 확인   형태 키가 표준 목록과 맞으면 가장 낮은 등급. 학생 등급보다 높으면 out_of_level
  4. 정리        근거만 넣어 요점을 만들고, 근거에 없는 예문이 든 요점은 코드가 뺀다

출처와 인용은 코드가 parent에서 잘라 붙인다 (LLM이 지어내지 않게). 형태 키는 화면에 보이지 않는다.
분기·루프가 없어서 그래프 대신 함수로 둔다 (intake와 같은 방식).
"""

import os
import re
from functools import lru_cache

from langsmith import traceable
from pydantic import BaseModel, Field

from app.agent.lesson_prep import llm
from app.rag import index as rag_index
from app.rag.forms import form_keys, quoted_forms
from app.rag.handbook import split_item
from app.standard import l1_notes
from app.standard.levels import grammar_items

MAX_FORMS = 4  # 한 질문에서 비교할 문법 수 ("너라면, 너라서, 너니까, 너거나")
MAX_HANDBOOK = 2  # 형태 하나에 붙일 핸드북 항목 수 (1권 기본 + 2권 확장·비교)
MAX_GUIDE = 2  # 형태 하나에 붙일 지침서 구역 수
QUOTE_CHARS = 700  # 지침서 인용 길이

HYPHEN_FORM = re.compile(r"-(?:\(으\)|\(이\))?(?:[가-힣]/)*[가-힣ㄴㄹㅂ]+(?:\s[가-힣]+)?-?")  # -아서, -(으)니까, -던-, -기 나름이다, -아/어서
SLASH_FORM = re.compile(r"(?<![-/가-힣])[가-힣]+(?:/[가-힣]+)+")  # 은/는, 이/가 (-아/어서 의 뒷부분은 빼고)
QUOTED_FORM = re.compile(r"['‘\"“「]([가-힣]{1,4})['’\"”」]")  # '도'
LIST_SEP = re.compile(r"[\s,，、/]+")  # 너라면, 너라서 / 너라면 너라서


class FormsDraft(BaseModel):
    forms: list[str] = Field(
        description='질문이 묻는 문법(어미·조사·표현)을 기본형으로. 활용형이면 어미만 떼어 쓴다. 예: "사는" → "-는", "살던" → "-던", "살아서" → "-아서", "을/를". 최대 3개'
    )


class FormUsage(BaseModel):
    form: str = Field(description='근거 자료 제목(## 뒤)의 문법 표기 그대로. 예: "-라서"')
    usage: str = Field(description="이 문법이 언제 쓰이는지 한 줄 (25자 안팎, \"뜻 · 쓰임 조건\" 모양). 그 문법의 근거 자료에서만")


class GrammarAnswer(BaseModel):
    """
    화면은 비교표(문법·등급·쓰임·교재 예문) → 핵심 차이 → 근거(접힘)다 (기술 ADR-0043).
    예문은 LLM이 쓰지 않고 코드가 핸드북 예문을 넣는다. 학생 모국어 설명도 핸드북 원문(explain_native)을 그대로 보여 준다.
    """

    forms: list[FormUsage] = Field(description="근거 자료의 문법마다 하나씩, 쓰임 한 줄")
    differences: list[str] = Field(description="문법끼리 무엇이 다른지 한 문장씩 1~3개. 문법이 하나면 가르칠 때 주의할 점. 근거 자료에 있는 내용만")
    ai_note: str = Field(default="", description="근거 자료에 없지만 보충한 내용. 없으면 빈 문자열")


class AiFormExplanation(BaseModel):
    form: str = Field(description="질문에 나온 문법 표기 그대로")
    usage: str = Field(description='언제 쓰는지 한 줄 ("뜻 · 쓰임 조건", 25자 안팎)')
    explanation: str = Field(description="선생님이 학생에게 설명할 말 2~3문장 (한국어)")
    examples: list[str] = Field(description="그 문법이 든 짧은 해요체 예문 1~2개")
    caution: str = Field(default="", description="자주 틀리는 점이나 확인이 필요한 점 한 문장. 없으면 빈 문자열")


class AiExplanation(BaseModel):
    """교재 근거가 없는 문법의 AI 설명 (기획 ADR-0036). 화면에서 "AI 설명 · 검수 필요"로 따로 보인다. 학생 모국어 설명은 쓰지 않는다."""

    forms: list[AiFormExplanation]
    comparison: str = Field(default="", description="질문이 차이를 물으면 이 문법들과 다른 문법의 차이 한두 문장. 아니면 빈 문자열")


SENSE_NO = re.compile(r"\d+(?:\(\d+\))?$")  # 표준 목록의 뜻 번호: "-다가1(1)", "-다가1(2)"
ALT_FORM = re.compile(r"^([^()]+)\(([가-힣]{2,})\)$")  # 다른 꼴: "에서부터(서부터)" ("-(으)면"의 (으)는 아님)


def standard_forms(form: str) -> list[str]:
    """표준 목록의 표제 형태 → 형태 키로 바꿀 수 있는 꼴들"""
    form = SENSE_NO.sub("", form)
    match = ALT_FORM.match(form)
    return [match.group(1), match.group(2)] if match else [form]


@lru_cache
def _standard_by_key() -> dict[str, list[dict]]:
    """형태 키 → 표준 문법 항목들 (등급이 낮은 것부터). 등급 표시용일 뿐 검색 키가 아니다 (기술 ADR-0025 결정 6)."""
    table: dict[str, list[dict]] = {}
    for item in sorted(grammar_items(), key=lambda i: i["level"]):
        for form in [alt for f in [item["form"], *item["related"]] for alt in standard_forms(f)]:
            for key in form_keys(form):
                if item not in table.setdefault(key, []):
                    table[key].append(item)
    return table


def known(keys: set[str]) -> set[str]:
    """색인 태그나 표준 목록에 있는 키만 남긴다."""
    return {key for key in keys if key in rag_index.known_keys() or key in _standard_by_key()}


def _match_part(part: str) -> tuple[str, set[str]]:
    """형태 하나 → (맞은 형태, 키). "-아서랑"처럼 조사가 붙어 있으면 뒤에서부터 한 글자씩 떼며 맞춘다."""
    while part:
        keys = known(form_keys(part))
        if keys and " " in part and known(form_keys(part.rsplit(" ", 1)[0])) == keys:
            return part.rsplit(" ", 1)[0], keys  # "-어/아서 어떻게" → "-어/아서" (뒤 낱말이 키를 안 바꾸면 뗀다)
        if keys or not part.startswith("-") or len(part) <= 2:
            return part, keys
        part = part[:-1].rstrip()
    return part, set()


def match_forms(candidates: list[str]) -> list[dict]:
    """후보 형태들 → [{form, keys, level, meaning}]. 아는 형태가 아니면 버린다. "이/가"는 조각 중 하나라도 맞으면 된다."""
    found, seen = [], set()
    for cand in candidates:
        parts = cand.split("/") if "/" in cand and not cand.startswith("-") else [cand]
        keys, matched = set(), []
        for part in parts:
            part, part_keys = _match_part(part.strip())
            if part_keys:
                matched.append(part)
                keys |= part_keys
        if not keys or frozenset(keys) in seen:
            continue
        seen.add(frozenset(keys))
        items = [item for key in sorted(keys) for item in _standard_by_key().get(key, [])]
        lowest = min(items, key=lambda i: i["level"]) if items else None
        # 관련형으로 맞았으면 ("-라서" → -어서 항목) 대표형 키로도 교재를 찾는다. 교재는 대표형 제목으로 가르친다
        head = SENSE_NO.sub("", lowest["form"]) if lowest else None
        head_keys = {k for f in standard_forms(lowest["form"]) for k in form_keys(f)} if lowest else set()
        found.append(
            {
                "form": "/".join(matched),
                "keys": sorted(keys),
                "search_keys": sorted(keys | head_keys),
                "standard_form": head if head_keys - keys else None,  # 대표형이 다를 때만 ("-라서"의 "-어서")
                "level": lowest["level"] if lowest else None,  # 표준 목록에 없으면 등급을 모른다
                "meaning": lowest.get("meaning") if lowest else None,
            }
        )
    return found[:MAX_FORMS]


def listed_endings(question: str) -> list[str]:
    """
    "너라면, 너라서, 너니까"처럼 같은 말에 끝만 바꿔 나열하면, 같은 앞부분을 떼고 남은 끝을 어미로 본다 → -라면, -라서, -니까.
    명사 뒤의 "이"는 서술격 조사 '이다'라서 뗀다: "학생이라서" → "-라서" (받침 없는 명사 뒤에서는 원래 빠진다: "너라서").
    쉼표·띄어쓰기 어느 쪽으로 나열해도 된다. 이어진 낱말 중 앞부분이 같은 묶음만 보고, 끝이 2개 이상 맞아야 쓴다.
    끝을 그대로 키로 맞춰 볼 뿐 자르지 않는다 (아는 형태가 아니면 버린다).
    """
    out = []
    for line in question.splitlines():
        words = [w for w in LIST_SEP.split(line) if re.fullmatch(r"[가-힣]+", w)]
        i = 0
        while i < len(words):
            j = i + 1  # words[i:j]: 앞부분이 같은 이어진 낱말 묶음
            while j < len(words) and os.path.commonprefix(words[i : j + 1]):
                j += 1
            group, i = words[i:j], max(j, i + 1)
            stem = os.path.commonprefix(group)
            if len(group) < 2 or any(len(w) == len(stem) for w in group):
                continue
            endings = [_ending(w[len(stem):]) for w in group]
            if sum(e is not None for e in endings) >= 2:
                out += [e for e in endings if e]
    return out


def _ending(tail: str) -> str | None:
    """나열에서 뗀 끝 → 아는 어미. 명사 뒤 "이"(이다)는 떼고, 묻는 말에 붙은 조사("먹어서랑")도 떼어 본다."""
    for t in [tail, re.sub(r"(이랑|랑|하고|와|과)$", "", tail)]:
        for cand in [f"-{t}", f"-{t[1:]}" if t.startswith("이") and len(t) > 1 else None]:
            if cand and len(cand) > 1 and known(form_keys(cand)):
                return cand
    return None


LINK = re.compile(r"(이랑|랑|하고|와|과)$")  # "라면이랑 니까" 의 이랑
OBJECT = re.compile(r"(을|를|은|는|이|가|의|이랑|랑|하고|와|과)$")  # "니까를" 의 를


def paired_forms(question: str) -> list[str]:
    """
    "라면이랑 니까를 어떻게 설명해?"처럼 형태를 맨몸으로 "A랑 B" 비교하면, 붙은 조사를 떼고 두 낱말을 형태로 맞춘다.
    한 글자 조사("은이랑 는")는 조사로, 나머지는 어미로 먼저 본다 ("라면" → -라면). 둘 다 맞아야 쓴다 ("나랑 너" 같은 말을 거른다).
    """
    words = re.findall(r"[가-힣]+", question)
    out = []
    for a, b in zip(words, words[1:]):
        if not LINK.search(a):
            continue
        a, b = LINK.sub("", a), b if _bare_form(b) else OBJECT.sub("", b)
        left, right = _bare_form(a), _bare_form(b)
        if left and right:
            if left.startswith("-") != right.startswith("-"):  # 짝이 어미면 한 글자도 어미로 ("다가랑 고" → -고)
                left, right = _bare_form(a, ending=True) or left, _bare_form(b, ending=True) or right
            out += [left, right]
    return out


def _bare_form(word: str, ending: bool = False) -> str | None:
    if not word:
        return None
    if len(word) == 1 and not ending and known(form_keys(word)):
        return word  # 은, 는, 도
    if known(form_keys(f"-{word}")):
        return f"-{word}"
    return word if known(form_keys(word)) else None


def forms_in_text(question: str) -> list[str]:
    """질문에 형태가 적혀 있으면 코드로 뽑는다 (-아서, 은/는, '도', 너라면·너라서, 라면이랑 니까)."""
    return (
        HYPHEN_FORM.findall(question) + SLASH_FORM.findall(question) + QUOTED_FORM.findall(question)
        + listed_endings(question) + paired_forms(question)
    )


@traceable(run_type="tool")
def extract_forms(question: str) -> list[dict]:
    found = match_forms(forms_in_text(question))
    if found and HYPHEN_FORM.search(question) or len(found) >= 2:  # 형태를 직접 적은 질문은 그대로 믿는다
        return found
    # "사는이랑 살던"처럼 활용형으로 물으면 저가 모델이 어미를 떼고, 코드가 다시 확인한다
    raw = llm.call_llm("grammar_forms", FormsDraft, {"question": question}, tier="fast")
    return match_forms([form for form in raw["forms"] if in_question(form, question)]) or found


def in_question(form: str, question: str) -> bool:
    """LLM이 뽑은 형태의 글자가 질문 낱말 속(첫 글자 뒤)에 보이는지. "이거 어떻게 가르쳐?"의 '가르쳐'에서 -어/아서를 지어내는 것을 막는다.
    "사는"의 는, "살아서"·"가서"의 서, "제가"의 가는 통과한다."""
    chars = set(re.sub(r"[^가-힣]", "", form))
    return any(chars & set(word[1:]) for word in re.findall(r"[가-힣]+", question))


def excerpt(text: str, keys: set[str]) -> str:
    """구역 글에서 그 형태가 처음 나오는 줄부터 잘라 인용한다. 한 쪽에 문법이 여러 개인 매뉴얼에 필요하다."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if keys & (quoted_forms(line) | form_keys(re.sub(r"^\d\.\s*", "", line.strip()))):
            return "\n".join(lines[i:])[:QUOTE_CHARS]
    return text[:QUOTE_CHARS]


def text_pattern(form: str) -> re.Pattern | None:
    """"-을래야" → 본문에서 '-을래야', ‘을래야’처럼 붙임표나 여는 따옴표 바로 뒤에 적힌 꼴. 두 글자 미만(조사 '도')은 너무 흔해서 찾지 않는다.
    "-(으)니까"는 "으니까", "니까" 둘 다. "-아서/-어서"는 조각마다."""
    surfaces = set()
    for part in form.split("/"):
        part = part.strip().lstrip("-")
        for v in {OPTIONAL_PART.sub(r"\1", part), OPTIONAL_PART.sub("", part)}:
            if len(v) >= 2 and re.fullmatch(r"[가-힣 ]+", v):
                surfaces.add(v)
    if not surfaces:
        return None
    return re.compile(r"[-'‘\"“「]\s*(?:" + "|".join(map(re.escape, sorted(surfaces, key=len, reverse=True))) + r")(?![가-힣])")


OPTIONAL_PART = re.compile(r"\(([가-힣]{1,2})\)")


TEXT_BEFORE = 450  # 글자로 찾은 자리 앞쪽 인용 길이. "말할 때 -을래야로 발음" 같은 덧붙임 줄 위에 본 설명(-으려야)이 있다


def text_excerpt(text: str, pattern: re.Pattern) -> str:
    """그 형태가 처음 나온 자리 앞뒤를 줄 단위로 잘라 인용한다."""
    match = pattern.search(text)
    if not match:
        return text[:QUOTE_CHARS]
    start = text.rfind("\n", 0, max(match.start() - TEXT_BEFORE, 0)) + 1
    return text[start : start + QUOTE_CHARS]


@traceable(run_type="tool")
def collect_evidence(form: dict, others: set[str], lang: str) -> dict:
    """형태 하나의 근거. others = 같은 질문의 다른 형태 키 (그 형태를 언급한 비교 설명을 앞에 둔다).
    관련형이면 대표형 키로도 찾는다 ("-라서" → -어서 구역)."""
    keys = set(form.get("search_keys", form["keys"]))
    sources = []
    for h in rag_index.find_by_form(keys, kind="handbook", others=others)[:MAX_HANDBOOK]:
        part = split_item(h["text"], h["section"])
        translations = h.get("translations", {})
        native_lang = lang if lang in translations else next(iter(translations), None)
        sources.append(
            {
                "kind": "handbook",
                "source": h["source"],
                "book": h["book"],
                "pages": h["pages"],
                "examples": part["examples"],
                "explain_ko": part["explain_ko"],
                "explain_native": translations.get(native_lang, "") if native_lang else "",
                "native_lang": native_lang,
            }
        )

    guides = rag_index.find_by_form(keys, kind="guide", others=others)[:MAX_GUIDE]
    if guides:
        sources += [{"kind": "guide", "source": g["source"], "book": g["book"], "pages": g["pages"], "quote": excerpt(g["text"], keys)} for g in guides]
    else:
        # 태그가 없으면 의미 검색으로 찾되, 그 형태를 본문에 언급한 구역만 쓴다 ("-는"이 "-는데" 구역을 끌어오지 않게)
        for found in rag_index.search(f"{form['form']} 문법 설명", k=5, kind="guide"):
            if keys & set(found.get("mentions", [])):
                sources.append({"kind": "guide", "source": found["source"], "book": found["book"], "pages": found["pages"], "quote": excerpt(found["text"], keys)})
                break

    if not sources and (pattern := text_pattern(form["form"])):
        # 그래도 없으면 본문에 그 형태 글자가 붙임표·따옴표와 함께 적힌 구역 (태그가 빠진 구역, 기술 ADR-0044)
        for found in rag_index.find_by_text(pattern, f"{form['form']} 문법 설명", k=MAX_GUIDE):
            sources.append({"kind": "text", "source": found["source"], "book": found["book"], "pages": found["pages"], "quote": text_excerpt(found["text"], pattern)})

    notes = l1_notes.notes_for_keys(keys, lang)
    return {
        "form": form["form"],
        "key": "|".join(form["keys"]),
        "level": form["level"],
        "meaning": form["meaning"],
        "standard_form": form.get("standard_form"),
        "sources": sources,
        "l1_notes": notes,
        "grounded": bool(sources or notes),
    }


def _evidence_text(evidence: list[dict]) -> str:
    blocks = []
    for ev in evidence:
        level = f"표준 {ev['level']}급" if ev["level"] is not None else "등급 모름"
        head = f"## {ev['form']} ({level}{' · ' + ev['meaning'] if ev['meaning'] else ''})"
        if ev.get("standard_form"):
            head += f"\n{ev['form']}은 {ev['standard_form']}의 관련형이다. 아래 근거는 {ev['standard_form']}을 설명한다."
        body = []
        for src in ev["sources"]:
            if src["kind"] == "handbook":
                body.append(f"[{src['source']}]\n예문: {' / '.join(src['examples'])}\n설명: {src['explain_ko']}\n모국어 설명: {src['explain_native']}")
            elif src["kind"] == "text":
                body.append(f"[{src['source']} · 본문에 '{ev['form']}'가 나온 곳. 이 문법(또는 같은 뜻의 표준 표기)을 설명한 부분만 쓴다]\n{src['quote']}")
            else:
                body.append(f"[{src['source']}]\n{src['quote']}")
        for note in ev["l1_notes"]:
            body.append("[검수 데이터] 자주 틀리는 점: " + " / ".join(note.get("common_mistakes", [])) + f"\n설명 팁: {note.get('explain_tip', '')}")
        blocks.append(head + "\n" + ("\n\n".join(body) if body else "(근거 자료 없음)"))
    return "\n\n".join(blocks)


EXAMPLE_PREFIX = re.compile(r"^[•·\-\s]*(?:[가-힣]{1,2}\s*:\s*)?")  # "• 가: ", "나: "


def first_example(ev: dict) -> str:
    """비교표의 교재 예문: 핸드북 예문 중 첫 대답 줄 ("가: 왜 배워요?" 같은 질문 줄은 건너뛴다). LLM이 만들지 않는다 (기획 ADR-0017)."""
    examples = [EXAMPLE_PREFIX.sub("", ex).strip() for src in ev["sources"] if src["kind"] == "handbook" for ex in src["examples"]]
    examples = [ex for ex in examples if ex]
    return next((ex for ex in examples if not ex.endswith("?")), examples[0] if examples else "")


QUOTE_MARK = re.compile(r"['‘’\"“”]")
SENTENCE = re.compile(r"[가-힣].*\s.*[가-힣](요|다|까)[.?!]?$")  # 띄어쓰기가 있고 문장 어미로 끝나면 예문


def quoted_sentences(answer: str) -> list[str]:
    """따옴표를 앞에서부터 둘씩 짝지어 인용을 뽑고, 그중 예문 모양인 것만. ('사는' 같은 한 단어 인용과 섞여도 짝이 어긋나지 않게)"""
    marks = [m.start() for m in QUOTE_MARK.finditer(answer)]
    spans = [answer[a + 1 : b] for a, b in zip(marks[::2], marks[1::2])]
    return [span for span in spans if SENTENCE.search(span.strip())]


@traceable(run_type="tool")
def check_examples(points: list[str], evidence_text: str) -> tuple[list[str], list[str]]:
    """
    권위 게이트: 요점에 인용한 예문이 근거 자료에 있는지 코드가 확인한다 (기획 ADR-0017: 예문은 만들지 않고 찾는다).
    근거에 없는 예문이 든 요점은 통째로 빼서 따로 돌려준다. 띄어쓰기·문장부호는 무시하고 비교한다.
    """
    def norm(text: str) -> str:
        return re.sub(r"[^가-힣]", "", text)

    pool = norm(evidence_text)
    kept, removed = [], []
    for point in points:
        if any(norm(sentence) not in pool for sentence in quoted_sentences(point)):
            removed.append(point)
        else:
            kept.append(point)
    return kept, removed


@traceable(name="grammar_qa")
def answer_question(question: str, native_language: str = "ja", student_level: int | None = None) -> dict:
    forms = extract_forms(question)
    if not forms:
        return {
            "points": ["어떤 문법을 묻는지 찾지 못했어요. '-아서', '은/는'처럼 형태를 적어서 다시 물어봐 주세요."],
            "ai_note": "",
            "removed_points": [],
            "forms": [],
            "out_of_level": [],
            "ungrounded_forms": [],
            "grounded": False,
        }

    all_keys = {key for form in forms for key in form["search_keys"]}
    evidence = [collect_evidence(form, all_keys - set(form["search_keys"]), native_language) for form in forms]
    out_of_level = [
        {"form": ev["form"], "level": ev["level"]}
        for ev in evidence
        if student_level is not None and ev["level"] is not None and ev["level"] > student_level
    ]
    # 근거가 하나도 없으면 근거 정리는 건너뛰고 AI 설명만 만든다
    result = llm.call_llm(
        "grammar_answer",
        GrammarAnswer,
        {
            "question": question,
            "lang_name": llm.LANG_NAMES.get(native_language, native_language),
            "evidence": _evidence_text(evidence),
        },
    ) if any(ev["grounded"] for ev in evidence) else {"forms": [], "differences": [], "ai_note": ""}
    evidence_text = _evidence_text(evidence)
    points, removed = check_examples(result["differences"], evidence_text)
    usages = {u["form"].strip(): u["usage"].strip() for u in result["forms"]}
    for ev in evidence:
        usage = usages.get(ev["form"], "")
        ev["usage"] = usage if usage and not check_examples([usage], evidence_text)[1] else ""
        ev["example"] = first_example(ev)
    ungrounded = [ev["form"] for ev in evidence if not ev["grounded"]]
    ai_comparison = explain_ungrounded(question, evidence, native_language) if ungrounded else ""
    return {
        "points": points,  # 핵심 차이 (Spring이 글로 보낸다)
        "ai_note": "\n".join(note for note in [result.get("ai_note", "").strip(), ai_comparison] if note and "근거 자료 없음" not in note),
        "removed_points": removed,  # 근거에 없는 예문이 들어 있어 뺀 요점 (화면에 "검수 필요"로)
        "forms": evidence,
        "out_of_level": out_of_level,
        "ungrounded_forms": ungrounded,  # 교재 근거가 없는 형태: 이 형태에 대한 요점은 AI 설명이다
        "grounded": not ungrounded,
    }


@traceable(run_type="tool")
def explain_ungrounded(question: str, evidence: list[dict], lang: str) -> str:
    """
    교재 근거가 없는 문법은 AI가 설명을 만든다 (기획 ADR-0036). 시스템 프롬프트에 역할·규칙을 두고 한 번 부른다.
    결과는 그 형태의 ev["ai"]에 붙는다 (화면은 "AI 설명 · 검수 필요", 예문은 "AI 예문"). 교재 예문 칸(ev["example"])에는 넣지 않는다.
    돌려주는 값은 문법끼리 차이(comparison) — ai_note에 붙인다.
    """
    targets = [ev for ev in evidence if not ev["grounded"]]
    result = llm.call_llm(
        "grammar_ai_explain",
        AiExplanation,
        {
            "question": question,
            "forms": ", ".join(ev["form"] for ev in targets),
            "grounded_forms": ", ".join(ev["form"] for ev in evidence if ev["grounded"]) or "없음",
            "lang_name": llm.LANG_NAMES.get(lang, lang),
        },
        system="grammar_ai_system",
    )
    by_form = {item["form"].strip(): item for item in result["forms"]}
    if len(targets) == len(result["forms"]):  # 표기를 바꿔 답해도 ("라면" → "-라면") 순서로 맞춘다
        by_form = {ev["form"]: by_form.get(ev["form"], item) for ev, item in zip(targets, result["forms"])}
    for ev in targets:
        if item := by_form.get(ev["form"]):
            ev["ai"] = {
                "usage": item["usage"].strip(),
                "explanation": item["explanation"].strip(),
                "examples": [ex.strip() for ex in item["examples"] if ex.strip()][:2],
                "caution": item["caution"].strip(),
            }
    return result.get("comparison", "").strip()

