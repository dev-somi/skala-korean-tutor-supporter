package com.koreantutor.chat;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.aiclient.AiServerException;
import com.koreantutor.config.AppProperties;
import com.koreantutor.lesson.Lesson;
import com.koreantutor.lesson.LessonDtos.CreateLessonRequest;
import com.koreantutor.lesson.LessonDtos.LessonView;
import com.koreantutor.lesson.LessonRepository;
import com.koreantutor.lesson.LessonService;
import com.koreantutor.student.Student;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.MessageChatMemoryAdvisor;
import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 채팅 (PRD F6). 순서: 라우팅 게이트 → 권위 게이트 → intent별 처리.
 *
 * SSE 이벤트
 *   routing_decided {intent, student_id, student_name, reason}   ← 항상 가장 먼저 (프론트가 UI를 미리 정함)
 *   token           {text}                                       ← 답변 글 조각
 *   action          {type: open_intake|open_prep|open_record|open_student, ...}  ← 화면 이동 버튼
 *   sources         {forms, out_of_level, ungrounded_forms, removed_points, ai_note}  ← 문법 질문의 교재 근거 (token보다 먼저)
 *   done            {}
 *   error           {code, message, retryable}
 *
 * 작업 요청(수업 준비·수업 후 기록)은 채팅에서 끝까지 돌리지 않고, 수업을 만들어 검토 화면으로 연결한다.
 * 그 화면에서 진행 단계와 HITL 검토를 보여 준다 (PRD F6-3).
 */
