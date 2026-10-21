"""
데모용 가상 학생 3명을 backend API로 등록한다. 같은 이름의 학생이 있으면 프로필을 이 내용으로 고친다.
  - 기존 약점은 지우지 않고(이력 보존), 여기 적힌 약점 중 없는 것만 더한다.
  - 다음 수업(준비 전·확정)이 없으면 수업일을 넣은 다음 수업을 하나 만든다 (수업 준비 탭의 일정 순서용).
  - 여기에 없는 학생은 건드리지 않는다.
  - 수업·기록·레벨테스트 이력은 이어서 scripts/seed_demo_history.sql 로 넣는다 (README "실행").

  python3 scripts/seed_demo.py                 # backend가 localhost:8080 에서 실행 중이어야 함
  python3 scripts/seed_demo.py --api http://localhost:8080/api

모두 가상 인물이다 (PRD 4장: MVP는 가상 데이터만).
"""

import argparse
import datetime
import json
import urllib.request

# next_in_days: 오늘부터 며칠 뒤에 다음 수업이 있는지 (seed 전용 칸, API로 보내지 않는다). None이면 수업을 만들지 않는다
STUDENTS = [
    {
        "name": "사토 유이",
        "nativeLanguage": "ja",
        "level": "한글은 읽을 수 있음. '-이에요/예요' 자기소개와 짧은 문장 가능, 듣기가 말하기보다 빠름",
        "standardLevel": 1,
        "targetLevel": 2,
        "levelAssessedOn": "2026-10-07",
        "persona": "travel",
        "goals": ["한국 여행에서 식당·카페 주문, 길 묻기를 혼자 하기", "좋아하는 K-드라마 대사를 조금씩 알아듣기"],
        "interests": ["K-pop", "K-드라마", "카페", "여행"],
        "nextUnit": 3,
        "lessonMinutesDefault": 50,
        "notes": "일본 대학생. 한국 여행을 위해 배우는 중이고 TOPIK은 준비하지 않음.\n수줍음이 많아 처음엔 대답이 짧지만 칭찬하면 말이 많아짐. 좋아하는 아이돌·드라마 이야기를 소재로 쓰면 반응이 좋음.",
        "weaknesses": [
            {"itemId": "u02-g01", "description": "이/가 구분"},
            {"description": "받침 발음 (특히 ㄹ 받침)"},
        ],
        "next_in_days": 1,
    },
    {
        "name": "히메나",
        "nativeLanguage": "ja",
        "level": "TOPIK 6급 보유 (체험수업 전이라 자격증 기준으로 6급). 한국 거주, 일상·업무 대화에 막힘이 없음",
        "standardLevel": 6,
        "targetLevel": 6,
        "levelAssessedOn": None,
        "persona": "structured",
        "goals": ["한국 신문 기사의 시사 어휘를 정확히 이해하고 쓰기", "잘 쓰이지 않는 관용구·속담의 뜻과 쓰임 익히기", "일본어 학원 수업에서 한국어로 더 자연스럽게 설명하기"],
        "interests": ["시사 기사", "번역", "언어 교육", "한국 문학"],
        "nextUnit": 4,
        "lessonMinutesDefault": 60,
        "notes": "10-24(토) 오전 체험수업 예정 — 기사 하나로 대화하며 수준·관심 확인.\n한국에 살면서 일본어 학원에서 일본어를 가르치는 선생님. 가르치는 입장이라 문법 설명보다 '이 표현은 언제 쓰나'를 궁금해함.\n수업 전에 읽고 싶은 기사를 보내 줌. 교재 데이터가 「한국어 1」뿐이라 수업 준비 결과는 아직 수준에 맞지 않음.",
        "weaknesses": [
            {"description": "비슷한 한자어 뉘앙스 구분 (예: 개선/개량, 확보/확립)"},
            {"description": "관용구를 문어체 글에 섞어 써서 어색해짐"},
        ],
        "next_in_days": None,  # 체험수업만 잡혀 있고 정규 수업은 아직 없음
    },
    {
        "name": "Jay",
        "nativeLanguage": "en",
        "level": "한글을 아직 읽지 못함. 드라마에서 들은 인사말 몇 개만 앎",
        "standardLevel": 0,
        "targetLevel": 1,
        "levelAssessedOn": "2026-10-18",
        "persona": "conversation",
        "goals": ["K-드라마에 나오는 짧은 말을 알아듣기", "인사·자기소개 정도는 말로 하기"],
        "interests": ["K-드라마", "한국 음식", "웹툰"],
        "nextUnit": 2,
        "lessonMinutesDefault": 30,
        "notes": "10-18 체험수업: 한글은 '학교'만 읽음, 인사말 몇 개는 소리로 앎. 10-23 첫 수업.\n미국인 직장인. 가벼운 흥미로 배우고 TOPIK은 준비하지 않음. 읽기보다 회화 위주를 원해서 한글은 소리 중심으로 천천히 같이 익히기로 함.\n숙제를 부담스러워해서 5분짜리만 줌.",
        "weaknesses": [
            {"description": "한글 자모 읽기 (모음 ㅓ/ㅗ 구분)"},
            {"description": "로마자 표기에 기대서 발음함"},
        ],
        "next_in_days": 2,
    },
]


def call(method: str, url: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read() or b"null")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8080/api")
    args = parser.parse_args()

    existing = {s["name"]: s["id"] for s in call("GET", f"{args.api}/students")}
    today = datetime.date.today()
    for seed in STUDENTS:
        body = {k: v for k, v in seed.items() if k != "next_in_days"}
        if seed["name"] in existing:
            sid = existing[seed["name"]]
            current = call("GET", f"{args.api}/students/{sid}")
            # 기존 약점(id 있음)은 그대로 보내서 이력을 지키고, 설명이 겹치지 않는 seed 약점만 더한다
            kept = [{"id": w["id"], "itemId": w.get("itemId"), "description": w["description"], "resolved": w.get("resolved", False)}
                    for w in current["weaknesses"]]
            known = {w["description"] for w in kept} | {w.get("itemId") for w in kept if w.get("itemId")}
            added = [w for w in body["weaknesses"] if w["description"] not in known and (w.get("itemId") or "") not in known]
            body["weaknesses"] = kept + added
            body["status"] = current.get("status", "active")
            call("PUT", f"{args.api}/students/{sid}", body)
            print(f"수정: {seed['name']} (id {sid})")
        else:
            sid = call("POST", f"{args.api}/students", body)["id"]
            print(f"등록: {seed['name']} (id {sid})")

        lessons = call("GET", f"{args.api}/students/{sid}/lessons")
        if seed["next_in_days"] is not None and not any(l["status"] in ("planned", "prepared") for l in lessons):
            date = (today + datetime.timedelta(days=seed["next_in_days"])).isoformat()
            call("POST", f"{args.api}/students/{sid}/lessons",
                 {"unitNo": seed["nextUnit"], "minutes": seed["lessonMinutesDefault"], "targetLang": seed["nativeLanguage"], "lessonDate": date})
            print(f"  다음 수업 추가: {date}")


if __name__ == "__main__":
    main()
