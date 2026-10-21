package com.koreantutor.chat;

import com.koreantutor.lesson.Lesson;
import com.koreantutor.lesson.LessonRepository;
import com.koreantutor.record.LessonRecordRepository;
import com.koreantutor.student.Student;
import com.koreantutor.student.StudentRepository;
import com.koreantutor.student.Weakness;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 채팅 조회(lookup)용 도구. 읽기만 한다 — 채팅은 DB에 쓰지 않는다 (PRD 8-3). */
@Component
public class StudentLookupTools {

    private final StudentRepository students;
    private final LessonRepository lessons;
    private final LessonRecordRepository records;

    public StudentLookupTools(StudentRepository students, LessonRepository lessons, LessonRecordRepository records) {
        this.students = students;
        this.lessons = lessons;
        this.records = records;
    }

    @Tool(description = "등록된 모든 학생의 id, 이름, 모국어(ja|en), 수준 메모, 표준 등급(0=입문, 1~6급, null=미정), 다음에 배울 과, 상태(active|paused)를 목록으로 돌려준다.")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listStudents() {
        return students.findAll().stream().map(s -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", s.getId());
            m.put("name", s.getName());
            m.put("native_language", s.getNativeLanguage());
            m.put("level", s.getLevel());
            m.put("standard_level", s.getStandardLevel());
            m.put("next_unit", s.getNextUnit());
            m.put("status", s.getStatus());
            return m;
        }).toList();
    }

    @Tool(description = "학생 id로 프로필 전체를 돌려준다: 표준 등급, 목표 등급, 학습 목적, 목표, 관심사, 메모, 약점 목록(교재 항목 ID, 설명, 해결 여부, 생긴 날짜).")
    @Transactional(readOnly = true)
    public Map<String, Object> getStudentProfile(@ToolParam(description = "학생 id (listStudents의 id)") long studentId) {
        Student s = students.findById(studentId).orElse(null);
        if (s == null) return Map.of("error", "학생이 없습니다: " + studentId);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("name", s.getName());
        m.put("native_language", s.getNativeLanguage());
        m.put("level", s.getLevel());
        m.put("standard_level", s.getStandardLevel());
        m.put("target_level", s.getTargetLevel());
        m.put("persona", s.getPersona());
        m.put("goals", s.getGoals());
        m.put("interests", s.getInterests());
        m.put("next_unit", s.getNextUnit());
        m.put("notes", s.getNotes());
        m.put("weaknesses", s.getWeaknesses().stream().map(StudentLookupTools::weakness).toList());
        return m;
    }

    @Tool(description = "학생 id로 최근 수업 기록을 최신순으로 돌려준다: 회차, 날짜, 과, 상태, 다룬 교재 항목, 승인된 수업 후 기록(잘한 점, 오류, 숙제, 다음 수업 메모).")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> getRecentLessons(
            @ToolParam(description = "학생 id") long studentId,
            @ToolParam(description = "가져올 수업 수 (1~10)") int limit) {
        return lessons.findByStudentIdOrderByLessonNoDesc(studentId).stream()
                .limit(Math.max(1, Math.min(limit, 10)))
                .map(this::lesson).toList();
    }

    private Map<String, Object> lesson(Lesson l) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("lesson_no", l.getLessonNo());
        m.put("date", l.getLessonDate());
        m.put("unit_no", l.getUnitNo());
        m.put("status", l.getStatus());
        m.put("covered_item_ids", l.getCoveredItemIds());
        records.findByLessonId(l.getId()).filter(r -> r.getApproved() != null)
                .ifPresent(r -> m.put("record", r.getApproved()));
        return m;
    }

    private static Map<String, Object> weakness(Weakness w) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("item_id", w.getItemId());
        m.put("description", w.getDescription());
        m.put("resolved", w.isResolved());
        m.put("since", w.getCreatedAt().toLocalDate());
        return m;
    }
}
