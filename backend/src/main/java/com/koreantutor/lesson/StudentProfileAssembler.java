package com.koreantutor.lesson;

import com.koreantutor.student.Student;
import com.koreantutor.student.Weakness;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * DB의 학생 정보를 ai-server가 받는 StudentProfile 모양(snake_case)으로 만든다 (ADR-0005).
 * 모양: ai-server/app/agent/lesson_prep/schemas.py StudentProfile
 */
@Component
public class StudentProfileAssembler {

    private final LessonRepository lessons;

    public StudentProfileAssembler(LessonRepository lessons) {
        this.lessons = lessons;
    }

    public static String studentKey(Long studentId) {
        return "stu-" + studentId;
    }

    public Map<String, Object> assemble(Student s) {
        List<Weakness> active = s.activeWeaknesses();
        List<Map<String, Object>> history = lessons.findByStudentIdAndStatusOrderByLessonNo(s.getId(), Lesson.RECORDED).stream()
                .map(l -> Map.<String, Object>of("lesson_no", l.getLessonNo(), "unit_no", l.getUnitNo(), "item_ids", l.getCoveredItemIds(),
                        "understanding", l.getUnderstanding()))
                .toList();

        Map<String, Object> profile = new LinkedHashMap<>();
        profile.put("student_id", studentKey(s.getId()));
        profile.put("name", s.getName());
        profile.put("native_language", s.getNativeLanguage());
        profile.put("level", s.getLevel());
        profile.put("standard_level", s.getStandardLevel());
        profile.put("target_level", s.getTargetLevel());
        profile.put("persona", s.getPersona());
        profile.put("goals", s.getGoals());
        profile.put("interests", s.getInterests());
        // 교재 ID가 있는 약점은 ID 목록으로, 없는 것은 자유 서술로 나눠 보낸다
        profile.put("weaknesses", active.stream().map(Weakness::getItemId).filter(Objects::nonNull).toList());
        profile.put("weakness_notes", active.stream().filter(w -> w.getItemId() == null).map(Weakness::getDescription).toList());
        profile.put("lesson_history", history);
        profile.put("next_book", s.getNextBook());
        profile.put("next_unit", s.getNextUnit());
        profile.put("notes", s.getNotes());
        return profile;
    }
}
