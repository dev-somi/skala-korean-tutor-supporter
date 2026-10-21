-- 학생 수준·목표·학습 목적 (기획 ADR-0016, ADR-0018, 기술 ADR-0017)
-- standard_level: 지금 배울 표준 등급. 0 = 입문(한글부터), 1~6 = 국립국어원 표준 교육과정 N급.
--   API는 저장할 때마다 필수로 받는다. 이미 있던 학생은 레벨테스트 결과를 모르므로 비워 두고, 다음에 고칠 때 고르게 한다.
-- level(기존 칸)은 수준 세부 메모로 쓴다 ("한글 읽기 가능, 받침 발음 약함").

alter table student
    add column standard_level    smallint    check (standard_level between 0 and 6),
    add column target_level      smallint    check (target_level between 1 and 6),
    add column level_assessed_on date,
    add column persona           varchar(20) check (persona in ('structured', 'conversation', 'travel', 'business'));
