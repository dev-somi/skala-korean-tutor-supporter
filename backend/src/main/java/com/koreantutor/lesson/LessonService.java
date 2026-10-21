package com.koreantutor.lesson;

import com.koreantutor.common.ConflictException;
import com.koreantutor.common.NotFoundException;
import com.koreantutor.lesson.LessonDtos.CreateLessonRequest;
import com.koreantutor.lesson.LessonDtos.LessonView;
import com.koreantutor.student.Student;
import com.koreantutor.student.StudentService;
import com.koreantutor.timelog.TimeLog;
import com.koreantutor.timelog.TimeLogService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class LessonService {

    private final LessonRepository lessons;
    private final StudentService students;
    private final StudentProfileAssembler profiles;
    private final TimeLogService timeLogs;

    public LessonService(LessonRepository lessons, StudentService students,
                         StudentProfileAssembler profiles, TimeLogService timeLogs) {
        this.lessons = lessons;
        this.students = students;
        this.profiles = profiles;
        this.timeLogs = timeLogs;
    }

    @Transactional
    public LessonView create(Long studentId, CreateLessonRequest req) {
        Student s = students.find(studentId);
        Lesson lesson = new Lesson(s,
                lessons.maxLessonNo(studentId) + 1,
                Objects.requireNonNullElse(req.book(), s.getNextBook()),
                Objects.requireNonNullElse(req.unitNo(), s.getNextUnit()),
                Objects.requireNonNullElse(req.minutes(), s.getLessonMinutesDefault()),
                Objects.requireNonNullElse(req.targetLang(), s.getNativeLanguage()),
                req.lessonDate());
        return LessonView.from(lessons.save(lesson));
    }

    @Transactional(readOnly = true)
    public List<LessonView> listByStudent(Long studentId) {
        students.find(studentId);
        return lessons.findByStudentIdOrderByLessonNoDesc(studentId).stream().map(LessonView::from).toList();
    }

    @Transactional(readOnly = true)
    public LessonView get(Long id) {
        return LessonView.from(find(id));
    }

    /** 승인 대기 중인 수업안 (대시보드 할 일, PRD F5-3) */
    @Transactional(readOnly = true)
    public List<LessonView> pendingPrep() {
        return lessons.findPendingPrep().stream().map(LessonView::from).toList();
    }

    /** 수업안은 확정했는데 기록을 아직 쓰지 않은 수업 (수업일이 오늘이거나 지났거나, 날짜를 안 정한 것) */
    @Transactional(readOnly = true)
    public List<LessonView> toRecord() {
        return lessons.findToRecord(java.time.LocalDate.now()).stream().map(LessonView::from).toList();
    }

    /**
     * 수업 준비를 시작한다: 새 thread를 만들고 시간 측정을 시작하고, ai-server에 보낼 요청 본문을 만든다.
     * 이미 확정된 수업안도 다시 준비할 수 있다 (이전 결과는 지워진다).
     */
    @Transactional
    public Map<String, Object> beginPrep(Long lessonId) {
        Lesson lesson = find(lessonId);
        if (!Lesson.PLANNED.equals(lesson.getStatus()) && !Lesson.PREPARED.equals(lesson.getStatus())) {
            throw new ConflictException("이미 수업한 수업은 다시 준비할 수 없습니다 (status=" + lesson.getStatus() + ")");
        }
        String threadId = "lesson-" + lessonId + "-" + Instant.now().getEpochSecond();
        lesson.startPrep(threadId);
        Student s = lesson.getStudent();
        timeLogs.startIfAbsent(s.getId(), lessonId, TimeLog.PREP);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("thread_id", threadId);
        body.put("profile", profiles.assemble(s));
        body.put("book", lesson.getBook());
        body.put("unit_no", lesson.getUnitNo());
        body.put("lesson_minutes", lesson.getMinutes());
        body.put("target_lang", lesson.getTargetLang());
        body.put("output_subdir", StudentProfileAssembler.studentKey(s.getId()) + "/lesson-" + lessonId);
        return body;
    }

    /** 선생님 검토를 보낼 수 있는 상태인지 확인하고 thread ID를 돌려준다 */
    @Transactional(readOnly = true)
    public String reviewableThread(Long lessonId) {
        Lesson lesson = find(lessonId);
        if (lesson.getPrepThreadId() == null || !Lesson.PLANNED.equals(lesson.getStatus())) {
            throw new ConflictException("검토 대기 중인 수업안이 없습니다");
        }
        return lesson.getPrepThreadId();
    }

    @Transactional(readOnly = true)
    public String threadOf(Long lessonId) {
        String threadId = find(lessonId).getPrepThreadId();
        if (threadId == null) throw new NotFoundException("prep thread of lesson", lessonId);
        return threadId;
    }

    /** ai-server의 done 이벤트: 확정된 구성안·브리핑·파일을 저장한다. 다른 thread(이전 시도)의 결과는 무시한다. */
    @Transactional
    @SuppressWarnings("unchecked")
    public void completePrep(Long lessonId, Map<String, Object> done) {
        Lesson lesson = find(lessonId);
        if (!Objects.equals(lesson.getPrepThreadId(), done.get("thread_id"))) {
            return;
        }
        lesson.completePrep(
                (Map<String, Object>) done.get("plan"),
                (Map<String, Object>) done.get("briefing"),
                (Map<String, Object>) done.get("drafts"),
                (String) done.get("pptx_file"),
                (String) done.get("pdf_file"));
    }

    /** 이 수업의 파일 경로 (kind = pptx | pdf). 다른 파일은 내주지 않는다. */
    @Transactional(readOnly = true)
    public String fileOf(Long lessonId, String kind) {
        Lesson lesson = find(lessonId);
        String file = switch (kind) {
            case "pptx" -> lesson.getPptxFile();
            case "pdf" -> lesson.getPdfFile();
            default -> throw new IllegalArgumentException("kind must be pptx or pdf");
        };
        if (file == null) throw new NotFoundException(kind + " file of lesson", lessonId);
        return file;
    }

    Lesson find(Long id) {
        return lessons.findById(id).orElseThrow(() -> new NotFoundException("lesson", id));
    }
}
