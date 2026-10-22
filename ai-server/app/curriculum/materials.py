"""
이 파일의 역할: 본책·익힘책 OCR 쪽에서 단원 시트의 대화·읽기·연습을 코드 규칙으로 뽑는다. (기술 ADR-0032)

본책·익힘책은 한 쪽 = parent 하나로 색인돼 있다 (catalog.json, layout ocr_page). OCR에서 확인한 모양:
  - 연습: 한국어 지시문 다음 줄에 영어 번역 ("대화를 완성하세요." / "Complete the conversation.")
  - 읽기: "글을 잘 읽으세요." 다음의 글
  - 대화: 본책 뒤 정답·지문 부록에 과마다 "N과:제목" → "듣고 말하기 지문" → "쯔엉 안녕하세요? …" (말하는 사람 + 말)
OCR 글이라 빈칸·보기가 섞여 있다. 시트에는 원문 쪽(source)을 함께 둬서 선생님이 "원문"으로 확인한다.
"""

import re

from app.rag import index as rag_index

INSTRUCTION = re.compile(r"[가-힣].*(?:세요|보세요|하세요|쓰세요|고르세요|읽으세요|말해요|해요)\.?$")
ENGLISH = re.compile(r"^[A-Za-z][A-Za-z ,.'’()?!:/-]{6,}$")
NUMBERING = re.compile(r"^(?:\d{1,2}\s*[.)]?\s*|[①-⑩]\s*)")
QUESTION = re.compile(r"[가-힣]")
UNIT_LINE = re.compile(r"^(\d{1,2})과\s*[:·•]?\s*[가-힣]")  # "2과:회사원이…", "4과·여기가…", "3과 저도…" (OCR마다 다르다)
SCRIPT_HEAD = "듣고 말하기 지문"
SCRIPT_END = re.compile(r"^(?:\d{1,2}과\s*[:·•]?\s*[가-힣]|읽고 쓰기|문법 연습|어휘 및 문법 연습|듣고 말하기 연습|초급)")
# 듣기·읽기·말하기 지시문은 연습이 아니다 (대화·읽기·말하기 단계 자료)
NOT_EXERCISE = re.compile(r"들으세요|읽으세요|이야기해 보세요|말해 보세요")
MAX_PAGE_GAP = 40  # 과 번호를 잘못 읽은 앞쪽 쪽(목차 등)을 버리는 기준: 그 과 쪽들의 가운데에서 이만큼 넘게 떨어진 쪽
SPEAKER = re.compile(r"^([가-힣]{1,5})\s+(.+)$")
SENTENCE_END = re.compile(r"[요다까죠][.?!]?$|[.?!]$")
MAX_QUESTIONS = 8
MAX_SPEAKERS = 4


