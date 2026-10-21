"""
이 파일의 역할: 「어휘와 문법」 핸드북 항목 글을 나누고, 같은 시리즈의 영어판·일본어판을 한 덩어리로 합친다. (기술 ADR-0025)

  핸드북 한 쪽 = 문법 항목 하나: 제목 → 예문 → 한국어 설명 → 영어(또는 일본어) 설명
  영어판과 일본어판은 한국어 부분이 같고 모국어 설명만 다르다.
  → 한국어 부분은 한 번만 두고(검색·임베딩도 한 번), 모국어 설명은 translations[lang]에 붙인다.
"""

import re

from app.rag.ocr import KANA

GARBLED_QUOTE = re.compile(r"「([^」]*[A-Za-z0-9][^」]*)」")  # 일본어 설명 안의 한국어는 OCR에서 로마자·숫자로 깨진다
EXAMPLE_LINE = re.compile(r"^[•・·]|^[가나]\s?:")


def headword(section: str) -> str:
    """"문법 14-1 -아서/-어서/-여서(1)" → "-아서/-어서/-여서" """
    return re.sub(r"^문법\s*\d{1,2}-\d+\)?\s*|\(\d\)$", "", section).strip()


def clean_native(text: str, head: str) -> str:
    """일본어 설명의 깨진 「」: 첫 번째는 항목 이름(설명이 항상 표제어로 시작한다), 나머지는 「…」로 바꾼다."""
    first = [True]

    def fix(match: re.Match) -> str:
        if first[0] and head:
            first[0] = False
            return f"「{head}」"
        return "「…」"

    return GARBLED_QUOTE.sub(fix, text)


def is_native_line(line: str) -> bool:
    """모국어 설명 줄인가: 가나가 있거나, 알파벳이 한글보다 많다 (영어 설명에도 '-으니까' 같은 한국어 형태가 섞인다)."""
    return bool(KANA.search(line) or len(re.findall(r"[A-Za-z]", line)) > len(re.findall(r"[가-힣]", line)))


def split_item(text: str, section: str) -> dict:
    """핸드북 항목 글 → {korean(제목·예문·한국어 설명), examples, explain_ko, native}"""
    lines = [line.strip() for line in text.splitlines() if line.strip() and not re.fullmatch(r"\d{1,3}", line.strip())]
    native = [line for line in lines[2:] if is_native_line(line)]
    korean = [line for line in lines if line not in native]
    examples = [line for line in korean if EXAMPLE_LINE.match(line)]
    explain_ko = re.sub(r"^\d{1,2}-\d\s*", "", " ".join(line for line in korean[2:] if line not in examples))
    native_text = " ".join(native)
    if KANA.search(native_text):
        native_text = clean_native(native_text, headword(section))
    return {"korean": "\n".join(korean), "examples": examples[:6], "explain_ko": explain_ko, "native": native_text}


def item_no(section: str) -> str | None:
    match = re.match(r"^문법\s*(\d{1,2}-\d)", section)
    return match.group(1) if match else None


def merge_editions(parents: list, books: dict) -> list:
    """
    같은 시리즈·같은 문법 항목의 영어판·일본어판 parent를 하나로 합친다.
    합친 parent: book = "<series>_handbook", text = 한국어 부분, translations = {en: …, ja: …}
    어휘 쪽과 시리즈가 없는 책은 그대로 둔다.
    """
    merged, groups = [], {}
    for parent in parents:
        series = books[parent.book].get("series")
        no = item_no(parent.section)
        if not series or not no:
            merged.append(parent)
            continue
        groups.setdefault((series, no), []).append(parent)

    for (series, no), group in groups.items():
        base = group[0]
        parts = {books[p.book]["lang"]: split_item(p.text, p.section) for p in group}
        korean = max(parts.values(), key=lambda part: len(part["explain_ko"]))["korean"]  # OCR이 더 잘 된 판
        base.id = f"{series}_handbook/{no}"
        base.book = f"{series}_handbook"
        base.text = korean
        base.translations = {lang: part["native"] for lang, part in parts.items() if part["native"]}
        base.pages = sorted({page for p in group for page in p.pages})
        merged.append(base)
    return merged
