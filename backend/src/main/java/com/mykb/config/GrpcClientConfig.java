package com.mykb.config;

import com.mykb.proto.chat.ChatServiceGrpc;
import com.mykb.proto.document.DocumentServiceGrpc;
import com.mykb.proto.kb.KBManagementServiceGrpc;
import com.mykb.proto.search.SearchServiceGrpc;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class GrpcClientConfig {

    @Value("${grpc.rag-service.host}")
    private String host;

    @Value("${grpc.rag-service.port}")
    private int port;

    @Bean
    public ManagedChannel managedChannel() {
        return ManagedChannelBuilder
                .forAddress(host, port)
                .usePlaintext()
                .keepAliveWithoutCalls(true)
                .maxInboundMessageSize(100 * 1024 * 1024)
                .build();
    }

    @Bean
    public KBManagementServiceGrpc.KBManagementServiceBlockingStub kbManagementStub(ManagedChannel channel) {
        return KBManagementServiceGrpc.newBlockingStub(channel);
    }

    @Bean
    public DocumentServiceGrpc.DocumentServiceBlockingStub documentStub(ManagedChannel channel) {
        return DocumentServiceGrpc.newBlockingStub(channel);
    }

    @Bean
    public SearchServiceGrpc.SearchServiceBlockingStub searchStub(ManagedChannel channel) {
        return SearchServiceGrpc.newBlockingStub(channel);
    }

    @Bean
    public ChatServiceGrpc.ChatServiceBlockingStub chatStub(ManagedChannel channel) {
        return ChatServiceGrpc.newBlockingStub(channel);
    }
}
