"""
이 파일의 역할: OCR 결과(쪽마다 줄 목록)를 Parent-Child 청크로 나눈다. (ADR-0014)

  parent = 한 과 안의 구역 하나 (예: 3과 "문법 1") — 브리핑에 통째로 넣는 단위
  child  = parent를 단락 크기로 나눈 조각 — 의미 검색에 쓰는 단위

책마다 쪽 구조가 달라서 나누는 방식(layout)이 여러 가지다.
  - "sections":    교원용 지침서처럼 구역 제목(도입, 문법 1, 마무리 …)이 반복되는 책
  - "pages":       핸드북처럼 한 쪽이 한 항목(문법 하나)인 책 → 한 쪽 = parent 하나
  - "text_pages":  글자 층 PDF, 펼친 두 쪽 = parent 하나 (문화 교재)
  - "ocr_page" / "text_page": 형식을 따로 맞추지 않은 책, 한 쪽 = parent 하나 (기본 규칙)

문법 태그 (기술 ADR-0025). 값은 형태 키(app.rag.forms)이고 화면에는 보이지 않는다.
  - teaches:  이 구역이 가르치는 문법. 책 형식별 규칙(teaches)으로 제목·도입 문장에서 뽑는다
  - mentions: 본문에 따옴표로 언급된 문법. 비교 설명("-어서와 구분")을 찾는 데 쓴다
"""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.rag.forms import form_keys, is_grammar_key, quoted_forms
from app.rag.ocr import ocr_dir

