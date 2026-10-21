"""
이 파일의 역할: 출처에서 원본 PDF를 여는 부분을 테스트한다 (기술 ADR-0030).

  - 인쇄 쪽 → PDF 쪽: 쪽 번호가 없는 쪽(과 표지), OCR이 쪽 번호를 잘못 읽은 쪽
  - 언어판을 합친 핸드북은 등록된 판(영어판 먼저)으로 연다
  - 등록되지 않은 책은 열지 않고 이유를 돌려준다
  - scan: 쪽 수·권 번호·판 언어로 짝짓는다
"""

from pathlib import Path

import pytest

from app.rag import pdfs


def footer(no: int | None) -> list[dict]:
    lines = [{"text": "본문", "x": 0.1, "y": 0.5, "w": 0.3, "h": 0.02}]
    if no is not None:
        lines.append({"text": f"교원용 지침서 {no}", "x": 0.6, "y": 0.96, "w": 0.3, "h": 0.01})
    return lines


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(pdfs, "REGISTRY", tmp_path / "pdfs.json")
    pdfs.page_table.cache_clear()
    yield tmp_path
    pdfs.page_table.cache_clear()


def test_page_table_skips_unnumbered_and_misread_pages(registry, monkeypatch):
    # PDF 1~6쪽: 인쇄 쪽 = PDF - 3. 4쪽은 쪽 번호가 없고(과 표지), 2쪽은 OCR이 "5"로 잘못 읽었다
    printed = {1: None, 2: 5, 3: None, 4: None, 5: 2, 6: 3}
    pages = [{"page": pdf, "lines": footer(no)} for pdf, no in printed.items()]
    monkeypatch.setattr(pdfs, "load_pages", lambda book: pages)
    monkeypatch.setitem(pdfs.BOOKS, "test_guide", {"title": "테스트", "layout": "sections", "lang": "ko", "kind": "guide"})
    pdfs.register("test_guide", registry / "x.pdf")
    assert pdfs.pdf_page("test_guide", 2) == 5
    assert pdfs.pdf_page("test_guide", 3) == 6  # 쪽 번호가 없는 PDF 3쪽이 대신 차지하지 않는다
    assert pdfs.pdf_page("test_guide", 99) == 99  # 모르는 쪽은 그대로


def test_merged_handbook_opens_registered_edition(registry):
    assert pdfs.resolve("practical1_handbook") is None
    pdfs.register("practical1_handbook_ja", registry / "ja.pdf")
    assert pdfs.resolve("practical1_handbook") == "practical1_handbook_ja"
    pdfs.register("practical1_handbook_en", registry / "en.pdf")
    assert pdfs.resolve("practical1_handbook") == "practical1_handbook_en"


def test_open_unregistered_book_returns_reason(registry):
    result = pdfs.open_pdf("ko1_guide", 33)
    assert result["opened"] is False and "등록" in result["message"]


def test_match_score_needs_volume_and_edition_language():
    ko1 = pdfs.match_score("ko1_guide", Path("세종학당 한국어 1 교원용 지침서.pdf"), 292, 292)
    ko2_file = pdfs.match_score("ko1_guide", Path("세종학당 한국어 2 교원용 지침서.pdf"), 292, 292)
    short = pdfs.match_score("ko1_guide", Path("세종학당 한국어 1 교원용 지침서.pdf"), 100, 292)
    assert ko1 > 1 and ko2_file == 0 and short == 0
    assert pdfs.match_score("practical1_handbook_en", Path("핸드북 어휘와 문법 1_일본어.pdf"), 71, 71) == 0
    assert pdfs.match_score("practical1_handbook_en", Path("[핸드북] 실용 한국어_어휘와 문법_1권(영어).pdf"), 71, 71) > 1


def test_materials_api_lists_and_opens(client, registry):
    assert client.get("/materials").json() == {"books": []}
    body = client.post("/materials/open", json={"book": "ko1_guide", "page": 33}).json()
    assert body["opened"] is False
