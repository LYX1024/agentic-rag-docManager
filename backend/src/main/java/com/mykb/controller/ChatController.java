package com.mykb.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.mykb.dto.ApiResponse;
import com.mykb.dto.ChatSessionCreateRequest;
import com.mykb.entity.ChatMessage;
import com.mykb.entity.ChatSession;
import com.mykb.proto.chat.ChatService;
import com.mykb.service.ChatService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Iterator;
import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("/session")
    public ApiResponse<ChatSession> createSession(@Valid @RequestBody ChatSessionCreateRequest request,
                                                   HttpServletRequest httpRequest) {
        long userId = StpUtil.getLoginIdAsLong();
        ChatSession session = chatService.createSession(userId, request);
        return ApiResponse.success(session);
    }

    @GetMapping("/sessions")
    public ApiResponse<List<ChatSession>> listSessions(HttpServletRequest httpRequest) {
        long userId = StpUtil.getLoginIdAsLong();
        List<ChatSession> sessions = chatService.listSessions(userId);
        return ApiResponse.success(sessions);
    }

    @GetMapping("/session/{id}/history")
    public ApiResponse<List<ChatMessage>> getHistory(@PathVariable Long id) {
        List<ChatMessage> messages = chatService.getHistory(id);
        return ApiResponse.success(messages);
    }

    @GetMapping("/rag")
    public SseEmitter ragChat(@RequestParam String query,
                               @RequestParam Long kbId,
                               @RequestParam(required = false) String sessionId,
                               HttpServletRequest httpRequest) {
        long userId = StpUtil.getLoginIdAsLong();
        SseEmitter emitter = new SseEmitter(300000L);

        String effectiveSessionId;
        if (sessionId == null || sessionId.isBlank()) {
            ChatSessionCreateRequest csReq = new ChatSessionCreateRequest(
                    query.length() > 50 ? query.substring(0, 50) : query, kbId);
            ChatSession session = chatService.createSession(userId, csReq);
            effectiveSessionId = session.getId().toString();
        } else {
            effectiveSessionId = sessionId;
        }

        String finalSessionId = effectiveSessionId;
        new Thread(() -> {
            StringBuilder fullContent = new StringBuilder();
            StringBuilder sourcesJson = new StringBuilder();
            try {
                Iterator<ChatService.RagChatResponse> responses =
                        chatService.ragChat(finalSessionId, query, kbId);

                while (responses.hasNext()) {
                    ChatService.RagChatResponse chunk = responses.next();

                    if ("token".equals(chunk.getType())) {
                        fullContent.append(chunk.getContent());
                        SseEmitter.SseEventBuilder event = SseEmitter.event()
                                .name("token")
                                .data(chunk.getContent());
                        emitter.send(event);
                    } else if ("sources".equals(chunk.getType())) {
                        sourcesJson.append(chunk.getContent());
                        SseEmitter.SseEventBuilder event = SseEmitter.event()
                                .name("sources")
                                .data(chunk.getContent());
                        emitter.send(event);
                    }
                }

                chatService.saveMessage(Long.valueOf(finalSessionId), "user",
                        query, null);
                chatService.saveMessage(Long.valueOf(finalSessionId), "assistant",
                        fullContent.toString(),
                        sourcesJson.length() > 0 ? sourcesJson.toString() : null);

                emitter.complete();
                log.info("RAG chat completed: sessionId={}, contentLength={}", finalSessionId, fullContent.length());

            } catch (Exception e) {
                log.error("RAG chat error: sessionId={}, query={}, error={}", finalSessionId, query, e.getMessage(), e);
                try {
                    SseEmitter.SseEventBuilder event = SseEmitter.event()
                            .name("error")
                            .data("Chat error: " + e.getMessage());
                    emitter.send(event);
                } catch (IOException ex) {
                    log.error("Failed to send error event", ex);
                }
                emitter.completeWithError(e);
            }
        }, "rag-chat-" + finalSessionId).start();

        return emitter;
    }
}
