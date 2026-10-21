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

MAX_FORMS = 3  # 한 질문에서 비교할 문법 수
MAX_HANDBOOK = 2  # 형태 하나에 붙일 핸드북 항목 수 (1권 기본 + 2권 확장·비교)
MAX_GUIDE = 2  # 형태 하나에 붙일 지침서 구역 수
QUOTE_CHARS = 700  # 지침서 인용 길이

HYPHEN_FORM = re.compile(r"-(?:\(으\)|\(이\))?(?:[가-힣]/)*[가-힣ㄴㄹㅂ]+(?:\s[가-힣]+)?-?")  # -아서, -(으)니까, -던-, -기 나름이다, -아/어서
SLASH_FORM = re.compile(r"(?<![-/가-힣])[가-힣]+(?:/[가-힣]+)+")  # 은/는, 이/가 (-아/어서 의 뒷부분은 빼고)
QUOTED_FORM = re.compile(r"['‘\"“「]([가-힣]{1,4})['’\"”」]")  # '도'


class FormsDraft(BaseModel):
    forms: list[str] = Field(
        description='질문이 묻는 문법(어미·조사·표현)을 기본형으로. 활용형이면 어미만 떼어 쓴다. 예: "사는" → "-는", "살던" → "-던", "살아서" → "-아서", "을/를". 최대 3개'
    )


class GrammarAnswer(BaseModel):
    """학생 모국어 설명은 LLM에게 맡기지 않는다. 핸드북 원문(explain_native)을 코드가 그대로 보여 준다 (작은 모델의 일본어가 틀린다)."""

    points: list[str] = Field(description="쓰임과 차이를 한국어 요점 2~4개로. 요점 하나는 한 문장. 근거 자료에 있는 내용과 예문만")
    ai_note: str = Field(default="", description="근거 자료에 없지만 보충한 내용. 없으면 빈 문자열")


@lru_cache
def _standard_by_key() -> dict[str, list[dict]]:
    """형태 키 → 표준 문법 항목들 (등급이 낮은 것부터). 등급 표시용일 뿐 검색 키가 아니다 (기술 ADR-0025 결정 6)."""
    table: dict[str, list[dict]] = {}
    for item in sorted(grammar_items(), key=lambda i: i["level"]):
        for form in [item["form"], *item["related"]]:
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
        found.append(
            {
                "form": "/".join(matched),
                "keys": sorted(keys),
                "level": lowest["level"] if lowest else None,  # 표준 목록에 없으면 등급을 모른다
                "meaning": lowest.get("meaning") if lowest else None,
            }
        )
    return found[:MAX_FORMS]


def forms_in_text(question: str) -> list[str]:
    """질문에 형태가 적혀 있으면 코드로 뽑는다 (-아서, 은/는, '도')."""
    return HYPHEN_FORM.findall(question) + SLASH_FORM.findall(question) + QUOTED_FORM.findall(question)


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


@traceable(run_type="tool")
def collect_evidence(form: dict, others: set[str], lang: str) -> dict:
    """형태 하나의 근거. others = 같은 질문의 다른 형태 키 (그 형태를 언급한 비교 설명을 앞에 둔다)."""
    keys = set(form["keys"])
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

    notes = l1_notes.notes_for_keys(keys, lang)
    return {
        "form": form["form"],
        "key": "|".join(form["keys"]),
        "level": form["level"],
        "meaning": form["meaning"],
        "sources": sources,
        "l1_notes": notes,
        "grounded": bool(sources or notes),
    }


def _evidence_text(evidence: list[dict]) -> str:
    blocks = []
    for ev in evidence:
        level = f"표준 {ev['level']}급" if ev["level"] is not None else "등급 모름"
        head = f"## {ev['form']} ({level}{' · ' + ev['meaning'] if ev['meaning'] else ''})"
        body = []
        for src in ev["sources"]:
            if src["kind"] == "handbook":
                body.append(f"[{src['source']}]\n예문: {' / '.join(src['examples'])}\n설명: {src['explain_ko']}\n모국어 설명: {src['explain_native']}")
            else:
                body.append(f"[{src['source']}]\n{src['quote']}")
        for note in ev["l1_notes"]:
            body.append("[검수 데이터] 자주 틀리는 점: " + " / ".join(note.get("common_mistakes", [])) + f"\n설명 팁: {note.get('explain_tip', '')}")
        blocks.append(head + "\n" + ("\n\n".join(body) if body else "(근거 자료 없음)"))
    return "\n\n".join(blocks)


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

    all_keys = {key for form in forms for key in form["keys"]}
    evidence = [collect_evidence(form, all_keys - set(form["keys"]), native_language) for form in forms]
    out_of_level = [
        {"form": ev["form"], "level": ev["level"]}
        for ev in evidence
        if student_level is not None and ev["level"] is not None and ev["level"] > student_level
    ]
    result = llm.call_llm(
        "grammar_answer",
        GrammarAnswer,
        {
            "question": question,
            "lang_name": llm.LANG_NAMES.get(native_language, native_language),
            "evidence": _evidence_text(evidence),
        },
    )
    points, removed = check_examples(result["points"], _evidence_text(evidence))
    ungrounded = [ev["form"] for ev in evidence if not ev["grounded"]]
    return {
        "points": points,
        "ai_note": result.get("ai_note", ""),
        "removed_points": removed,  # 근거에 없는 예문이 들어 있어 뺀 요점 (화면에 "검수 필요"로)
        "forms": evidence,
        "out_of_level": out_of_level,
        "ungrounded_forms": ungrounded,  # 교재 근거가 없는 형태: 이 형태에 대한 요점은 AI 설명이다
        "grounded": not ungrounded,
    }

