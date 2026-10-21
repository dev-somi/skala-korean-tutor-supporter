package com.koreantutor.timelog;

import com.koreantutor.lesson.ReviewDecisionRepository;
import com.koreantutor.record.LessonRecordRepository;
import com.koreantutor.student.StudentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 시간 측정 요약 (PRD F5-4, F7, 성공 지표 10장) */
@Service
public class MetricsService {

    private static final int RECENT = 10;

    private final TimeLogRepository logs;
    private final BaselineRepository baselines;
    private final StudentRepository students;
    private final ReviewDecisionRepository decisions;
    private final LessonRecordRepository records;

    public MetricsService(TimeLogRepository logs, BaselineRepository baselines, StudentRepository students,
                          ReviewDecisionRepository decisions, LessonRecordRepository records) {
        this.logs = logs;
        this.baselines = baselines;
        this.students = students;
        this.decisions = decisions;
        this.records = records;
    }

    /** prep = 수업안 범주별 첫 검토 승인 비율, post = 수업 후 기록 초안 항목이 그대로 남은 비율 */
    @Transactional(readOnly = true)
    @SuppressWarnings("unchecked")
    public Map<String, Map<String, QualityMetrics.Rate>> quality() {
        List<Map<String, Object>[]> pairs = records.findAll().stream()
                .filter(r -> r.getApprovedAt() != null)
                .map(r -> (Map<String, Object>[]) new Map[]{r.getDraft(), r.getApproved()})
                .toList();
        Map<String, Map<String, QualityMetrics.Rate>> result = new LinkedHashMap<>();
        result.put("prep", QualityMetrics.firstApproveRates(decisions.findAllByOrderByLessonIdAscIdAsc()));
        result.put("post", QualityMetrics.keptDraftItems(pairs));
        return result;
    }

    public record Session(Long lessonId, Long studentId, String studentName, OffsetDateTime startedAt,
                          double totalMinutes, double aiWaitMinutes, double teacherMinutes) {
    }

    public record KindSummary(String kind, int sessions, Double avgTotalMinutes, Double avgAiWaitMinutes,
                              Double avgTeacherMinutes, Integer baselineMinutes, boolean baselineIsEstimate,
                              String baselineNote, Double reductionPercent, List<Session> recent) {
    }

    @Transactional(readOnly = true)
    public Map<String, KindSummary> summary() {
        Map<String, KindSummary> result = new LinkedHashMap<>();
        for (String kind : List.of(TimeLog.PREP, TimeLog.POST)) {
            result.put(kind, summarize(kind));
        }
        return result;
    }

    @Transactional
    public Baseline saveBaseline(String kind, int minutes, String note, boolean isEstimate) {
        if (!TimeLog.PREP.equals(kind) && !TimeLog.POST.equals(kind)) {
            throw new IllegalArgumentException("kind must be prep or post");
        }
        Baseline b = baselines.findById(kind).orElseGet(() -> new Baseline(kind));
        b.update(minutes, note, isEstimate);
        return baselines.save(b);
    }

    private KindSummary summarize(String kind) {
        List<TimeLog> finished = logs.findByKindAndFinishedAtIsNotNullOrderByStartedAtDesc(kind);
        List<Session> sessions = finished.stream().map(this::toSession).toList();
        Baseline baseline = baselines.findById(kind).orElse(null);

        Double avgTotal = average(sessions.stream().mapToDouble(Session::totalMinutes).toArray());
        Double avgAi = average(sessions.stream().mapToDouble(Session::aiWaitMinutes).toArray());
        Double avgTeacher = average(sessions.stream().mapToDouble(Session::teacherMinutes).toArray());
        Double reduction = (baseline != null && baseline.getMinutes() > 0 && avgTotal != null)
                ? round(100.0 * (baseline.getMinutes() - avgTotal) / baseline.getMinutes()) : null;

        return new KindSummary(kind, sessions.size(), avgTotal, avgAi, avgTeacher,
                baseline == null ? null : baseline.getMinutes(),
                baseline != null && baseline.isEstimate(),
                baseline == null ? null : baseline.getNote(),
                reduction, sessions.stream().limit(RECENT).toList());
    }

    private Session toSession(TimeLog log) {
        double total = Duration.between(log.getStartedAt(), log.getFinishedAt()).toSeconds() / 60.0;
        double ai = log.getAiWaitSeconds() / 60.0;
        double teacher = log.getTeacherSeconds() == null ? Math.max(0, total - ai) : log.getTeacherSeconds() / 60.0;
        String name = students.findById(log.getStudentId()).map(s -> s.getName()).orElse("(삭제됨)");
        return new Session(log.getLessonId(), log.getStudentId(), name, log.getStartedAt(), round(total), round(ai), round(teacher));
    }

    private static Double average(double[] values) {
        if (values.length == 0) return null;
        double sum = 0;
        for (double v : values) sum += v;
        return round(sum / values.length);
    }

    private static double round(double v) {
        return Math.round(v * 10) / 10.0;
    }
}
