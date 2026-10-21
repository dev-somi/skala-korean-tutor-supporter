"""
이 파일의 역할: DB의 옛 교재 항목 ID를 새 ID로 바꾸는 Flyway SQL을 만든다. (기술 ADR-0032)

  uv run python -m app.curriculum.migrate_ids > ../backend/src/main/resources/db/migration/V6__standard_item_ids.sql

바꾸는 곳: weakness.item_id, lesson.covered_item_ids(배열), lesson.understanding(키).
더하는 칸: student.next_book, lesson.book (기본 ko1 — 지금까지의 수업은 모두 「세종학당 한국어 1」).
예전 수업의 plan·drafts·수업 기록 원문(JSON)은 그때의 기록이라 그대로 둔다.
대응표에 교재 원문은 없고 ID만 있어서 저장소에 넣어도 된다.
"""

from app.curriculum.ids import old_to_new


def sql() -> str:
    rows = ",\n    ".join(f"('{old}', '{new}')" for old, new in sorted(old_to_new().items()))
    return f"""-- 옛 교재 항목 ID(u02-g01) → 표준 ID(std-g-001) / 교재 안 ID(ko1-u02-d01) (기획 ADR-0030, 기술 ADR-0032)
-- app.curriculum.migrate_ids가 만든 파일이다. 직접 고치지 말고 다시 만든다.

-- 교재 시리즈 (단원 시트 data/curriculum/<book>/). next_unit·unit_no는 이 교재의 과다
alter table student add column next_book varchar(20) not null default 'ko1';
alter table lesson add column book varchar(20) not null default 'ko1';

create temporary table item_id_map (old_id varchar(20) primary key, new_id varchar(20) not null) on commit drop;
insert into item_id_map (old_id, new_id) values
    {rows};

update weakness w set item_id = m.new_id from item_id_map m where w.item_id = m.old_id;

-- 배열 순서를 지키며 바꾼다. 대응표에 없는 ID는 그대로
update lesson l set covered_item_ids = coalesce((
    select jsonb_agg(coalesce(m.new_id, e.value) order by e.ord)
    from jsonb_array_elements_text(l.covered_item_ids) with ordinality as e(value, ord)
    left join item_id_map m on m.old_id = e.value
), '[]'::jsonb)
where jsonb_array_length(l.covered_item_ids) > 0;

update lesson l set understanding = coalesce((
    select jsonb_object_agg(coalesce(m.new_id, e.key), e.value)
    from jsonb_each(l.understanding) as e(key, value)
    left join item_id_map m on m.old_id = e.key
), '{{}}'::jsonb)
where l.understanding <> '{{}}'::jsonb;
"""


if __name__ == "__main__":
    print(sql(), end="")
