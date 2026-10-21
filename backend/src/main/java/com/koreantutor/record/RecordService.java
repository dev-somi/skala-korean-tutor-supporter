package com.koreantutor.record;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.aiclient.SseRelay;
import com.koreantutor.common.ConflictException;
import com.koreantutor.common.NotFoundException;
import com.koreantutor.lesson.Lesson;
import com.koreantutor.lesson.LessonRepository;
import com.koreantutor.lesson.StudentProfileAssembler;
import com.koreantutor.record.RecordDtos.*;
import com.koreantutor.student.Student;
import com.koreantutor.student.Weakness;
import com.koreantutor.timelog.TimeLog;
import com.koreantutor.timelog.TimeLogService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.*;

/**
 * 수업 후 기록 (PRD F4). 메모 → ai-server post_lesson → AI 초안 저장(미처리) → 선생님 항목별 승인 → 프로필 반영.
 * AI 초안은 승인 전까지 학생 프로필에 아무 영향도 주지 않는다 (PRD 8-3).
 */
@Service
public class RecordService {

    private static final Logger log = LoggerFactory.getLogger(RecordService.class);
    private static final TypeReference<Map<String, Object>> MAP = new TypeReference<>() {
    };

    private final LessonRepository lessons;
    private final LessonRecordRepository records;
    private final StudentProfileAssembler profiles;
    private final TimeLogService timeLogs;
    private final AiServerClient aiServer;
    private final SseRelay relay;
    private final JsonMapper json;
    private final TransactionTemplate tx;

    public RecordService(LessonRepository lessons, LessonRecordRepository records, StudentProfileAssembler profiles,
                         TimeLogService timeLogs, AiServerClient aiServer, SseRelay relay, JsonMapper json,
                         TransactionTemplate tx) {
        this.lessons = lessons;
        this.records = records;
        this.profiles = profiles;
        this.timeLogs = timeLogs;
        this.aiServer = aiServer;
        this.relay = relay;
        this.json = json;
        this.tx = tx;
    }

    /** 메모를 보내 AI 초안을 만든다 (SSE). done을 받으면 미처리 기록으로 저장한다. */
    public SseEmitter draft(Long lessonId, RecordRequest req) {
        Map<String, Object> body = tx.execute(status -> {
            Lesson lesson = findLesson(lessonId);
            records.findByLessonId(lessonId).filter(LessonRecord::isApproved).ifPresent(r -> {
                throw new ConflictException("이미 승인한 기록이 있습니다");
            });
            Student s = lesson.getStudent();
            timeLogs.startIfAbsent(s.getId(), lessonId, TimeLog.POST, req.noteStartedAt());

            Map<String, Object> info = new LinkedHashMap<>();
            info.put("lesson_no", lesson.getLessonNo());
            info.put("book", lesson.getBook());
            info.put("unit_no", lesson.getUnitNo());
            info.put("minutes", lesson.getMinutes());
            info.put("target_lang", lesson.getTargetLang());
            info.put("plan", lesson.getPlan());

            Map<String, Object> b = new LinkedHashMap<>();
            b.put("profile", profiles.assemble(s));
            b.put("lesson", info);
            b.put("raw_note", req.rawNote());
            b.put("current_weaknesses", s.activeWeaknesses().stream().map(w -> {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", w.getId());
                m.put("item_id", w.getItemId());
                m.put("description", w.getDescription());
                return m;
            }).toList());
            return b;
        });

        return relay.relay(aiServer.postLesson(body),
                (event, elapsed) -> onEvent(lessonId, req.rawNote(), event, elapsed),
                elapsed -> timeLogs.addAiWait(lessonId, TimeLog.POST, elapsed));
    }

    @Transactional(readOnly = true)
    public RecordView get(Long lessonId) {
        return records.findByLessonId(lessonId).map(RecordView::from)
                .orElseThrow(() -> new NotFoundException("record of lesson", lessonId));
    }

    @Transactional(readOnly = true)
    public List<RecordView> pending() {
        return records.findPending().stream().map(RecordView::from).toList();
    }

    /**
     * 선생님이 승인한 항목만 반영한다: 다룬 항목·이해도 → 수업 이력, 약점 추가·해결 → 프로필, 수업 상태 → recorded.
     * 권위 게이트 2단계: 해결할 약점이 정말 이 학생의 것인지 여기서 한 번 더 확인한다.
     */
    @Transactional
    public RecordView approve(Long lessonId, ApproveRequest req) {
        LessonRecord record = records.findByLessonId(lessonId)
                .orElseThrow(() -> new NotFoundException("record of lesson", lessonId));
        if (record.isApproved()) throw new ConflictException("이미 승인한 기록입니다");
        Lesson lesson = record.getLesson();
        Student student = lesson.getStudent();

        Map<Long, Weakness> owned = new HashMap<>();
        student.getWeaknesses().forEach(w -> owned.put(w.getId(), w));
        for (WeaknessChange change : Objects.requireNonNullElse(req.weaknessChanges(), List.<WeaknessChange>of())) {
            if ("resolve".equals(change.action())) {
                Weakness w = owned.get(change.weaknessId());
                if (w == null) throw new IllegalArgumentException("이 학생의 약점이 아닙니다: " + change.weaknessId());
                w.resolve();
            } else {
                student.addWeakness(new Weakness(change.itemId(), change.description().trim(), lessonId));
            }
        }

        lesson.setCoveredItemIds(req.coveredItemIds());
        lesson.setUnderstanding(Objects.requireNonNullElse(req.understanding(), Map.of()));
        lesson.setStatus(Lesson.RECORDED);
        if (req.nextUnit() != null) student.setNextUnit(req.nextUnit());

        record.approve(json.convertValue(req, MAP));
        timeLogs.finish(lessonId, TimeLog.POST);
        log.info("record approved lesson_id={} student_id={}", lessonId, student.getId());
        return RecordView.from(record);
    }

    private void onEvent(Long lessonId, String rawNote, ServerSentEvent<String> event, Duration elapsed) {
        if (!"done".equals(event.event())) return;
        Map<String, Object> done = json.readValue(event.data(), MAP);
        tx.executeWithoutResult(status -> {
            Lesson lesson = findLesson(lessonId);
            LessonRecord record = records.findByLessonId(lessonId).orElseGet(() -> new LessonRecord(lesson));
            @SuppressWarnings("unchecked")
            Map<String, Object> draft = new LinkedHashMap<>((Map<String, Object>) done.get("record_draft"));
            draft.put("warnings", done.get("warnings"));
            draft.put("validation", done.get("validation"));
            record.saveDraft(rawNote, draft);
            records.save(record);
            if (Lesson.PLANNED.equals(lesson.getStatus()) || Lesson.PREPARED.equals(lesson.getStatus())) {
                lesson.setStatus(Lesson.DONE);
            }
        });
        // AI 대기 시간은 스트림이 끝날 때(relay의 onFinished) 더한다. 승인 전까지 세션이 열려 있으므로 여기서는 더하지 않는다.
    }

    private Lesson findLesson(Long id) {
        return lessons.findById(id).orElseThrow(() -> new NotFoundException("lesson", id));
    }
}
