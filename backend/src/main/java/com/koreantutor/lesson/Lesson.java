package com.koreantutor.lesson;

import com.koreantutor.common.BaseTimeEntity;
import com.koreantutor.student.Student;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 수업 1회. 상태: planned(만듦) → prepared(수업안 확정·PPT 생성) → done(수업함) → recorded(수업 후 기록 승인).
 * plan / briefing / drafts는 ai-server가 만든 JSON을 그대로(snake_case) 저장한다.
 */
@Entity
@Table(name = "lesson")
public class Lesson extends BaseTimeEntity {

    public static final String PLANNED = "planned";
    public static final String PREPARED = "prepared";
    public static final String DONE = "done";
    public static final String RECORDED = "recorded";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "student_id")
    private Student student;

    private int lessonNo;
    private LocalDate lessonDate;
    private int minutes;
    private String book = "ko1";  // 교재 시리즈 (단원 시트, 기술 ADR-0032). unitNo는 이 교재의 과
    private int unitNo;
    private String targetLang;
    private String status = PLANNED;
    private String prepThreadId;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> plan;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> briefing;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> drafts;

    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> coveredItemIds = new ArrayList<>();

    /** 다룬 항목별 이해도 {항목 ID: confused | shaky | ok}. 수업 후 기록 승인 때 확정 (기술 ADR-0033) */
    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, String> understanding = new LinkedHashMap<>();

    private String pptxFile;
    private String pdfFile;

    protected Lesson() {
    }

    public Lesson(Student student, int lessonNo, String book, int unitNo, int minutes, String targetLang, LocalDate lessonDate) {
        this.student = student;
        this.lessonNo = lessonNo;
        this.book = book;
        this.unitNo = unitNo;
        this.minutes = minutes;
        this.targetLang = targetLang;
        this.lessonDate = lessonDate;
    }

    /** 수업 준비를 (다시) 시작한다. 이전 결과는 지운다. */
    public void startPrep(String threadId) {
        this.prepThreadId = threadId;
        this.status = PLANNED;
        this.plan = null;
        this.briefing = null;
        this.drafts = null;
        this.pptxFile = null;
        this.pdfFile = null;
    }

    public void completePrep(Map<String, Object> plan, Map<String, Object> briefing, Map<String, Object> drafts,
                             String pptxFile, String pdfFile) {
        this.plan = plan;
        this.briefing = briefing;
        this.drafts = drafts;
        this.pptxFile = pptxFile;
        this.pdfFile = pdfFile;
        this.status = PREPARED;
    }

    public Long getId() { return id; }
    public Student getStudent() { return student; }
    public int getLessonNo() { return lessonNo; }
    public LocalDate getLessonDate() { return lessonDate; }
    public void setLessonDate(LocalDate lessonDate) { this.lessonDate = lessonDate; }
    public int getMinutes() { return minutes; }
    public void setMinutes(int minutes) { this.minutes = minutes; }
    public String getBook() { return book; }
    public int getUnitNo() { return unitNo; }
    public void setUnitNo(int unitNo) { this.unitNo = unitNo; }
    public String getTargetLang() { return targetLang; }
    public void setTargetLang(String targetLang) { this.targetLang = targetLang; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getPrepThreadId() { return prepThreadId; }
    public Map<String, Object> getPlan() { return plan; }
    public Map<String, Object> getBriefing() { return briefing; }
    public Map<String, Object> getDrafts() { return drafts; }
    public List<String> getCoveredItemIds() { return coveredItemIds; }
    public void setCoveredItemIds(List<String> ids) { this.coveredItemIds = new ArrayList<>(ids); }
    public Map<String, String> getUnderstanding() { return understanding; }
    public void setUnderstanding(Map<String, String> understanding) { this.understanding = new LinkedHashMap<>(understanding); }
    public String getPptxFile() { return pptxFile; }
    public String getPdfFile() { return pdfFile; }
}
