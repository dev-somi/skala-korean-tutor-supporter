package com.koreantutor.report;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.record.LessonRecord;
import com.koreantutor.record.LessonRecordRepository;
import com.koreantutor.student.Student;
import com.koreantutor.student.StudentService;
import com.koreantutor.student.Weakness;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.*;

/**
 * 학습자별 진도·향상 리포트 (기획 ADR-0019, 기술 ADR-0018).
 * DB에서 승인된 수업 기록과 약점을 모아 ai-server로 보내고, 계산 결과를 그대로 돌려준다 (ADR-0005).
 * 저장하지 않는다. 선생님이 화면에서 학생용 문장을 고쳐 복사해 보낸다.
 */
@RestController
@RequestMapping("/api/students/{studentId}/report")
public class ReportController {

    private final StudentService students;
    private final LessonRecordRepository records;
    private final AiServerClient aiServer;

    public ReportController(StudentService students, LessonRecordRepository records, AiServerClient aiServer) {
        this.students = students;
        this.records = records;
        this.aiServer = aiServer;
    }

    /** from이 없으면 첫 수업부터, to가 없으면 오늘까지 */
    @GetMapping
    @Transactional(readOnly = true)
    public Map<String, Object> report(@PathVariable Long studentId,
                                      @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                      @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        Student s = students.find(studentId);

        Map<String, Object> student = new LinkedHashMap<>();
        student.put("name", s.getName());
        student.put("native_language", s.getNativeLanguage());
        student.put("standard_level", s.getStandardLevel());
        student.put("target_level", s.getTargetLevel());
        student.put("next_unit", s.getNextUnit());

        List<Map<String, Object>> lessons = records.findApprovedByStudent(studentId).stream().map(ReportController::lesson).toList();
        List<Map<String, Object>> weaknesses = s.getWeaknesses().stream().map(ReportController::weakness).toList();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("student", student);
        body.put("date_from", from);
        body.put("date_to", Objects.requireNonNullElse(to, LocalDate.now()));
        body.put("lessons", lessons);
        body.put("weaknesses", weaknesses);
        return aiServer.progressReport(body);
    }

    private static Map<String, Object> lesson(LessonRecord r) {
        var l = r.getLesson();
        Map<String, Object> approved = Objects.requireNonNullElse(r.getApproved(), Map.of());
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("lesson_no", l.getLessonNo());
        // 수업 날짜를 비워 둔 수업은 기록을 승인한 날로 센다
        m.put("date", l.getLessonDate() != null ? l.getLessonDate() : r.getApprovedAt().toLocalDate());
        m.put("minutes", l.getMinutes());
        m.put("unit_no", l.getUnitNo());
        m.put("covered_item_ids", l.getCoveredItemIds());
        m.put("strengths", approved.getOrDefault("strengths", List.of()));
        m.put("errors", approved.getOrDefault("errors", List.of()));
        return m;
    }

    private static Map<String, Object> weakness(Weakness w) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("item_id", w.getItemId());
        m.put("description", w.getDescription());
        m.put("resolved", w.isResolved());
        m.put("created_at", w.getCreatedAt().toLocalDate());
        m.put("resolved_at", Optional.ofNullable(w.getResolvedAt()).map(OffsetDateTime::toLocalDate).orElse(null));
        return m;
    }
}