@Service
public class ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatService.class);
    private static final Set<String> RECORDABLE = Set.of(Lesson.PLANNED, Lesson.PREPARED, Lesson.DONE);

    private static final String LOOKUP_SYSTEM = """
            당신은 한국어 선생님의 조수입니다. 도구로 학생 정보와 수업 기록을 조회해서 선생님의 질문에 한국어로 짧게 답하세요.
            - 반드시 도구로 확인한 내용만 답합니다. 기록에 없으면 없다고 말합니다.
            - 해결된 약점(resolved=true)과 아직 남은 약점을 구분합니다.
            - 교재 항목 ID(예: u03-g02)는 괄호 안에 함께 적어도 됩니다.
            %s""";
    private static final String GENERAL_SYSTEM = """
            당신은 외국인(일본어·영어 화자)에게 한국어를 가르치는 선생님들을 돕는 한국어 교육 전문가입니다.
            경력이 길지 않은 선생님이 바로 수업에 쓸 수 있게 한국어로 짧게 답하세요.
            - 선생님의 말은 질문입니다. 학생이 쓴 문장으로 보고 고치거나 평가하지 않습니다.
            - 인사나 잡담에는 한두 문장으로 답하고, 도울 수 있는 일(학생 조회, 수업 준비, 수업 기록, 문법 질문)을 짧게 알려 줍니다.
            - "이거", "그거"처럼 무엇을 묻는지 알 수 없으면 추측해서 설명하지 말고 무엇을 말하는지 되묻습니다.
            - 표현·문법·수업 방법을 설명할 때만 설명 → 예문 → 학습자가 자주 하는 실수 순서로 씁니다.""";

    private final RouterService router;
    private final ChatClient fast;
    private final ChatClient quality;
    private final ChatMemory memory;
    private final StudentLookupTools tools;
    private final LessonService lessons;
    private final LessonRepository lessonRepository;
    private final AiServerClient aiServer;
    private final JsonMapper json;
    private final long timeoutMillis;

    public ChatService(RouterService router,
                       @Qualifier("fastChatClient") ChatClient fast,
                       @Qualifier("qualityChatClient") ChatClient quality,
                       ChatMemory memory, StudentLookupTools tools, LessonService lessons,
                       LessonRepository lessonRepository, AiServerClient aiServer, JsonMapper json, AppProperties props) {
        this.router = router;
        this.fast = fast;
        this.quality = quality;
        this.memory = memory;
        this.tools = tools;
        this.lessons = lessons;
        this.lessonRepository = lessonRepository;
        this.aiServer = aiServer;
        this.json = json;
        this.timeoutMillis = props.aiServer().sseTimeout().toMillis();
    }

    public SseEmitter chat(String message, String conversationId) {
        SseEmitter emitter = new SseEmitter(timeoutMillis);
        Thread.ofVirtual().name("chat-" + conversationId).start(() -> {
            try {
                handle(new Out(emitter), message, conversationId);
                emitter.complete();
            } catch (ClientGone e) {
                emitter.complete();
            } catch (Exception e) {
                log.error("chat failed", e);
                boolean retryable = !(e instanceof AiServerException a) || a.isRetryable();
                send(emitter, "error", Map.of("code", "CHAT_ERROR", "message", String.valueOf(e.getMessage()), "retryable", retryable));
                emitter.complete();
            }
        });
        return emitter;
    }

    private void handle(Out out, String message, String conversationId) {
        RouteDecision raw = router.route(message, recent(conversationId));
        RouterService.Resolved resolved = router.resolve(raw);
        RouteDecision decision = resolved.decision();
        Student student = resolved.student();

        Map<String, Object> routing = new LinkedHashMap<>();
        routing.put("intent", decision.intent());
        routing.put("student_id", student == null ? null : student.getId());
        routing.put("student_name", student == null ? null : student.getName());
        routing.put("reason", decision.reason());
        out.event("routing_decided", routing);
        log.info("chat routed intent={} student_id={}", decision.intent(), student == null ? null : student.getId());

        if (resolved.studentNotFound()) {
            reply(out, conversationId, message, decision.reason() + ". 대시보드에서 학생을 먼저 등록하거나 이름을 확인해 주세요.");
            return;
        }

        switch (decision.intent()) {
            case RouteDecision.LOOKUP -> streamAnswer(out, fast.prompt()
                    .system(LOOKUP_SYSTEM.formatted(student == null ? "" : "질문 대상 학생: " + student.getName() + " (id " + student.getId() + ")"))
                    .user(message)
                    .tools(tools), conversationId);
            case RouteDecision.STUDENT_UPSERT -> upsert(out, conversationId, message, student);
            case RouteDecision.LESSON_PREP -> prep(out, conversationId, message, student, decision.minutes());
            case RouteDecision.POST_LESSON -> postLesson(out, conversationId, message, student);
            case RouteDecision.GRAMMAR_QA -> grammarQa(out, conversationId, message, student);
            default -> streamAnswer(out, quality.prompt().system(GENERAL_SYSTEM).user(message), conversationId);
        }
    }

    private void upsert(Out out, String conversationId, String message, Student student) {
        if (student != null) {
            out.event("action", Map.of("type", "open_student", "student_id", student.getId(), "label", student.getName() + " 정보 수정하기"));
            reply(out, conversationId, message, student.getName() + " 학생 정보는 학생 화면에서 고쳐 주세요. (자연어 수정은 아직 지원하지 않아요)");
            return;
        }
        Map<String, Object> result = aiServer.intake(message);
        out.event("action", Map.of("type", "open_intake", "label", "학생 카드 초안 확인하기", "intake", result));
        reply(out, conversationId, message, "학생 카드 초안을 만들었어요. 틀린 칸을 고친 뒤 저장해 주세요.");
    }

    private void prep(Out out, String conversationId, String message, Student student, Integer minutes) {
        LessonView lesson = lessons.create(student.getId(), new CreateLessonRequest(null, minutes, null, null));
        out.event("action", Map.of("type", "open_prep", "lesson_id", lesson.id(), "label", "수업 준비 화면 열기"));
        reply(out, conversationId, message, "%s 학생 %d회차 수업(%d과, %d분)을 만들었어요. 검토 화면에서 수업 준비를 시작합니다."
                .formatted(student.getName(), lesson.lessonNo(), lesson.unitNo(), lesson.minutes()));
    }

    private void postLesson(Out out, String conversationId, String message, Student student) {
        // 가장 최근의 아직 기록하지 않은 수업. 없으면 새로 만든다.
        Long lessonId = lessonRepository.findByStudentIdOrderByLessonNoDesc(student.getId()).stream()
                .filter(l -> RECORDABLE.contains(l.getStatus())).findFirst().map(Lesson::getId)
                .orElseGet(() -> lessons.create(student.getId(), new CreateLessonRequest(null, null, null, java.time.LocalDate.now())).id());
        out.event("action", Map.of("type", "open_record", "lesson_id", lessonId, "note", message, "label", "수업 후 기록 화면 열기"));
        reply(out, conversationId, message, student.getName() + " 학생의 수업 후 기록 화면에 메모를 넣어 두었어요. [정리하기]를 누르면 AI가 초안을 만듭니다.");
    }

    /**
     * 문법 질문 (PRD F6-4): ai-server가 교재 근거를 모으고 요점을 만든다. 근거 카드는 sources 이벤트로, 요점은 글로 보낸다.
     * 학생이 지정되면 그 학생의 모국어와 등급으로 근거 언어와 "아직 안 배운 문법"을 정한다.
     */
    @SuppressWarnings("unchecked")
    private void grammarQa(Out out, String conversationId, String message, Student student) {
        String lang = student == null || student.getNativeLanguage() == null ? "ja" : student.getNativeLanguage();
        Integer level = student == null ? null : student.getStandardLevel();
        Map<String, Object> result = aiServer.grammarQa(message, lang, level);

        Map<String, Object> sources = new LinkedHashMap<>();
        for (String key : List.of("forms", "out_of_level", "ungrounded_forms", "removed_points", "ai_note")) {
            sources.put(key, result.get(key));
        }
        out.event("sources", sources);

        List<String> points = (List<String>) result.getOrDefault("points", List.of());
        String text = points.stream().map(p -> "• " + p).collect(Collectors.joining("\n"));
        reply(out, conversationId, message, text);
    }

    private void streamAnswer(Out out, ChatClient.ChatClientRequestSpec spec, String conversationId) {
        spec.advisors(a -> a.advisors(MessageChatMemoryAdvisor.builder(memory).build())
                        .param(ChatMemory.CONVERSATION_ID, conversationId))
                .stream().content()
                .doOnNext(text -> out.event("token", Map.of("text", text)))
                .blockLast();
        out.event("done", Map.of());
    }

    /** LLM을 거치지 않는 고정 답변. 대화 기록에도 남긴다. */
    private void reply(Out out, String conversationId, String userMessage, String text) {
        memory.add(conversationId, List.of(new UserMessage(userMessage), new AssistantMessage(text)));
        out.event("token", Map.of("text", text));
        out.event("done", Map.of());
    }

    private String recent(String conversationId) {
        List<Message> messages = memory.get(conversationId);
        return messages.stream().skip(Math.max(0, messages.size() - 6))
                .map(m -> (m instanceof UserMessage ? "선생님: " : "조수: ") + m.getText())
                .collect(Collectors.joining("\n"));
    }

    private void send(SseEmitter emitter, String name, Object data) {
        try {
            emitter.send(SseEmitter.event().name(name).data(json.writeValueAsString(data)));
        } catch (IOException | IllegalStateException e) {
            throw new ClientGone(e);
        }
    }

    /** 이벤트를 보내는 작은 도우미 */
    private final class Out {
        private final SseEmitter emitter;

        Out(SseEmitter emitter) {
            this.emitter = emitter;
        }

        void event(String name, Object data) {
            send(emitter, name, data);
        }
    }

    private static final class ClientGone extends RuntimeException {
        ClientGone(Throwable cause) {
            super(cause);
        }
    }
}
