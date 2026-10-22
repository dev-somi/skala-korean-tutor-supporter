package com.koreantutor.chat;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/** 채팅 대화 목록·기록 (AI 채팅 탭, 기술 ADR-0041) */
@RestController
@RequestMapping("/api/chat/conversations")
public class ChatHistoryController {

    private final ChatHistoryService history;

    public ChatHistoryController(ChatHistoryService history) {
        this.history = history;
    }

    public record ConversationView(String id, String title, OffsetDateTime createdAt, OffsetDateTime updatedAt) {
        static ConversationView of(ChatConversation c) {
            return new ConversationView(c.getId(), c.getTitle(), c.getCreatedAt(), c.getUpdatedAt());
        }
    }

    public record MessageView(long id, String role, String text, Map<String, Object> meta, OffsetDateTime createdAt) {
    }

    public record RenameRequest(@NotBlank @Size(max = 100) String title) {
    }

    @GetMapping
    public List<ConversationView> list() {
        return history.list().stream().map(ConversationView::of).toList();
    }

    @GetMapping("/{id}")
    public List<MessageView> messages(@PathVariable String id) {
        return history.messages(id).stream()
                .map(m -> new MessageView(m.getId(), m.getRole(), m.getText(), m.getMeta(), m.getCreatedAt()))
                .toList();
    }

    @PatchMapping("/{id}")
    public ConversationView rename(@PathVariable String id, @Valid @RequestBody RenameRequest req) {
        return ConversationView.of(history.rename(id, req.title()));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable String id) {
        history.delete(id);
        return ResponseEntity.noContent().build();
    }
}
