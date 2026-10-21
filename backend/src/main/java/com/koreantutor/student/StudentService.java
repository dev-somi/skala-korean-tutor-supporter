package com.koreantutor.student;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.common.NotFoundException;
import com.koreantutor.lesson.LessonRepository;
import com.koreantutor.student.StudentDtos.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class StudentService {

    private static final int MAIN_WEAKNESS_COUNT = 3;

    private final StudentRepository students;
    private final LessonRepository lessons;
    private final AiServerClient aiServer;

    public StudentService(StudentRepository students, LessonRepository lessons, AiServerClient aiServer) {
        this.students = students;
        this.lessons = lessons;
        this.aiServer = aiServer;
    }

    @Transactional(readOnly = true)
    public List<StudentSummary> list() {
        return students.findAllByOrderByStatusAscNameAsc().stream()
                .map(s -> new StudentSummary(s.getId(), s.getName(), s.getNativeLanguage(), s.getLevel(),
                        s.getStandardLevel(), s.getPersona(),
                        s.getNextUnit(), s.getStatus(),
                        lessons.lastLessonDate(s.getId()).orElse(null),
                        s.activeWeaknesses().stream().limit(MAIN_WEAKNESS_COUNT).map(Weakness::getDescription).toList()))
                .toList();
    }

    @Transactional(readOnly = true)
    public StudentDetail get(Long id) {
        return StudentDetail.from(find(id));
    }

    @Transactional
    public StudentDetail create(StudentRequest req) {
        Student student = new Student(req.name(), req.nativeLanguage());
        apply(student, req);
        return StudentDetail.from(students.save(student));
    }

    @Transactional
    public StudentDetail update(Long id, StudentRequest req) {
        Student student = find(id);
        apply(student, req);
        // 새로 추가한 약점의 id와 updated_at이 응답에 들어가도록 먼저 DB에 반영한다
        return StudentDetail.from(students.saveAndFlush(student));
    }

    @Transactional
    public void delete(Long id) {
        students.delete(find(id));
    }

    /** 자연어 → 학생 카드 초안. 저장하지 않는다 (선생님 확인 후 create로 저장, PRD F1-2). */
    public Map<String, Object> intake(String text) {
        return aiServer.intake(text);
    }

    public Student find(Long id) {
        return students.findById(id).orElseThrow(() -> new NotFoundException("student", id));
    }

    private void apply(Student s, StudentRequest req) {
        s.setName(req.name().trim());
        s.setNativeLanguage(req.nativeLanguage());
        s.setLevel(Objects.requireNonNullElse(req.level(), ""));
        s.setStandardLevel(req.standardLevel());
        s.setTargetLevel(req.targetLevel());
        s.setLevelAssessedOn(req.levelAssessedOn());
        s.setPersona(req.persona());
        s.setGoals(Objects.requireNonNullElse(req.goals(), List.of()));
        s.setInterests(Objects.requireNonNullElse(req.interests(), List.of()));
        if (req.nextUnit() != null) s.setNextUnit(req.nextUnit());
        if (req.lessonMinutesDefault() != null) s.setLessonMinutesDefault(req.lessonMinutesDefault());
        s.setNotes(Objects.requireNonNullElse(req.notes(), ""));
        if (req.status() != null) s.setStatus(req.status());
        if (req.weaknesses() != null) syncWeaknesses(s, req.weaknesses());
    }

    /** 폼에서 보낸 약점 목록과 맞춘다: id가 있으면 수정, 없으면 추가, 목록에서 빠진 것은 삭제. */
    private void syncWeaknesses(Student s, List<WeaknessDto> dtos) {
        Map<Long, Weakness> existing = s.getWeaknesses().stream()
                .collect(Collectors.toMap(Weakness::getId, Function.identity()));
        Set<Long> keep = new HashSet<>();
        for (WeaknessDto dto : dtos) {
            Weakness w = dto.id() == null ? null : existing.get(dto.id());
            if (w == null) {
                w = new Weakness(dto.itemId(), dto.description().trim(), null);
                s.addWeakness(w);
            } else {
                keep.add(w.getId());
                w.setItemId(dto.itemId());
                w.setDescription(dto.description().trim());
            }
            if (dto.isResolved()) w.resolve(); else w.reopen();
        }
        s.getWeaknesses().removeIf(w -> w.getId() != null && !keep.contains(w.getId()));
    }
}