# 색인할 책 목록 (기획 ADR-0025의 1순위). 새 PDF를 넣으면 여기에 한 줄 추가한다.
#   kind:    guide(교사용 설명) | handbook | culture — 문법 질문이 근거를 고를 때 쓴다
#   teaches: 문법 태그 규칙 (아래 TEACHES_RULES)
BOOKS = {
    "ko0_guide": {"title": "세종학당 한국어 입문 교원용 지침서", "layout": "text_page", "lang": "ko", "kind": "guide"},
    "ko1_guide": {"title": "바로 배워 바로 쓰는 세종학당 한국어 1 교원용 지침서", "layout": "sections", "lang": "ko", "kind": "guide", "teaches": "first_quote"},
    "ko2_guide": {"title": "세종학당 한국어 2 교원용 지침서", "layout": "sections", "lang": "ko", "kind": "guide", "teaches": "first_quote"},
    "ko3a_manual": {"title": "세종학당 한국어 3A 교원용 매뉴얼", "layout": "ocr_page", "lang": "ko", "kind": "guide", "teaches": "numbered"},
    "ko3b_manual": {"title": "세종학당 한국어 3B 교원용 매뉴얼", "layout": "ocr_page", "lang": "ko", "kind": "guide", "teaches": "numbered"},
    "ko4a_manual": {"title": "세종학당 한국어 4A 교원용 매뉴얼", "layout": "ocr_page", "lang": "ko", "kind": "guide", "teaches": "numbered"},
    "ko4b_manual": {"title": "세종학당 한국어 4B 교원용 매뉴얼", "layout": "ocr_page", "lang": "ko", "kind": "guide", "teaches": "numbered"},
    "ko5a_guide": {"title": "세종학당 한국어 5A 교원용 지침서", "layout": "text_page", "lang": "ko", "kind": "guide", "teaches": "introduce"},
    "ko5b_guide": {"title": "세종학당 한국어 5B 교원용 지침서", "layout": "text_page", "lang": "ko", "kind": "guide", "teaches": "introduce"},
    "ko6a_guide": {"title": "세종학당 한국어 6A 교원용 지침서", "layout": "text_page", "lang": "ko", "kind": "guide", "teaches": "introduce"},
    "ko6b_guide": {"title": "세종학당 한국어 6B 교원용 지침서", "layout": "text_page", "lang": "ko", "kind": "guide", "teaches": "introduce"},
    # 「실용 한국어」 지침서: 쪽마다 수업 개요 표와 설명이 섞여 teaches 규칙을 아직 정하지 않았다 → 기본 규칙, mentions만 (기술 ADR-0025 결정 8)
    "practical1_guide": {"title": "세종학당 실용 한국어 1 교원용 지침서", "layout": "ocr_page", "lang": "ko", "kind": "guide"},
    "practical2_guide": {"title": "세종학당 실용 한국어 2 교원용 지침서", "layout": "ocr_page", "lang": "ko", "kind": "guide"},
    "practical3_guide": {"title": "세종학당 실용 한국어 3 교원용 지침서", "layout": "ocr_page", "lang": "ko", "kind": "guide"},
    "practical4_guide": {"title": "세종학당 실용 한국어 4 교원용 지침서", "layout": "ocr_page", "lang": "ko", "kind": "guide"},
    "culture1_guide": {"title": "세종한국문화 1 교원용 지침서", "layout": "ocr_page", "lang": "ko", "kind": "culture"},
    "culture2_guide": {"title": "세종한국문화 2 교원용 지침서", "layout": "ocr_page", "lang": "ko", "kind": "culture"},
    # 핸드북: series가 같은 책은 판(영어·일본어)만 다르고 항목 번호가 같다 → 색인에서 한 덩어리로 합친다 (app.rag.handbook)
    "practical1_handbook_en": {"title": "세종학당 실용 한국어 1 어휘와 문법 (영어판)", "layout": "pages", "lang": "en", "series": "practical1", "kind": "handbook"},
    "practical1_handbook_ja": {"title": "세종학당 한국어 회화 어휘와 문법 1 (일본어판)", "layout": "pages", "lang": "ja", "series": "practical1", "kind": "handbook"},
    "practical2_handbook_en": {"title": "세종학당 실용 한국어 2 어휘와 문법 (영어판)", "layout": "pages", "lang": "en", "series": "practical2", "kind": "handbook"},
    "practical2_handbook_ja": {"title": "세종학당 한국어 회화 어휘와 문법 2 (일본어판)", "layout": "pages", "lang": "ja", "series": "practical2", "kind": "handbook"},
    "practical3_handbook_en": {"title": "세종학당 실용 한국어 3 어휘와 문법 (영어판)", "layout": "pages", "lang": "en", "series": "practical3", "kind": "handbook"},
    "practical4_handbook_en": {"title": "세종학당 실용 한국어 4 어휘와 문법 (영어판)", "layout": "pages", "lang": "en", "series": "practical4", "kind": "handbook"},
    # 글자 층이 있는 PDF (app.rag.textlayer). 본문 13~138쪽(1~8과 + 문화 더하기)만 쓴다
    "culture1": {"title": "세종한국문화 1", "layout": "text_pages", "lang": "ko,en", "pages": (13, 138), "kind": "culture"},
}
# 언어판을 합친 핸드북 (merge_editions가 만든다. 직접 청크하지 않는다)
SERIES_TITLES = {
    "practical1": "세종학당 실용 한국어 1 어휘와 문법",
    "practical2": "세종학당 실용 한국어 2 어휘와 문법",
    "practical3": "세종학당 실용 한국어 3 어휘와 문법",
    "practical4": "세종학당 실용 한국어 4 어휘와 문법",
}
for _series, _title in SERIES_TITLES.items():
    BOOKS[f"{_series}_handbook"] = {"title": _title, "layout": "merged", "lang": "ko", "kind": "handbook", "series": _series}

# 지침서의 구역 제목. OCR 줄이 이 모양과 정확히 같으면 새 구역이 시작된다.
SECTION_PATTERN = re.compile(
    r"^(?:\d\s*)?(학습\s?목표|학습 내용|수업 개요|수업 절차|도입|어휘 및 표현(?:_.+)?|문법 ?[12]|"
    r"어휘 및 문법 연습|듣고 말하기|읽고 쓰기|마무리|과제|보충 연습)$"
)
UNIT_COVER = re.compile(r"^(\d{1,2})과$")  # 과 표지의 큰 "2과"
UNIT_HEADER = re.compile(r"^(\d{1,2})과\s*[•·]")  # 쪽 머리말 "1과 • 저는 한국 사람이에요"
HANDBOOK_UNIT = re.compile(r"^0?(\d{1,2})\s+\S")  # 핸드북 쪽 제목 "01 저는 대학생이에요"
HANDBOOK_ITEM = re.compile(r"^(\d{1,2})-(\d)\s*(.*)$")  # 핸드북 항목 "1-2 은/는"

