"""
이 파일의 역할: 국립국어원 표준 교육과정 등급 목록(1~6급)을 공통 기준으로 쓰게 하는 도우미 함수 모음. (기술 ADR-0016)

- 표준 항목 찾기:      get_item("std-g-007")
- 교재 항목 -> 표준:   standard_ids("u03-g02") -> ["std-g-007"]
- 단어 등급:          word_level("가다", "동사") -> 1
- 예문 등급 판정:      sentence_level("한국 드라마를 좋아합니다.") -> 문장에서 가장 높은 어휘 등급
- 예문 거르기:        filter_examples(문장들, max_level=1) -> 학생 등급 안의 문장만 (기획 ADR-0017)

예문 등급은 어휘만 본다. 문장 안의 문법 표현(-는 것 같다 등)을 표준 목록과 맞추는 건 아직 하지 않는다.
목록에 없는 단어(고유명사, 목록 밖 단어)는 등급을 올리지 않고 unknown으로 따로 돌려준다. 판단은 선생님이 한다.
"""

import json
import re
from functools import lru_cache

from app.agent.lesson_prep.textbook import get_data_dir

# Kiwi 품사 태그 -> 표준 목록의 품사 이름. 목록의 품사는 "관형사∙명사"처럼 겹쳐 있어서 "포함"으로 맞춘다.
# 보조용언(VX: -고 싶다, -어 주다, -지 않다)은 문법 표현이라 어휘 등급에서 뺀다.
CONTENT_TAGS = {
    "NNG": "명사",
    "NNB": "의존명사",
    "NR": "수사",
    "NP": "대명사",
    "VV": "동사",
    "VA": "형용사",
    "MAG": "부사",
    "MM": "관형사",
    "IC": "감탄사",
}
PREDICATE_TAGS = {"VV", "VA"}  # 어간 + "다"가 사전형
# 어근 + 하다 (조용 + 하 -> 조용하다)
ROOT_SUFFIX = {"XSA": "형용사", "XSV": "동사"}
# 원본 품사 칸은 "부사/명사", "관형사∙명사", "수사.관형사/명사"처럼 여럿이 묶여 있고 구분자도 섞여 있다
POS_SEP = re.compile(r"[/∙·‧・.]")
# 쪼갠 뒤 나오는 품사 11가지 (화면에 보여 줄 순서)
POS_LIST = ["명사", "의존명사", "대명사", "수사", "동사", "형용사", "부사", "관형사", "감탄사", "접사", "줄어든말"]


def pos_parts(pos: str | None) -> list[str]:
    """'부사/명사' -> ['부사', '명사']. "포함"으로 맞추면 '명사'가 '의존명사'에도 걸려서 쪼개서 정확히 맞춘다."""
    return [p.strip() for p in POS_SEP.split(pos or "") if p.strip()]


# 대화 예문의 화자 표시 ("가: 이름이 뭐예요? 나: …"). 그대로 두면 "가"가 명사 5급으로 잡힌다.
SPEAKER_LABEL = re.compile(r"(?:^|(?<=\s))[가-힣A-Za-z]{1,4}\s*:\s*")


def _load(name: str) -> list[dict]:
    path = get_data_dir() / "standard" / name
    return json.loads(path.read_text(encoding="utf-8"))["items"]


@lru_cache
def grammar_items() -> list[dict]:
    return _load("grammar.json")


@lru_cache
def vocab_items() -> list[dict]:
    return _load("vocab.json")


@lru_cache
def _items_by_id() -> dict:
    return {item["id"]: item for item in grammar_items() + vocab_items()}


@lru_cache
def _vocab_by_word() -> dict:
    by_word: dict[str, list[dict]] = {}
    for item in vocab_items():
        by_word.setdefault(item["word"], []).append(item)
    return by_word


@lru_cache
def _textbook_map() -> dict:
    """{교재 항목 ID: [표준 ID, ...]} — 모든 교재를 합친다. "_"로 시작하는 키는 설명이라 뺀다."""
    path = get_data_dir() / "standard" / "textbook_map.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = {}
    for book, mapping in data.items():
        if book.startswith("_"):
            continue
        merged.update({k: v for k, v in mapping.items() if not k.startswith("_")})
    return merged


def get_item(standard_id: str) -> dict | None:
    return _items_by_id().get(standard_id)


