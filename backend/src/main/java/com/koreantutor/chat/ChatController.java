package com.koreantutor.chat;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService service;

    public ChatController(ChatService service) {
        this.service = service;
    }

    public record ChatRequest(@NotBlank @Size(max = 4000) String message,
                              @NotBlank @Pattern(regexp = "[A-Za-z0-9_-]{1,64}") String conversationId,
                              @Pattern(regexp = "auto|ja|en") String lang) {
    }

    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@Valid @RequestBody ChatRequest req) {
        return service.chat(req.message(), req.conversationId(), req.lang() == null ? ChatService.LANG_AUTO : req.lang());
    }
}
