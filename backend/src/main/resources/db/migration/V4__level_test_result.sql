-- 체험수업 레벨테스트 결과 (기획 ADR-0021, 기술 ADR-0019)
-- [결과 저장]을 누르면 코드가 판정한 추천 등급과 문항별 맞음/틀림을 남긴다.
-- 학생 카드에는 선생님이 확인해야 반영된다: pending → applied(학생에 반영) | dismissed(버림).

create table level_test_result (
    id               bigserial primary key,
    answers          jsonb        not null,            -- {문항 ID: true|false}
    score            jsonb        not null,            -- ai-server 판정 결과 그대로 (snake_case)
    suggested_level  smallint     check (suggested_level between 0 and 6),
    note             text         not null default '', -- 관찰 메모
    status           varchar(10)  not null default 'pending' check (status in ('pending', 'applied', 'dismissed')),
    student_id       bigint       references student (id) on delete set null,
    applied_level    smallint     check (applied_level between 0 and 6),  -- 선생님이 최종 고른 등급
    taken_at         timestamptz  not null default now(),
    decided_at       timestamptz
);
create index level_test_result_status_idx on level_test_result (status, id);
