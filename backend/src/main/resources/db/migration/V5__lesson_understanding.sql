-- 수업에서 다룬 항목별 이해도 (기획 ADR-0029, 기술 ADR-0033)
-- 수업 후 기록을 승인할 때 선생님이 확인한 값만 남는다: {항목 ID: confused | shaky | ok}. 장면이 없던 항목은 키가 없다.
-- 다음 수업 준비가 복습 항목 순서와 복습 시간을 정할 때 쓴다.

alter table lesson add column understanding jsonb not null default '{}';
