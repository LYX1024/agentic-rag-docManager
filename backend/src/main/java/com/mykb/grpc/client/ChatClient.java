package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.chat.ChatServiceGrpc;
import com.mykb.proto.chat.ChatService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Iterator;

@Slf4j
@Component
@RequiredArgsConstructor
public class ChatClient {

    private final ChatServiceGrpc.ChatServiceStub stub;

    public Iterator<ChatService.RagChatResponse> ragChat(String sessionId, String query, Long kbId) {
        try {
            ChatService.RagChatRequest request = ChatService.RagChatRequest.newBuilder()
                    .setSessionId(sessionId != null ? sessionId : "")
                    .setQuery(query)
                    .setKbId(kbId.toString())
                    .build();
            Iterator<ChatService.RagChatResponse> responses = stub.ragChat(request);
            log.info("gRPC ragChat initiated: sessionId={}, query={}, kbId={}", sessionId, query, kbId);
            return responses;
        } catch (Exception e) {
            log.error("gRPC ragChat failed: sessionId={}, query={}, kbId={}, error={}", sessionId, query, kbId, e.getMessage(), e);
            throw new BusinessException("Failed to chat with Python RAG service: " + e.getMessage());
        }
    }
}
