package com.koreantutor.student;

import com.koreantutor.common.BaseTimeEntity;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "student")
public class Student extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;
    private String nativeLanguage;   // "ja" | "en"
    private String level = "";        // 수준 세부 메모 ("한글 읽기 가능, 받침 발음 약함")
    @JdbcTypeCode(SqlTypes.SMALLINT)
    private Integer standardLevel;    // 지금 배울 표준 등급 0(입문)~6. 기존 학생은 null (기획 ADR-0018)
    @JdbcTypeCode(SqlTypes.SMALLINT)
    private Integer targetLevel;      // 목표 표준 등급 1~6
    private LocalDate levelAssessedOn; // 레벨테스트 날짜
    private String persona;           // structured | conversation | travel | business (기획 ADR-0016)

    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> goals = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> interests = new ArrayList<>();

    private int nextUnit = 1;
    private int lessonMinutesDefault = 50;
    private String notes = "";
    private String status = "active"; // "active" | "paused"

    @OneToMany(mappedBy = "student", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("id")
    private List<Weakness> weaknesses = new ArrayList<>();

    protected Student() {
    }

    public Student(String name, String nativeLanguage) {
        this.name = name;
        this.nativeLanguage = nativeLanguage;
    }

    public void addWeakness(Weakness weakness) {
        weakness.setStudent(this);
        weaknesses.add(weakness);
    }

    public List<Weakness> activeWeaknesses() {
        return weaknesses.stream().filter(w -> !w.isResolved()).toList();
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getNativeLanguage() { return nativeLanguage; }
    public void setNativeLanguage(String nativeLanguage) { this.nativeLanguage = nativeLanguage; }
    public String getLevel() { return level; }
    public void setLevel(String level) { this.level = level; }
    public Integer getStandardLevel() { return standardLevel; }
    public void setStandardLevel(Integer standardLevel) { this.standardLevel = standardLevel; }
    public Integer getTargetLevel() { return targetLevel; }
    public void setTargetLevel(Integer targetLevel) { this.targetLevel = targetLevel; }
    public LocalDate getLevelAssessedOn() { return levelAssessedOn; }
    public void setLevelAssessedOn(LocalDate levelAssessedOn) { this.levelAssessedOn = levelAssessedOn; }
    public String getPersona() { return persona; }
    public void setPersona(String persona) { this.persona = persona; }
    public List<String> getGoals() { return goals; }
    public void setGoals(List<String> goals) { this.goals = new ArrayList<>(goals); }
    public List<String> getInterests() { return interests; }
    public void setInterests(List<String> interests) { this.interests = new ArrayList<>(interests); }
    public int getNextUnit() { return nextUnit; }
    public void setNextUnit(int nextUnit) { this.nextUnit = nextUnit; }
    public int getLessonMinutesDefault() { return lessonMinutesDefault; }
    public void setLessonMinutesDefault(int lessonMinutesDefault) { this.lessonMinutesDefault = lessonMinutesDefault; }
    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public List<Weakness> getWeaknesses() { return weaknesses; }
}
