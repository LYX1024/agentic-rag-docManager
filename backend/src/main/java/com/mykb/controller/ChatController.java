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

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;
    private final ThreadPoolExecutor executor;
    private final ObjectMapper objectMapper;

    public ChatController(ChatService chatService, ObjectMapper objectMapper) {
        this.chatService = chatService;
        this.objectMapper = objectMapper;
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
    public ApiResponse<List<ChatMessage>> getHistory(@PathVariable Long id,
                                                      @RequestParam(defaultValue = "false") boolean includeSystem) {
        List<ChatMessage> messages = chatService.getHistory(id);
        if (!includeSystem) {
            messages = messages.stream().filter(m -> !"system".equals(m.getRole())).collect(Collectors.toList());
        }
        return ApiResponse.success(messages);
    }

    @PostMapping("/session/{id}/message")
    public ApiResponse<Void> saveMessage(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        String role = (String) body.get("role");
        String content = (String) body.get("content");
        String sources = (String) body.getOrDefault("sources", null);
        chatService.saveMessage(id, role, content, sources);
        return ApiResponse.success();
    }

    @DeleteMapping("/session/{id}")
    public ApiResponse<Void> deleteSession(@PathVariable Long id) {
        chatService.deleteSession(id);
        return ApiResponse.success();
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
                            List<Map<String, Object>> jsonSources = sourcesList.stream()
                                    .map(s -> {
                                        Map<String, Object> m = new LinkedHashMap<>();
                                        m.put("file_name", s.getFileName());
                                        m.put("file_ext", s.getFileExt());
                                        m.put("chunk_text", s.getChunkText());
                                        m.put("chunk_index", s.getChunkIndex());
                                        m.put("score", s.getScore());
                                        return m;
                                    }).collect(Collectors.toList());
                            sourcesJson = objectMapper.writeValueAsString(jsonSources);
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
