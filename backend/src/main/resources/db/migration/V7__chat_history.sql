-- 채팅 대화 기록 (기획 ADR-0035, 기술 ADR-0041)
-- 플로팅 채팅과 AI 채팅 탭이 같은 대화를 쓴다. LLM 문맥(ChatMemory)도 이 표의 최근 메시지를 읽는다.

create table chat_conversation (
    id          varchar(64)  primary key,              -- 프론트가 만드는 conversationId 그대로
    title       varchar(100) not null,                 -- 첫 질문 앞 30자. 선생님이 바꿀 수 있다
    created_at  timestamptz  not null default now(),
    updated_at  timestamptz  not null default now()
);
create index chat_conversation_updated_idx on chat_conversation (updated_at desc);

create table chat_message (
    id               bigserial    primary key,
    conversation_id  varchar(64)  not null references chat_conversation (id) on delete cascade,
    role             varchar(10)  not null check (role in ('user', 'assistant')),
    text             text         not null,
    meta             jsonb        not null default '{}'::jsonb,  -- 답: intent, studentName, lang, sources, actions, error
    created_at       timestamptz  not null default now()
);
create index chat_message_conversation_idx on chat_message (conversation_id, id);