# 학습 목표 ~ 수업 개요 쪽은 표 칸 이름에 "도입", "문법 1" 같은 구역 이름이 들어 있다.
# 이 구역 안에서는 "수업 절차"가 나올 때까지 새 구역을 만들지 않고 한 parent로 모은다.
OVERVIEW_SECTIONS = {"학습 목표", "학습목표", "학습 내용", "수업 개요"}

HEADER_Y, FOOTER_Y = 0.09, 0.93  # 이 위·아래는 머리말·꼬리말
MIN_TEXT_HEIGHT = 0.0095  # 이보다 작은 글자는 지침서에 축소해 실은 교재 쪽 그림이라 버린다
CHILD_CHARS = 400  # child 하나의 목표 길이(글자)
PARENT_MAX_CHARS = 3000  # 프롬프트가 너무 길어지지 않게 parent를 자르는 길이


@dataclass
class Parent:
    id: str
    book: str
    unit: int
    section: str  # 구역 이름 (예: "문법 1", "어휘 및 표현_나라", "1-2 은/는")
    pages: list[int] = field(default_factory=list)  # 책에 인쇄된 쪽 번호 (없으면 PDF 쪽)
    text: str = ""
    teaches: list[str] = field(default_factory=list)  # 이 구역이 가르치는 문법의 형태 키
    mentions: list[str] = field(default_factory=list)  # 본문에 언급된 문법의 형태 키 (teaches 제외)
    translations: dict[str, str] = field(default_factory=dict)  # 언어판을 합친 핸드북의 모국어 설명 {en, ja}


@dataclass
class Child:
    id: str
    parent_id: str
    text: str


def reading_order(lines: list[dict]) -> list[dict]:
    """2단 편집을 고려해 왼쪽 단 → 오른쪽 단, 위 → 아래 순서로 줄을 정렬한다."""
    body = [line for line in lines if HEADER_Y <= line["y"] <= FOOTER_Y and line["h"] >= MIN_TEXT_HEIGHT]
    return sorted(body, key=lambda line: (line["x"] >= 0.5, line["y"]))


def printed_page(lines: list[dict]) -> int | None:
    """꼬리말에서 책에 인쇄된 쪽 번호를 찾는다. 없으면(표지·속표지) None."""
    for line in lines:
        if line["y"] > FOOTER_Y:
            match = re.search(r"(\d{1,3})\s*$", line["text"]) or re.match(r"^\s*(\d{1,3})\b", line["text"])
            if match:
                return int(match.group(1))
    return None


def load_pages(book: str) -> list[dict]:
    pages = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ocr_dir(book).glob("p-*.json"))]
    return sorted(pages, key=lambda p: p["page"])


def split_children(parent: Parent) -> list[Child]:
    """줄 경계를 지키며 CHILD_CHARS 근처에서 자른다. 앞에 과·구역 이름을 붙여 검색이 잘 되게 한다."""
    children, buf = [], []
    prefix = f"[{parent.unit}과 {parent.section}] "
    for line in parent.text.split("\n"):
        buf.append(line)
        if sum(len(x) for x in buf) >= CHILD_CHARS:
            children.append(prefix + " ".join(buf))
            buf = []
    if buf:
        children.append(prefix + " ".join(buf))
    return [Child(id=f"{parent.id}#{i}", parent_id=parent.id, text=t) for i, t in enumerate(children)]


