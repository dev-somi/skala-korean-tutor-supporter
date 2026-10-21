-- 데모 학생의 "실제로 수업해 온 것 같은" 이력을 넣는다. scripts/seed_demo.py로 학생 3명을 만든 뒤에 실행한다.
--   docker exec -i tutor-postgres psql -U tutor -d tutor -v ON_ERROR_STOP=1 < scripts/seed_demo_history.sql
--
-- 상황 (기준일 2026-10-21)
--   사토 유이: 10-07 체험수업 → 10-11 1회차, 10-18 2회차 (2과, 기록 승인 완료) → 10-22 3회차 (3과) 예정
--   히메나:   체험수업 일정만 잡힘 (TOPIK 6급 자격으로 등급만 정함). 아직 수업 없음
--   Jay:      10-18 체험수업 레벨테스트 (한글 1/5 → 입문) → 10-23 첫 수업 예정
--
-- 다시 실행해도 된다: 유이의 1·2회차와 4회차 이후 수업, 약점, Jay의 레벨테스트, 히메나의 수업을 지우고 새로 넣는다.
-- 유이의 3회차가 이미 있으면(수업 준비로 만든 수업안 포함) 날짜만 바꾸고 그대로 둔다. 모두 가상 데이터다 (기획 ADR-0011).

BEGIN;

DO $$
DECLARE
  yui bigint := (SELECT id FROM student WHERE name = '사토 유이');
  jay bigint := (SELECT id FROM student WHERE name = 'Jay');
  himena bigint := (SELECT id FROM student WHERE name = '히메나');
  l1 bigint; l2 bigint;
  w_iga bigint; w_nuna bigint; w_batchim bigint; w_anida bigint;
  r1 jsonb; r2 jsonb;
  lt bigint;
