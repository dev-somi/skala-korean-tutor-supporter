"""
이 파일의 역할: 단원 시트(한 교재의 한 과에서 가르칠 것)의 모양을 정한다. (기술 ADR-0032)

  data/curriculum/<book>/unit_NN.json

손으로 만든 교재 JSON(TextbookUnit)과 칸 이름을 같게 둔다. 수업 준비 그래프가 같은 코드로 읽는다.
다른 점:
  - 문법·어휘 ID는 국립국어원 표준 ID (std-g-007, std-v-00399). 진도·약점은 이 ID로 센다
  - 표준 목록에 없는 표현("이름이 뭐예요?")과 대화·읽기·연습은 교재 안 ID (ko1-u02-x01, ko1-u02-d01)
  - status: draft(자료에서 자동으로 만듦, 검수 전) | reviewed(선생님이 확인함)
  - 항목마다 source(책·쪽): 화면의 "원문" 버튼이 그 쪽을 연다 (기술 ADR-0030)
"""

from typing import Literal

from pydantic import BaseModel


class Source(BaseModel):
    book: str  # 색인의 책 ID (예: ko1_guide)
    pages: list[int]  # 책에 인쇄된 쪽


class SheetVocab(BaseModel):
    id: str  # std-v-NNNNN, 표준 목록에 없으면 <book>-uNN-xNN
    word: str
    meaning: str = ""  # 영어 뜻 (자료에 있을 때만)
    pos: str = ""  # 표준 목록의 품사
    example: str = ""
    page: int  # 대표 쪽 (source.pages[0])
    level: int | None = None  # 표준 등급. 목록에 없으면 None
    source: Source


class SheetGrammar(BaseModel):
    id: str  # 첫 번째 표준 ID
    standard_ids: list[str]  # 이 항목이 다루는 표준 문법 (예: -습니다, -습니까)
    form: str
    description: str = ""  # 자료의 설명 (지침서 구역 발췌)
    examples: list[str] = []  # 자료에 실린 예문 (기획 ADR-0017: 만들지 않는다)
    page: int
    level: int | None = None
    source: Source


class SheetDialogueLine(BaseModel):
    speaker: str
    text: str


class SheetDialogue(BaseModel):
    id: str
    lines: list[SheetDialogueLine]
    page: int
    source: Source


class SheetReading(BaseModel):
    id: str
    text: str
    page: int
    source: Source


class SheetExercise(BaseModel):
    id: str
    instruction: str
    questions: list[str]
    page: int
    source: Source


class UnitSheet(BaseModel):
    book: str  # 교재 시리즈 ID (예: ko1 = 「세종학당 한국어 1」)
    unit_no: int
    title: str
    status: Literal["draft", "reviewed"]
    page_start: int
    page_end: int
    vocabulary: list[SheetVocab]
    grammar: list[SheetGrammar]
    dialogues: list[SheetDialogue] = []
    readings: list[SheetReading] = []
    exercises: list[SheetExercise] = []
    notes: list[str] = []  # 만들면서 확인할 점 ("어휘를 지침서에서 찾지 못함" 등)