def chunk_sections(book: str) -> list[Parent]:
    """지침서: 과 표지와 구역 제목을 따라 parent를 만든다."""
    parents: list[Parent] = []
    unit, current = 0, None
    in_overview = False  # 학습 목표 ~ 수업 개요 표 안인가
    past_overview = False  # 이 과의 "수업 절차"를 지났는가 (그 뒤의 "학습목표"는 축소 교재 그림 속 글자)

    def start(section: str) -> Parent:
        parent = Parent(id=f"{book}/{unit}/{len(parents)}", book=book, unit=unit, section=section)
        parents.append(parent)
        return parent

    for page in load_pages(book):
        lines = page["lines"]
        page_no = printed_page(lines)
        for line in lines:  # 과 번호는 표지의 큰 글자나 머리말에서 얻는다
            match = UNIT_COVER.match(line["text"].strip()) or (
                line["y"] < HEADER_Y and UNIT_HEADER.match(line["text"].strip())
            )
            if match:
                unit = int(match.group(1))
                break
        if unit == 0 or page_no is None:
            continue  # 책 표지·판권, 과 표지·속표지 (학습 목표가 본문 쪽에 다시 나온다)

        for line in reading_order(lines):
            text = line["text"].strip()
            heading = re.sub(r"^\d\s*", "", text) if SECTION_PATTERN.match(text) else None

            if heading in OVERVIEW_SECTIONS and past_overview and current is not None and current.unit == unit:
                heading = None

            if current is None or current.unit != unit:  # 과가 바뀌었다
                in_overview = past_overview = False
                current = start("학습 목표·수업 개요" if heading in OVERVIEW_SECTIONS else "개요")
                if heading in OVERVIEW_SECTIONS:
                    in_overview = True
            elif heading == "수업 절차":
                in_overview, past_overview = False, True  # 다음 줄의 "도입"부터 실제 구역이다
            elif heading in OVERVIEW_SECTIONS:
                if not in_overview:
                    current = start("학습 목표·수업 개요")
                    in_overview = True
            elif heading and not in_overview:  # 개요 표 안의 칸 이름("도입", "문법 1")은 무시한다
                current = start(heading)

            if heading != "수업 절차":
                current.text += text + "\n"
            if page_no not in current.pages:
                current.pages.append(page_no)
    return [p for p in parents if len(p.text.strip()) >= 30]  # 제목만 있는 조각은 버린다


def chunk_pages(book: str) -> list[Parent]:
    """
    핸드북: 한 쪽을 parent 하나로 만든다. 쪽 제목에서 과, 항목 번호("1-2 은/는")에서 구역을 얻는다.
    어휘 쪽과 문법 쪽이 같은 번호를 쓰므로, 구분 쪽("어휘" / "문법" 큰 제목 + 과 목록)을 만나면 모드를 바꾼다.
    """
    parents: list[Parent] = []
    unit, mode = 0, "어휘"
    for page in load_pages(book):
        texts = [line["text"].strip() for line in page["lines"]]
        if any(t in ("어휘", "문법") for t in texts) and sum(bool(re.match(r"^\d{1,2}과(\s|$)", t)) for t in texts) >= 5:
            mode = "문법" if "문법" in texts else "어휘"
            continue  # 구분 쪽 (목차)

        ordered = sorted(page["lines"], key=lambda line: (line["y"], line["x"]))
        label = ""
        for line in ordered[:4]:  # 제목은 쪽 맨 위에 있다
            text = line["text"].strip()
            if match := HANDBOOK_ITEM.match(text):
                unit, label = int(match.group(1)), text
                if not match.group(3):  # 번호("3-1")와 형태("이/가")가 따로 읽힌 쪽: 같은 높이의 오른쪽 줄이 형태
                    beside = [o for o in ordered[:4] if o is not line and abs(o["y"] - line["y"]) < 0.02 and o["x"] > line["x"]]
                    if beside:
                        label = f"{text} {beside[0]['text'].strip()}"
                break
            if (match := HANDBOOK_UNIT.match(text)) and line["y"] < 0.12:
                unit = int(match.group(1))
        if unit == 0:
            continue
        if mode == "문법" and not HANDBOOK_ITEM.match(label):
            # 번호 배지를 못 읽은 쪽: 과 안에서 몇 번째 문법 쪽인지로 번호를 붙이고, 제목 줄(배지 옆)을 형태로 쓴다
            no = sum(p.unit == unit and p.section.startswith("문법") for p in parents) + 1
            title = next((o["text"].strip() for o in ordered if 0.1 < o["y"] < 0.13 and o["x"] > 0.15), "")
            label = f"{unit}-{no} {title}".strip()
        body = "\n".join(line["text"] for line in ordered if line["y"] <= FOOTER_Y)
        item = HANDBOOK_ITEM.match(label)
        parents.append(
            Parent(
                id=f"{book}/{unit}/p{page['page']}",
                book=book,
                unit=unit,
                section=f"{mode} {label}".strip(),
                pages=[printed_page(page["lines"]) or page["page"]],
                text=body,
                teaches=sorted(form_keys(item.group(3))) if item and mode == "문법" else [],
            )
        )
    return parents


