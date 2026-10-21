-- 수업안 검토 결정 기록 (기획 ADR-0020: 주 지표 = 수정 없이 승인된 비율)
-- 검토를 보낼 때마다 범주별 결정을 한 줄씩 남긴다. 범주의 "첫 결정"이 approve면 AI 초안을 그대로 쓴 것이다.

create table review_decision (
    id          bigserial primary key,
    lesson_id   bigint      not null references lesson (id) on delete cascade,
    category    varchar(20) not null check (category in ('review', 'new_vocab', 'new_grammar', 'homework')),
    action      varchar(10) not null check (action in ('approve', 'edit', 'feedback')),
    decided_at  timestamptz not null default now()
);
create index review_decision_lesson_idx on review_decision (lesson_id, id);
