-- 옛 교재 항목 ID(u02-g01) → 표준 ID(std-g-001) / 교재 안 ID(ko1-u02-d01) (기획 ADR-0030, 기술 ADR-0032)
-- app.curriculum.migrate_ids가 만든 파일이다. 직접 고치지 말고 다시 만든다.

-- 교재 시리즈 (단원 시트 data/curriculum/<book>/). next_unit·unit_no는 이 교재의 과다
alter table student add column next_book varchar(20) not null default 'ko1';
alter table lesson add column book varchar(20) not null default 'ko1';

create temporary table item_id_map (old_id varchar(20) primary key, new_id varchar(20) not null) on commit drop;
insert into item_id_map (old_id, new_id) values
    ('u02-d01', 'ko1-u02-d01'),
    ('u02-e01', 'ko1-u02-e01'),
    ('u02-e02', 'ko1-u02-e02'),
    ('u02-g01', 'std-g-001'),
    ('u02-g02', 'std-g-037'),
    ('u02-v01', 'std-v-00404'),
    ('u02-v02', 'std-v-00436'),
    ('u02-v03', 'std-v-00178'),
    ('u02-v04', 'std-v-00440'),
    ('u02-v05', 'std-v-00142'),
    ('u02-v06', 'std-v-00482'),
    ('u02-v07', 'std-v-00723'),
    ('u02-v08', 'std-v-00009'),
    ('u02-v09', 'std-v-00275'),
    ('u02-v10', 'std-v-00730'),
    ('u02-v11', 'std-v-00523'),
    ('u02-v12', 'ko1-u02-x01'),
    ('u02-v13', 'ko1-u02-x02'),
    ('u02-v14', 'ko1-u02-x03'),
    ('u03-d01', 'ko1-u03-d01'),
    ('u03-e01', 'ko1-u03-e01'),
    ('u03-e02', 'ko1-u03-e02'),
    ('u03-e03', 'ko1-u03-e03'),
    ('u03-e04', 'ko1-u03-e04'),
    ('u03-e05', 'ko1-u03-e05'),
    ('u03-e06', 'ko1-u03-e06'),
    ('u03-e07', 'ko1-u03-e07'),
    ('u03-e08', 'ko1-u03-e08'),
    ('u03-e09', 'ko1-u03-e09'),
    ('u03-e10', 'ko1-u03-e10'),
    ('u03-g01', 'std-g-030'),
    ('u03-g02', 'std-g-007'),
    ('u03-g03', 'std-g-006'),
    ('u03-r01', 'ko1-u03-r01'),
    ('u03-v01', 'std-v-00136'),
    ('u03-v02', 'std-v-00185'),
    ('u03-v03', 'std-v-00521'),
    ('u03-v04', 'std-v-00584'),
    ('u03-v05', 'std-v-00709'),
    ('u03-v06', 'std-v-00598'),
    ('u03-v07', 'std-v-00005'),
    ('u03-v08', 'std-v-00222'),
    ('u03-v09', 'std-v-00187'),
    ('u03-v10', 'std-v-00675'),
    ('u03-v11', 'std-v-00561'),
    ('u03-v12', 'std-v-00476'),
    ('u03-v13', 'std-v-00597'),
    ('u03-v14', 'ko1-u03-x01'),
    ('u03-v15', 'ko1-u03-x02'),
    ('u04-d01', 'ko1-u04-d01'),
    ('u04-e01', 'ko1-u04-e01'),
    ('u04-e02', 'ko1-u04-e02'),
    ('u04-e03', 'ko1-u04-e03'),
    ('u04-e04', 'ko1-u04-e04'),
    ('u04-e05', 'ko1-u04-e05'),
    ('u04-e06', 'ko1-u04-e06'),
    ('u04-e07', 'ko1-u04-e07'),
    ('u04-e08', 'ko1-u04-e08'),
    ('u04-e09', 'ko1-u04-e09'),
    ('u04-e10', 'ko1-u04-e10'),
    ('u04-e11', 'ko1-u04-e11'),
    ('u04-e12', 'ko1-u04-e12'),
    ('u04-g01', 'std-g-002'),
    ('u04-g02', 'std-g-014'),
    ('u04-r01', 'ko1-u04-r01'),
    ('u04-v01', 'ko1-u04-x01'),
    ('u04-v02', 'std-v-00206'),
    ('u04-v03', 'std-v-00713'),
    ('u04-v04', 'std-v-00056'),
    ('u04-v05', 'std-v-00169'),
    ('u04-v06', 'std-v-00032'),
    ('u04-v07', 'std-v-00377'),
    ('u04-v08', 'std-v-00555'),
    ('u04-v09', 'std-v-00445'),
    ('u04-v10', 'std-v-00208'),
    ('u04-v11', 'std-v-00130'),
    ('u04-v12', 'ko1-u04-x02'),
    ('u04-v13', 'ko1-u04-x03'),
    ('u04-v14', 'ko1-u04-x04'),
    ('u04-v15', 'std-v-00636'),
    ('u04-v16', 'std-v-00524'),
    ('u04-v17', 'std-v-01637'),
    ('u04-v18', 'std-v-00661'),
    ('u04-v19', 'std-v-01318'),
    ('u04-v20', 'std-v-00668');

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
), '{}'::jsonb)
where l.understanding <> '{}'::jsonb;