CULTURE_FOOTER = re.compile(r"(\d)과\s+\S")  # 꼬리말 "1과 한국인의 일상을 들여다봐요  15"


def chunk_text_pages(book: str) -> list[Parent]:
    """
    글자 층 PDF(문화 교재): 펼친 두 쪽을 parent 하나로 만든다. 주제 제목이 단원 끝 정리 쪽에만 모여 있어서
    구역으로 나누지 않고, 의미 검색으로 찾는다. 과 번호는 홀수 쪽 꼬리말에서 얻는다.
    """
    from app.rag.textlayer import text_dir  # 순환 import 방지

    first, last = BOOKS[book]["pages"]
    parents: list[Parent] = []
    unit, spread = 0, []
    for page in range(first, last + 1):
        path = text_dir(book) / f"p-{page:03d}.txt"
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines[-3:]:
            if match := CULTURE_FOOTER.search(line):
                unit = int(match.group(1))
        printed = page - 1  # 이 책은 PDF 쪽 - 1 = 인쇄 쪽 (표지가 1쪽)
        body = [line for line in lines if not re.fullmatch(r"\d{1,3}", line.strip())]
        spread.append((printed, "\n".join(body)))
        if len(spread) == 2 or page == last:
            pages = [p for p, _ in spread]
            section = "문화 더하기" if pages[0] >= 126 else "문화"
            parents.append(
                Parent(
                    id=f"{book}/{unit}/p{pages[0]}",
                    book=book,
                    unit=unit if pages[0] < 126 else 0,
                    section=section,
                    pages=pages,
                    text="\n".join(text for _, text in spread),
                )
            )
            spread = []
    return [p for p in parents if len(p.text.strip()) >= 30]


def chunk_single_pages(book: str) -> list[Parent]:
    """
    기본 규칙: 한 쪽 = parent 하나. 형식을 따로 맞추지 않은 책에 쓴다 (기술 ADR-0025 결정 8).
    OCR 책은 2단 읽기 순서로, 글자 층 책은 뽑은 글 그대로. 과 번호는 "N과"가 처음 보이는 줄에서 얻는다.
    """
    from app.rag.textlayer import text_dir  # 순환 import 방지

    parents: list[Parent] = []
    unit = 0
    if BOOKS[book]["layout"] == "ocr_page":
        pages = [(p["page"], printed_page(p["lines"]) or p["page"], [line["text"] for line in reading_order(p["lines"])]) for p in load_pages(book)]
    else:
        files = sorted(text_dir(book).glob("p-*.txt"))
        pages = [(int(f.stem[2:]), int(f.stem[2:]), f.read_text(encoding="utf-8").splitlines()) for f in files]
    for pdf_page, printed, lines in pages:
        for line in lines[:6]:
            if match := re.search(r"(\d{1,2})과", line):
                unit = int(match.group(1))
                break
        body = "\n".join(line for line in lines if line.strip())
        if len(body) < 30:
            continue
        parents.append(Parent(id=f"{book}/p{pdf_page}", book=book, unit=unit, section=f"{printed}쪽", pages=[printed], text=body))
    return parents


