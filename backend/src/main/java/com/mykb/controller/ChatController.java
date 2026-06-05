package com.mykb.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.mykb.dto.ApiResponse;
import com.mykb.dto.ChatSessionCreateRequest;
import com.mykb.entity.ChatMessage;
import com.mykb.entity.ChatSession;
import com.mykb.proto.chat.RagChatChunk;
import com.mykb.proto.common.SourceDoc;
import com.mykb.service.ChatService;
import jakarta.annotation.PreDestroy;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

@Slf4j
@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;
    private final ThreadPoolExecutor executor;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
        this.executor = new ThreadPoolExecutor(
                4, 10, 60L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(100),
                r -> new Thread(r, "rag-chat"),
                new ThreadPoolExecutor.CallerRunsPolicy()
        );
        this.executor.allowCoreThreadTimeOut(true);
    }

    @PreDestroy
    public void shutdown() {
        executor.shutdown();
        try {
            if (!executor.awaitTermination(30, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

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
        executor.execute(() -> {
            StringBuilder fullContent = new StringBuilder();
            String sourcesJson = null;
            try {
                Iterator<RagChatChunk> responses =
                        chatService.ragChat(finalSessionId, query, kbId);

                while (responses.hasNext()) {
                    RagChatChunk chunk = responses.next();
                    String token = chunk.getToken();
                    if (!token.isEmpty()) {
                        fullContent.append(token);
                        emitter.send(SseEmitter.event()
                                .name("token")
                                .data(token));
                    }
                    if (chunk.getFinished()) {
                        List<SourceDoc> sourcesList = chunk.getSourcesList();
                        if (!sourcesList.isEmpty()) {
                            sourcesJson = sourcesList.toString();
                            emitter.send(SseEmitter.event()
                                    .name("sources")
                                    .data(sourcesJson));
                        }
                    }
                }

                chatService.saveMessage(Long.valueOf(finalSessionId), "user", query, null);
                chatService.saveMessage(Long.valueOf(finalSessionId), "assistant",
                        fullContent.toString(), sourcesJson);

                emitter.complete();
                log.info("RAG chat completed: sessionId={}, contentLength={}", finalSessionId, fullContent.length());

            } catch (Exception e) {
                log.error("RAG chat error: sessionId={}, query={}, error={}", finalSessionId, query, e.getMessage(), e);
                try {
                    emitter.send(SseEmitter.event()
                            .name("error")
                            .data("Chat error: " + e.getMessage()));
                } catch (IOException ex) {
                    log.error("Failed to send error event", ex);
                }
                emitter.complete();
            }
        });

        return emitter;
    }
}