def standard_ids(textbook_item_id: str) -> list[str]:
    """교재 항목에 대응하는 표준 항목 ID 목록. 대응이 없으면 빈 목록."""
    return _textbook_map().get(textbook_item_id, [])


def item_level(textbook_item_id: str) -> int | None:
    """교재 항목의 등급 = 대응하는 표준 항목 중 가장 높은 등급 (다 알아야 그 항목을 안다)."""
    levels = [get_item(sid)["level"] for sid in standard_ids(textbook_item_id) if get_item(sid)]
    return max(levels) if levels else None


def word_level(word: str, pos: str | None = None) -> int | None:
    """
    사전형 단어의 등급. 같은 글자가 여러 등급에 있으면 품사가 맞는 것 중 가장 낮은 등급.
    품사가 맞는 게 없으면 None — 다른 품사의 등급을 빌려 오면 틀린다 (관형사 "이"가 명사 "이(치아)" 2급이 됨).
    """
    candidates = _vocab_by_word().get(word, [])
    if pos:
        # Kiwi가 명사라고 한 것은 목록의 의존명사와도 맞춘다. 둘을 가르는 기준이 달라서다
        # ("받을 때"의 때를 Kiwi는 명사, 목록은 의존명사 1급으로 둔다. 명사만 보면 "때가 타다"의 4급이 걸린다).
        # 거꾸로 Kiwi가 의존명사라고 한 것은 의존명사만 본다. "본 적이 있다"의 적이 "적(敵)" 4급에 걸리지 않게.
        # 문법 표현 속 의존명사(적, 수, 뻔)는 목록에 없으면 unknown이 된다.
        wanted = {"명사", "의존명사"} if pos == "명사" else {pos}
        candidates = [c for c in candidates if wanted & set(pos_parts(c["pos"]))]
    return min((c["level"] for c in candidates), default=None)


@lru_cache
def _kiwi():
    from kiwipiepy import Kiwi

    return Kiwi()


def content_words(sentence: str) -> list[tuple[str, str]]:
    """문장의 내용어를 (사전형, 품사) 목록으로. 조사·어미·문장부호·고유명사는 뺀다."""
    words = []
    tokens = _kiwi().tokenize(SPEAKER_LABEL.sub(" ", sentence))
    for i, token in enumerate(tokens):
        next_tag = tokens[i + 1].tag if i + 1 < len(tokens) else None
        if token.tag == "XR" and next_tag in ROOT_SUFFIX:
            words.append((token.form + "하다", ROOT_SUFFIX[next_tag]))
        elif token.tag == "NNG" and next_tag == "XSN" and word_level(token.form + tokens[i + 1].form, "명사"):
            # 선생 + 님 -> 선생님 (목록에 붙은 꼴로 있을 때만)
            words.append((token.form + tokens[i + 1].form, "명사"))
        elif token.tag in CONTENT_TAGS:
            lemma = token.form + "다" if token.tag in PREDICATE_TAGS else token.form
            words.append((lemma, CONTENT_TAGS[token.tag]))
    return words


def sentence_level(sentence: str) -> dict:
    """
    예문 하나의 어휘 등급.
    level = 목록에 있는 단어 중 가장 높은 등급 (단어가 하나도 안 걸리면 None)
    words = [{word, level}], unknown = 목록에 없는 단어
    """
    words, unknown = [], []
    for lemma, pos in content_words(sentence):
        level = word_level(lemma, pos)
        if level is None:
            unknown.append(lemma)
        else:
            words.append({"word": lemma, "level": level})
    level = max((w["level"] for w in words), default=None)
    return {"sentence": sentence, "level": level, "words": words, "unknown": unknown}


def filter_examples(sentences: list[str], max_level: int) -> dict:
    """
    학생 등급(max_level) 안의 예문만 고른다.
    fit     = 모든 단어가 max_level 이하인 예문 (쉬운 예문부터)
    too_hard = 등급을 넘는 단어가 있는 예문과 그 단어들 (선생님이 볼 수 있게 버리지 않는다)
    """
    fit, too_hard = [], []
    for sentence in sentences:
        result = sentence_level(sentence)
        hard_words = [w for w in result["words"] if w["level"] > max_level]
        if hard_words:
            too_hard.append({**result, "hard_words": hard_words})
        else:
            fit.append(result)
    fit.sort(key=lambda r: r["level"] or 0)
    return {"fit": fit, "too_hard": too_hard}
