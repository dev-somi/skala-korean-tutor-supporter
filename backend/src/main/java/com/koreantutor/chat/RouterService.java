package com.koreantutor.chat;

import com.koreantutor.student.Student;
import com.koreantutor.student.StudentRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.converter.BeanOutputConverter;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/** 채팅 입력을 분류한다. 단순 조회에 무거운 그래프를 돌리지 않기 위한 첫 관문 (참고노트 2장 #7). */
@Service
public class RouterService {

    private static final Logger log = LoggerFactory.getLogger(RouterService.class);

    private static final Set<String> INTENTS = Set.of(RouteDecision.LOOKUP, RouteDecision.STUDENT_UPSERT,
            RouteDecision.LESSON_PREP, RouteDecision.POST_LESSON, RouteDecision.GRAMMAR_QA, RouteDecision.GENERAL);
    private static final Set<String> NEEDS_STUDENT = Set.of(RouteDecision.LESSON_PREP, RouteDecision.POST_LESSON);

    private static final String PROMPT = """
            당신은 한국어 선생님용 학습관리 서비스의 요청 분류기입니다. 선생님의 마지막 메시지를 아래 중 하나로 분류하세요.

            - lookup: 학생 정보·약점·수업 기록을 묻는 질문 (예: "유이 요즘 약한 거 뭐야?", "지난 수업에 뭐 했지?")
            - student_upsert: 새 학생을 등록하거나 학생 정보를 바꾸려는 설명 (예: "일본인 대학생 유이, 드라마 좋아함…")
            - lesson_prep: 다음 수업 자료 준비 요청 (예: "Jay 다음 수업 30분으로 준비해줘")
            - post_lesson: 방금 끝난 수업의 메모·기록 (예: "3과 1~10 단어 함. 을/를 계속 틀림. 숙제는 연습문제 2번")
            - grammar_qa: 한국어 문법·표현의 뜻, 차이, 설명 방법을 묻는 질문 (예: "'은/는'과 '이/가' 차이를 일본인에게 어떻게 설명해?", "-아서랑 -(으)니까 뭐가 달라?", "사는이랑 살던 차이")
            - general: 그 밖의 질문 (예: "수업 분위기 좋게 하는 법", "숙제를 안 해 오는 학생은 어떻게 해?")

            studentName: 메시지(또는 최근 대화)에 나온 학생 이름. 아래 등록된 학생 이름 중 하나와 맞으면 그 이름 그대로. 없으면 null.
            minutes: 수업 시간(분)이 나오면 숫자, 없으면 null.
            reason: 한 줄 이유 (한국어).

            # 등록된 학생
            %s

            # 최근 대화
            %s
            """;

    private final ChatClient fast;
    private final StudentRepository students;

    public RouterService(@Qualifier("fastChatClient") ChatClient fast, StudentRepository students) {
        this.fast = fast;
        this.students = students;
    }

    public RouteDecision route(String message, String recentConversation) {
        String names = students.findAll().stream().map(Student::getName).collect(Collectors.joining(", "));
        BeanOutputConverter<RouteDecision> converter = new BeanOutputConverter<>(RouteDecision.class);
        ChatResponse response = fast.prompt()
                .system(PROMPT.formatted(names.isBlank() ? "(없음)" : names, recentConversation.isBlank() ? "(없음)" : recentConversation)
                        + "\n" + converter.getFormat())
                .user(message)
                .call()
                .chatResponse();
        // 응답이 여러 블록으로 올 수 있어서(빈 블록 + JSON 블록) 모든 결과의 글을 합친다
        String text = response == null ? null : response.getResults().stream()
                .map(g -> g.getOutput().getText())
                .filter(s -> s != null && !s.isBlank())
                .collect(Collectors.joining("\n"));
        try {
            return converter.convert(text);
        } catch (RuntimeException e) {
            // 분류에 실패해도 채팅은 계속된다: 일반 질문으로 처리
            log.warn("router output not parsable results={} text={}",
                    response == null ? null : response.getResults().stream()
                            .map(g -> g.getMetadata().getFinishReason() + ":" + g.getOutput().getText()).toList(), text);
            return new RouteDecision(RouteDecision.GENERAL, null, null, "요청을 분류하지 못해 일반 질문으로 답합니다");
        }
    }

    /**
     * 권위 게이트 (참고노트 4-1): LLM이 고른 intent와 학생 이름을 코드가 다시 확인한다.
     * - 모르는 intent → general
     * - 학생이 꼭 필요한 작업(수업 준비·수업 후 기록)인데 DB에 없는 학생이면 → general로 바꾸고 이유를 남긴다
     */
    public Resolved resolve(RouteDecision decision) {
        String intent = INTENTS.contains(decision.intent()) ? decision.intent() : RouteDecision.GENERAL;
        decision = decision.withIntent(intent, decision.reason());
        Optional<Student> student = findStudent(decision.studentName());
        if (NEEDS_STUDENT.contains(intent) && student.isEmpty()) {
            String who = decision.studentName() == null ? "학생 이름" : "'" + decision.studentName() + "'";
            return new Resolved(decision.withIntent(RouteDecision.GENERAL, who + "을(를) 찾지 못했습니다"), null, true);
        }
        return new Resolved(decision, student.orElse(null), false);
    }

    public record Resolved(RouteDecision decision, Student student, boolean studentNotFound) {
    }

    private Optional<Student> findStudent(String name) {
        if (name == null || name.isBlank()) return Optional.empty();
        Optional<Student> exact = students.findFirstByNameIgnoreCase(name.trim());
        if (exact.isPresent()) return exact;
        List<Student> partial = students.findByNameContainingIgnoreCase(name.trim());
        return partial.size() == 1 ? Optional.of(partial.get(0)) : Optional.empty();
    }
}
