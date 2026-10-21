package com.koreantutor.student;

import com.koreantutor.student.StudentDtos.*;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/students")
public class StudentController {

    private final StudentService service;

    public StudentController(StudentService service) {
        this.service = service;
    }

    @GetMapping
    public List<StudentSummary> list() {
        return service.list();
    }

    @GetMapping("/{id}")
    public StudentDetail get(@PathVariable Long id) {
        return service.get(id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public StudentDetail create(@Valid @RequestBody StudentRequest req) {
        return service.create(req);
    }

    @PutMapping("/{id}")
    public StudentDetail update(@PathVariable Long id, @Valid @RequestBody StudentRequest req) {
        return service.update(id, req);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }

    /** 자연어 → 학생 카드 초안 {draft, warnings}. 저장하지 않는다. */
    @PostMapping("/intake")
    public Map<String, Object> intake(@Valid @RequestBody IntakeRequest req) {
        return service.intake(req.text());
    }
}