BEGIN
  IF yui IS NULL OR jay IS NULL OR himena IS NULL THEN
    RAISE EXCEPTION '먼저 python3 scripts/seed_demo.py 로 학생 3명을 만들어 주세요';
  END IF;

  -- ===================== 사토 유이 =====================
  UPDATE student SET level_assessed_on = '2026-10-07', next_unit = 3, created_at = '2026-10-07 20:00+09' WHERE id = yui;

  DELETE FROM lesson WHERE student_id = yui AND lesson_no <> 3;  -- 기록·시간 로그·검토 결정은 cascade
  DELETE FROM weakness WHERE student_id = yui;

  INSERT INTO lesson (student_id, lesson_no, lesson_date, minutes, unit_no, target_lang, status, covered_item_ids, created_at, updated_at)
  VALUES (yui, 1, '2026-10-11', 50, 2, 'ja', 'recorded',
          '["u02-v01","u02-v02","u02-v03","u02-v04","u02-v05","u02-v06","u02-v07","u02-g01"]',
          '2026-10-10 21:00+09', '2026-10-11 21:30+09')
  RETURNING id INTO l1;
  INSERT INTO lesson (student_id, lesson_no, lesson_date, minutes, unit_no, target_lang, status, covered_item_ids, created_at, updated_at)
  VALUES (yui, 2, '2026-10-18', 50, 2, 'ja', 'recorded',
          '["u02-v08","u02-v09","u02-v10","u02-v11","u02-v12","u02-v13","u02-v14","u02-g02"]',
          '2026-10-17 21:00+09', '2026-10-18 21:20+09')
  RETURNING id INTO l2;

  -- 3회차: 있으면 날짜만 맞추고, 없으면 준비 전 수업으로 만든다
  UPDATE lesson SET lesson_date = '2026-10-22', unit_no = 3 WHERE student_id = yui AND lesson_no = 3;
  IF NOT FOUND THEN
    INSERT INTO lesson (student_id, lesson_no, lesson_date, minutes, unit_no, target_lang)
    VALUES (yui, 3, '2026-10-22', 50, 3, 'ja');
  END IF;

  -- 약점 이력: 1회차에 셋이 생기고, 2회차에 이/가가 해결되고 '이/가 아니다'가 새로 생김
  INSERT INTO weakness (student_id, item_id, description, since_lesson_id, resolved, created_at, resolved_at)
  VALUES (yui, 'u02-g01', '이/가 구분', l1, true, '2026-10-11 21:30+09', '2026-10-18 21:20+09') RETURNING id INTO w_iga;
  INSERT INTO weakness (student_id, item_id, description, since_lesson_id, created_at)
  VALUES (yui, 'u02-v05', '누나/언니 구분 (여성 화자는 언니)', l1, '2026-10-11 21:30+09') RETURNING id INTO w_nuna;
  INSERT INTO weakness (student_id, item_id, description, since_lesson_id, created_at)
  VALUES (yui, NULL, '받침 발음 (특히 ㄹ 받침)', l1, '2026-10-11 21:30+09') RETURNING id INTO w_batchim;
  INSERT INTO weakness (student_id, item_id, description, since_lesson_id, created_at)
  VALUES (yui, 'u02-g02', '''이/가 아니다''에서 받침에 따라 이/가 고르기', l2, '2026-10-18 21:20+09') RETURNING id INTO w_anida;

  -- 1회차 기록 (AI 초안 → 선생님이 전부 승인)
  r1 := jsonb_build_object(
    'covered_item_ids', '["u02-v01","u02-v02","u02-v03","u02-v04","u02-v05","u02-v06","u02-v07","u02-g01"]'::jsonb,
    'strengths', '["가족 어휘 7개를 듣고 바로 따라 말함", "-이에요/예요로 가족 소개 문장을 혼자 만듦"]'::jsonb,
    'errors', '[
      {"student_said": "우리 누나는 대학생이에요", "correction": "우리 언니는 대학생이에요", "item_id": "u02-v05", "note": "여성 화자는 손위 여자 형제를 언니라고 부름"},
      {"student_said": "동생가 학생이에요", "correction": "동생이 학생이에요", "item_id": "u02-g01", "note": "받침이 있으면 이, 없으면 가"},
      {"student_said": "형이에요를 [형-이에요]로 끊어 읽음", "correction": "[형이에요] 이어서 읽기", "item_id": null, "note": "받침 뒤 모음 연음이 아직 어색함, 특히 ㄹ 받침(\"딸이에요\")"}
    ]'::jsonb,
    'weakness_changes', jsonb_build_array(
      jsonb_build_object('action', 'add', 'weakness_id', null, 'item_id', 'u02-g01', 'description', '이/가 구분'),
      jsonb_build_object('action', 'add', 'weakness_id', null, 'item_id', 'u02-v05', 'description', '누나/언니 구분 (여성 화자는 언니)'),
      jsonb_build_object('action', 'add', 'weakness_id', null, 'item_id', null, 'description', '받침 발음 (특히 ㄹ 받침)')),
    'homework', '[{"description": "연습 Ⅰ: 이/가를 넣어 대화 완성하기 + 가족 사진 보고 소개 문장 3개", "item_id": "u02-e01"}]'::jsonb,
    'next_lesson_note', '2과 직업 어휘와 ''이/가 아니다''. 이/가 다시 확인',
    'feedback_message', jsonb_build_object(
      'target_lang_text', E'ユイさん、今日もお疲れさまでした！\n家族の単語7つをすぐに覚えて、「우리 어머니예요」のように自分で紹介文が作れましたね。すばらしいです。\n一つだけ：女性が年上の姉妹を呼ぶときは「누나」ではなく「언니」です。\nそれから、パッチムがあるときは「이」、ないときは「가」。「동생이」と言いましょう。\n宿題は練習Ⅰ：이/가を入れて会話を完成させ、家族の写真を見て紹介文を3つ書いてみてください。次のレッスンも楽しみにしています！',
      'korean_text', E'유이 씨, 오늘도 수고했어요!\n가족 단어 7개를 바로 익히고 "우리 어머니예요"처럼 소개 문장을 혼자 만들었어요. 아주 좋아요.\n하나만: 여자가 손위 여자 형제를 부를 때는 "누나"가 아니라 "언니"예요.\n그리고 받침이 있으면 "이", 없으면 "가". "동생이"라고 해요.\n숙제는 연습 Ⅰ: 이/가를 넣어 대화를 완성하고, 가족 사진을 보고 소개 문장 3개를 써 보세요. 다음 수업도 기대할게요!'),
    'validation', jsonb_build_object('is_acceptable', true, 'reasoning', '메모에 있는 잘한 점·틀린 점·숙제만 담았고 초급 학습자에게 맞는 쉬운 문장이다.'),
    'warnings', '[]'::jsonb);
  INSERT INTO lesson_record (lesson_id, raw_note, draft, approved, approved_at, created_at, updated_at)
  VALUES (l1,
    E'2과 가족 어휘 아버지~형까지 7개 + 이/가. 단어는 금방 외움, 가족 소개 문장도 혼자 만듦.\n누나/언니 헷갈림 (본인이 여자인데 누나라고 함). 동생가 → 동생이, 받침 있으면 이 아직 헷갈림.\n형이에요 끊어 읽음, 받침 연음 어색 (딸이에요 특히). 숙제 연습 1 + 가족 사진 보고 3문장.',
    r1,
    jsonb_build_object(
      'coveredItemIds', r1->'covered_item_ids', 'strengths', r1->'strengths', 'errors', r1->'errors',
      'weaknessChanges', jsonb_build_array(
        jsonb_build_object('action', 'add', 'weaknessId', null, 'itemId', 'u02-g01', 'description', '이/가 구분'),
        jsonb_build_object('action', 'add', 'weaknessId', null, 'itemId', 'u02-v05', 'description', '누나/언니 구분 (여성 화자는 언니)'),
        jsonb_build_object('action', 'add', 'weaknessId', null, 'itemId', null, 'description', '받침 발음 (특히 ㄹ 받침)')),
      'homework', r1->'homework', 'nextLessonNote', r1->'next_lesson_note', 'feedbackMessage', r1->'feedback_message', 'nextUnit', 2),
    '2026-10-11 21:30+09', '2026-10-11 21:15+09', '2026-10-11 21:30+09');

  -- 2회차 기록
  r2 := jsonb_build_object(
    'covered_item_ids', '["u02-v08","u02-v09","u02-v10","u02-v11","u02-v12","u02-v13","u02-v14","u02-g02"]'::jsonb,
    'strengths', '["이/가를 이제 거의 틀리지 않음", "좋아하는 배우 이야기로 직업 어휘를 자연스럽게 씀", "숙제(연습 Ⅰ, 가족 소개 3문장)를 모두 해 옴"]'::jsonb,
    'errors', '[
      {"student_said": "의사이 아니에요", "correction": "의사가 아니에요", "item_id": "u02-g02", "note": "아니다 앞에서도 받침이 없으면 가"},
      {"student_said": "회사원예요", "correction": "회사원이에요", "item_id": null, "note": "받침 있는 명사 뒤에는 -이에요"}
    ]'::jsonb,
    'weakness_changes', jsonb_build_array(
      jsonb_build_object('action', 'resolve', 'weakness_id', w_iga, 'item_id', 'u02-g01', 'description', '이/가 구분'),
      jsonb_build_object('action', 'add', 'weakness_id', null, 'item_id', 'u02-g02', 'description', '''이/가 아니다''에서 받침에 따라 이/가 고르기')),
    'homework', '[{"description": "연습 Ⅱ: 그림 보고 \"회사원이 아니에요, 가수예요\" 대화 완성하기", "item_id": "u02-e02"}]'::jsonb,
    'next_lesson_note', '3과 시작 (좋아하다, -습니다, 을/를, 도). 이/가 아니다 복습 5분. 누나/언니 한 번 더',
    'feedback_message', jsonb_build_object(
      'target_lang_text', E'ユイさん、お疲れさまでした！\n「이/가」はもうほとんど間違えませんでしたね。好きな俳優の話で「배우예요」「가수예요」が自然に使えていました。\n一つ確認：「의사이 아니에요」→「의사가 아니에요」です。아니다の前でも、パッチムがなければ「가」です。\n宿題は練習Ⅱ：絵を見て「회사원이 아니에요、가수예요」の会話を完成させてください。\n次は3課「저도 드라마를 좋아합니다」に入ります！',
      'korean_text', E'유이 씨, 수고했어요!\n"이/가"는 이제 거의 틀리지 않았어요. 좋아하는 배우 이야기로 "배우예요", "가수예요"를 자연스럽게 썼어요.\n하나 확인: "의사이 아니에요" → "의사가 아니에요". 아니다 앞에서도 받침이 없으면 "가"예요.\n숙제는 연습 Ⅱ: 그림을 보고 "회사원이 아니에요, 가수예요" 대화를 완성해 보세요.\n다음에는 3과 「저도 드라마를 좋아합니다」를 시작해요!'),
    'validation', jsonb_build_object('is_acceptable', true, 'reasoning', '메모의 내용과 일치하고, 고칠 점이 구체적이며 학습자 수준에 맞다.'),
    'warnings', '[]'::jsonb);
  INSERT INTO lesson_record (lesson_id, raw_note, draft, approved, approved_at, created_at, updated_at)
  VALUES (l2,
    E'2과 직업 어휘 가수~직업이 뭐예요 + 이/가 아니다. 이/가는 이제 잘 씀 (해결).\n좋아하는 배우 이야기로 직업 단어 연습, 반응 좋음. 의사이 아니에요 → 의사가 아니에요, 아니다 앞에서 받침 판단 헷갈림. 회사원예요 → 회사원이에요.\n숙제 다 해 옴. 다음 숙제 연습 2. 다음 시간 3과.',
    r2,
    jsonb_build_object(
      'coveredItemIds', r2->'covered_item_ids', 'strengths', r2->'strengths', 'errors', r2->'errors',
      'weaknessChanges', jsonb_build_array(
        jsonb_build_object('action', 'resolve', 'weaknessId', w_iga, 'itemId', 'u02-g01', 'description', '이/가 구분'),
        jsonb_build_object('action', 'add', 'weaknessId', null, 'itemId', 'u02-g02', 'description', '''이/가 아니다''에서 받침에 따라 이/가 고르기')),
      'homework', r2->'homework', 'nextLessonNote', r2->'next_lesson_note', 'feedbackMessage', r2->'feedback_message', 'nextUnit', 3),
    '2026-10-18 21:20+09', '2026-10-18 21:05+09', '2026-10-18 21:20+09');

  -- 시간 측정 (지표 화면용): 수업 준비 / 수업 후 정리
  INSERT INTO time_log (student_id, lesson_id, kind, started_at, finished_at, ai_wait_seconds, teacher_seconds) VALUES
    (yui, l1, 'prep', '2026-10-10 21:00+09', '2026-10-10 21:14+09', 420, 420),
    (yui, l1, 'post', '2026-10-11 21:15+09', '2026-10-11 21:30+09', 60, 840),
    (yui, l2, 'prep', '2026-10-17 21:00+09', '2026-10-17 21:11+09', 400, 260),
    (yui, l2, 'post', '2026-10-18 21:05+09', '2026-10-18 21:20+09', 55, 845);

  -- ===================== 히메나: 체험수업 일정만 =====================
  DELETE FROM lesson WHERE student_id = himena;
  UPDATE student SET level_assessed_on = NULL WHERE id = himena;

  -- ===================== Jay: 체험수업 레벨테스트 =====================
  DELETE FROM level_test_result WHERE student_id = jay;
  INSERT INTO level_test_result (answers, score, suggested_level, note, status, student_id, applied_level, taken_at, decided_at)
  VALUES (
    '{"hangul-1": true, "hangul-2": false, "hangul-3": false, "hangul-4": false, "hangul-5": false}',
    '{"suggested_level": 0, "suggested_name": "입문 (한글부터)", "reason": "한글 읽기 1/5개 — 한글부터 시작한다", "hangul_correct": 1,
      "levels": [{"level": 1, "answered": 0, "correct": 0, "status": "untested"}, {"level": 2, "answered": 0, "correct": 0, "status": "untested"},
                 {"level": 3, "answered": 0, "correct": 0, "status": "untested"}, {"level": 4, "answered": 0, "correct": 0, "status": "untested"},
                 {"level": 5, "answered": 0, "correct": 0, "status": "untested"}, {"level": 6, "answered": 0, "correct": 0, "status": "untested"}]}',
    0,
    '한글은 "학교"만 읽음 (드라마에서 본 글자라고 함). 1급 문항은 진행하지 않음. "안녕하세요", "감사합니다", "사랑해요"는 소리로 앎. 읽기보다 회화 위주 희망',
    'applied', jay, 0, '2026-10-18 10:20+09', '2026-10-18 11:00+09')
  RETURNING id INTO lt;
  UPDATE student SET standard_level = 0, level_assessed_on = '2026-10-18', created_at = '2026-10-18 11:00+09' WHERE id = jay;
  UPDATE lesson SET lesson_date = '2026-10-23' WHERE student_id = jay AND lesson_no = 1;
END $$;

COMMIT;