# 책 형식별 teaches 규칙: parent 글 → 가르치는 문법 형태 (기술 ADR-0025 결정 3)
NUMBERED_TITLE = re.compile(r"^\d\.\s*(-[^\n]{1,30})$", re.M)  # 3~4급 매뉴얼 "1. -나 보다, -는가 보다"
INTRODUCE = re.compile(r"[‘'\"“]([^’'\"”\n]{1,20})[’'\"”]\s*(?:을|를)\s*도입한다")  # 5~6급 "‘...은 -기 나름이다’를 도입한다"
FIRST_QUOTE = re.compile(r"[‘'\"“]\s*(-?[가-힣][^’'\"”\n]{0,15})[’'\"”]")
TARGET_GRAMMAR = re.compile(r"목표\s*문법\s*['‘]?\s*(-?[가-힣][^’'\n]{0,12}?)['’]\s*(?:가|이|는|은)")  # 여는 따옴표를 OCR이 놓친 경우


def teaches_of(parent: Parent, rule: str | None) -> set[str]:
    if rule == "first_quote":  # 1·2급 지침서: "문법 N" 구역 앞부분의 첫 따옴표 ("목표 문법 '-어서'가 …")
        if parent.section.startswith("문법"):
            for match in [*TARGET_GRAMMAR.finditer(parent.text[:250]), *FIRST_QUOTE.finditer(parent.text[:250])]:
                keys = {key for key in form_keys(match.group(1)) if is_grammar_key(key)}
                if keys:
                    return keys
        return set()
    if rule == "numbered":
        return {key for match in NUMBERED_TITLE.finditer(parent.text) for key in form_keys(match.group(1))}
    if rule == "introduce":
        return {key for match in INTRODUCE.finditer(parent.text) for key in form_keys(match.group(1))}
    return set()


def tag(parent: Parent) -> None:
    """teaches(책 규칙)와 mentions(본문 따옴표)를 붙인다. 핸드북은 chunk_pages가 이미 teaches를 붙였다."""
    teaches = set(parent.teaches) | teaches_of(parent, BOOKS[parent.book].get("teaches"))
    parent.teaches = sorted(teaches)
    parent.mentions = sorted(quoted_forms(parent.text) - teaches)


def build_chunks(book: str) -> tuple[list[Parent], list[Child]]:
    layout = BOOKS[book]["layout"]
    if layout == "sections":
        parents = chunk_sections(book)
    elif layout == "text_pages":
        parents = chunk_text_pages(book)
    elif layout in ("ocr_page", "text_page"):
        parents = chunk_single_pages(book)
    else:
        parents = chunk_pages(book)
    for parent in parents:
        parent.text = parent.text.strip()[:PARENT_MAX_CHARS]
        tag(parent)
    children = [child for parent in parents for child in split_children(parent)]
    return parents, children


def build_all(books: list[str]) -> tuple[list[Parent], list[Child]]:
    """여러 책을 청크하고, 같은 시리즈 핸드북의 언어판을 합친 뒤 child를 다시 만든다 (임베딩은 한 번만)."""
    from app.rag.handbook import merge_editions  # 순환 import 방지

    parents = [parent for book in books for parent in build_chunks(book)[0]]
    parents = merge_editions(parents, BOOKS)
    for parent in parents:
        tag(parent)
    children = [child for parent in parents for child in split_children(parent)]
    return parents, children


def to_dicts(items) -> list[dict]:
    return [asdict(item) for item in items]


if __name__ == "__main__":
    import sys

    parents, children = build_chunks(sys.argv[1])
    print(f"parent {len(parents)}개, child {len(children)}개")
    for parent in parents[:40]:
        print(parent.unit, parent.section, parent.pages, len(parent.text))