def unit_pages(book: str, unit_no: int) -> list[dict]:
    """그 책에서 과 번호가 unit_no인 쪽들 (책 순서)"""
    pages = sorted((p for p in rag_index.load_index()["parents"].values() if p["book"] == book and p["unit"] == unit_no), key=lambda p: p["pages"][0])
    if not pages:
        return []
    middle = pages[len(pages) // 2]["pages"][0]
    return [p for p in pages if abs(p["pages"][0] - middle) <= MAX_PAGE_GAP]


def exercises(pages: list[dict]) -> list[dict]:
    """[{instruction, questions, page, book}] — 지시문 + 영어 번역 줄이 붙은 곳마다 하나"""
    found = []
    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        starts = [i for i in range(len(lines) - 1) if INSTRUCTION.search(lines[i]) and ENGLISH.match(lines[i + 1]) and not NOT_EXERCISE.search(lines[i])]
        for n, i in enumerate(starts):
            end = starts[n + 1] if n + 1 < len(starts) else len(lines)
            body = [line for line in lines[i + 2 : end] if QUESTION.search(line) and not ENGLISH.match(line)]
            questions = [line for line in body if len(line) >= 3][:MAX_QUESTIONS]
            if questions:
                found.append({"instruction": NUMBERING.sub("", lines[i]), "questions": questions, "page": page["pages"][0], "book": page["book"]})
    return found


def readings(pages: list[dict]) -> list[dict]:
    """[{text, page, book}] — "글을 잘 읽으세요." 다음의 문장들 (문장으로 끝나는 줄만 이어 붙인다)"""
    found = []
    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        for i, line in enumerate(lines):
            if not line.startswith("글을 잘 읽으세요"):
                continue
            text = []
            for nxt in lines[i + 1 :]:
                if ENGLISH.match(nxt):
                    continue
                if not QUESTION.search(nxt) or len(nxt) < 8:
                    if text:
                        break  # 낱말 풀이("사진 picture")가 나오면 글이 끝난 것
                    continue
                text.append(nxt)
            if text:
                found.append({"text": " ".join(text), "page": page["pages"][0], "book": page["book"]})
    return found


def speaker_names(lines: list[str]) -> set[str]:
    """
    말하는 사람 이름: 앞 줄이 문장으로 끝난 뒤 줄 맨 앞에 두 번 이상 나온 낱말 (이름만 있는 줄 포함).
    한 번만 나온 낱말은 줄이 바뀐 문장의 첫 낱말("한국 드라마를…")일 수 있어 이름으로 보지 않는다.
    """
    counts: dict[str, int] = {}
    previous_ended = True
    for line in lines:
        first = line.split()[0] if line.split() else ""
        if previous_ended and re.fullmatch(r"[가-힣]{1,5}", first):
            counts[first] = counts.get(first, 0) + 1
        previous_ended = bool(SENTENCE_END.search(line)) or bool(re.fullmatch(r"[가-힣]{1,5}", line))
    return {name for name, n in counts.items() if n >= 2}


def dialogue_lines(lines: list[str]) -> list[dict]:
    """["쯔엉 안녕하세요? 저는 쯔엉이에요", "나타샤", "안녕하세요?"] → [{speaker, text}]. 말하는 사람이 없는 줄은 앞 말에 잇는다."""
    names = speaker_names(lines)
    out, pending = [], None
    for line in lines:
        first, _, rest = line.partition(" ")
        if line in names:
            pending = line  # 이름만 있는 줄 (다음 줄이 그 사람의 말)
        elif pending:
            out.append({"speaker": pending, "text": line})
            pending = None
        elif first in names and rest:
            out.append({"speaker": first, "text": rest.strip()})
        elif out:
            out[-1]["text"] += " " + line
    speakers = {line["speaker"] for line in out}
    return out if 2 <= len(speakers) <= MAX_SPEAKERS else []  # 말하는 사람이 너무 많으면 대화가 아니라 OCR 조각이다


def script_dialogues(book: str, unit_no: int) -> list[dict]:
    """본책 부록의 "듣고 말하기 지문" 중 그 과의 것 → [{lines, page, book}]"""
    return [d for d in all_scripts(book) if d["unit"] == unit_no]


def all_scripts(book: str) -> list[dict]:
    """
    부록의 지문 전부 [{unit, lines, page, book}]. 지문은 1과부터 차례로 실려 있다.
    과는 지문 앞의 가장 가까운 "N과 제목" 줄로 정하고, 그 사이에 제목 줄이 없으면(OCR이 못 읽음) 앞 지문의 과 + 1.
    """
    pages = sorted((p for p in rag_index.load_index()["parents"].values() if p["book"] == book), key=lambda p: p["pages"][0])
    lines = [(line.strip(), page["pages"][0]) for page in pages for line in page["text"].splitlines() if line.strip()]
    found, header, last_unit = [], None, 0
    for j, (line, page_no) in enumerate(lines):
        if match := UNIT_LINE.match(line):
            header = int(match.group(1))
            continue
        if not line.startswith(SCRIPT_HEAD):
            continue
        unit = header if header and header > last_unit else last_unit + 1
        header, last_unit = None, unit
        body = []
        for text, _ in lines[j + 1 :]:
            if SCRIPT_END.match(text) or text.startswith(SCRIPT_HEAD):
                break
            body.append(text)
        parsed = dialogue_lines(body)
        if parsed:
            found.append({"unit": unit, "lines": parsed, "page": page_no, "book": book})
    return found
