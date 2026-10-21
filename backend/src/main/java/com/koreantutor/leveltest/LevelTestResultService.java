package com.koreantutor.leveltest;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.common.ConflictException;
import com.koreantutor.common.NotFoundException;
import com.koreantutor.student.Student;
import com.koreantutor.student.StudentService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 레벨테스트 결과 저장과 확인 (기획 ADR-0021).
 * 저장할 때 ai-server가 판정한 추천 등급을 같이 남긴다. 학생 카드는 apply에서만 바뀐다 (선생님 확인).
 */
@Service
public class LevelTestResultService {

    private final LevelTestResultRepository results;
    private final StudentService students;
    private final AiServerClient aiServer;

    public LevelTestResultService(LevelTestResultRepository results, StudentService students, AiServerClient aiServer) {
        this.results = results;
        this.students = students;
        this.aiServer = aiServer;
    }

    public record ResultView(Long id, Integer suggestedLevel, Map<String, Object> score, int answered, String note,
                             String status, Long studentId, Integer appliedLevel, OffsetDateTime takenAt, OffsetDateTime decidedAt) {
        static ResultView from(LevelTestResult r) {
            return new ResultView(r.getId(), r.getSuggestedLevel(), r.getScore(), r.getAnswers().size(), r.getNote(),
                    r.getStatus(), r.getStudentId(), r.getAppliedLevel(), r.getTakenAt(), r.getDecidedAt());
        }
    }

    @Transactional
    public ResultView save(Map<String, Boolean> answers, String note) {
        if (answers.isEmpty()) throw new IllegalArgumentException("확인한 문항이 없어요");
        Map<String, Object> score = aiServer.levelTestScore(Map.of("answers", answers));
        Integer suggested = score.get("suggested_level") instanceof Number n ? n.intValue() : null;
        String trimmed = Objects.requireNonNullElse(note, "").trim();
        return ResultView.from(results.save(new LevelTestResult(answers, score, suggested, trimmed)));
    }

    @Transactional(readOnly = true)
    public ResultView get(Long id) {
        return ResultView.from(find(id));
    }

    @Transactional(readOnly = true)
    public List<ResultView> pending() {
        return results.findByStatusOrderByIdDesc("pending").stream().map(ResultView::from).toList();
    }

    /**
     * 선생님이 확인한 등급을 학생 카드에 넣는다. level이 null이면 추천 등급.
     * 레벨테스트 날짜도 함께 적고, 학생의 수준 세부 메모가 비어 있으면 관찰 메모로 채운다.
     */
    @Transactional
    public ResultView apply(Long id, Long studentId, Integer level) {
        LevelTestResult result = find(id);
        if (!result.isPending()) throw new ConflictException("이미 확인한 레벨테스트 결과예요");
        Integer chosen = level != null ? level : result.getSuggestedLevel();
        if (chosen == null) throw new IllegalArgumentException("추천 등급이 없어요. 등급을 골라 주세요");

        Student student = students.find(studentId);
        student.setStandardLevel(chosen);
        student.setLevelAssessedOn(LocalDate.ofInstant(result.getTakenAt().toInstant(), ZoneId.systemDefault()));
        if (student.getLevel().isBlank() && !result.getNote().isBlank()) student.setLevel(result.getNote());

        result.apply(studentId, chosen);
        return ResultView.from(result);
    }

    @Transactional
    public ResultView dismiss(Long id) {
        LevelTestResult result = find(id);
        if (!result.isPending()) throw new ConflictException("이미 확인한 레벨테스트 결과예요");
        result.dismiss();
        return ResultView.from(result);
    }

    private LevelTestResult find(Long id) {
        return results.findById(id).orElseThrow(() -> new NotFoundException("level test result", id));
    }
}
