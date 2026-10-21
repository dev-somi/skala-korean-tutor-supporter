-- PRD 7장 데이터 모델. AI가 만든 구조(구성안·브리핑·추출 결과)는 모양이 자주 바뀌어서 jsonb로 둔다 (ADR-0002).
-- jsonb 안의 키는 ai-server가 만든 그대로(snake_case) 저장한다.

create table student (
    id                      bigserial primary key,
    name                    varchar(100) not null,
    native_language         varchar(2)   not null check (native_language in ('ja', 'en')),
    level                   varchar(200) not null default '',
    goals                   jsonb        not null default '[]',
    interests               jsonb        not null default '[]',
    next_unit               int          not null default 1,
    lesson_minutes_default  int          not null default 50,
    notes                   text         not null default '',
    status                  varchar(10)  not null default 'active' check (status in ('active', 'paused')),
    created_at              timestamptz  not null default now(),
    updated_at              timestamptz  not null default now()
);

create table weakness (
    id               bigserial primary key,
    student_id       bigint       not null references student (id) on delete cascade,
    item_id          varchar(20),                 -- 교재 항목 ID (없으면 자유 서술만)
    description      varchar(500) not null,
    since_lesson_id  bigint,
    resolved         boolean      not null default false,
    created_at       timestamptz  not null default now(),
    resolved_at      timestamptz
);
create index weakness_student_idx on weakness (student_id);

create table lesson (
    id                bigserial primary key,
    student_id        bigint      not null references student (id) on delete cascade,
    lesson_no         int         not null,
    lesson_date       date,
    minutes           int         not null,
    unit_no           int         not null,
    target_lang       varchar(2)  not null check (target_lang in ('ja', 'en')),
    status            varchar(10) not null default 'planned'
                          check (status in ('planned', 'prepared', 'done', 'recorded')),
    prep_thread_id    varchar(64),               -- ai-server LangGraph thread (ADR-0002)
    plan              jsonb,                     -- 승인된 구성안
    briefing          jsonb,                     -- 선생님 브리핑
    drafts            jsonb,                     -- 범주별 설명·대본
    covered_item_ids  jsonb       not null default '[]',  -- 실제로 다룬 항목 (수업 후 기록 승인 시 확정)
    pptx_file         varchar(300),
    pdf_file          varchar(300),
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    unique (student_id, lesson_no)
);

create table lesson_record (
    id           bigserial primary key,
    lesson_id    bigint      not null unique references lesson (id) on delete cascade,
    raw_note     text        not null,
    draft        jsonb       not null,           -- AI 추출 결과 (post_lesson)
    approved     jsonb,                          -- 선생님이 승인한 내용
    approved_at  timestamptz,                    -- null = 미처리 기록
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

create table time_log (
    id               bigserial primary key,
    student_id       bigint      not null references student (id) on delete cascade,
    lesson_id        bigint      not null references lesson (id) on delete cascade,
    kind             varchar(4)  not null check (kind in ('prep', 'post')),
    started_at       timestamptz not null,
    finished_at      timestamptz,
    ai_wait_seconds  int         not null default 0,   -- AI 응답을 기다린 시간 (SSE 스트림 길이 합)
    teacher_seconds  int
);
create index time_log_lesson_idx on time_log (lesson_id, kind);

create table baseline (
    kind         varchar(4)  primary key check (kind in ('prep', 'post')),
    minutes      int         not null,
    note         text        not null default '',
    is_estimate  boolean     not null default false,
    updated_at   timestamptz not null default now()
);
