package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.document.DeleteDocRequest;
import com.mykb.proto.document.DocumentInfo;
import com.mykb.proto.document.DocumentServiceGrpc;
import com.mykb.proto.document.UploadDocRequest;
import com.mykb.proto.common.StatusResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DocumentClient {

    private final DocumentServiceGrpc.DocumentServiceBlockingStub stub;

    public DocumentInfo uploadDocument(Long kbId, String fileName, String fileExt,
                                       Long fileSize, String minioKey) {
        try {
            UploadDocRequest request = UploadDocRequest.newBuilder()
                    .setKbId(kbId)
                    .setFileName(fileName)
                    .setFileExt(fileExt)
                    .setFileSize(fileSize)
                    .setMinioKey(minioKey)
                    .build();
            DocumentInfo response = stub.uploadDocument(request);
            log.info("gRPC uploadDocument success: kbId={}, file={}", kbId, fileName);
            return response;
        } catch (Exception e) {
            log.error("gRPC uploadDocument failed: kbId={}, file={}, error={}", kbId, fileName, e.getMessage(), e);
            throw new BusinessException("Failed to upload document to Python service: " + e.getMessage());
        }
    }

    public void deleteDocument(Long kbId, Long fileId, String minioKey) {
        try {
            DeleteDocRequest request = DeleteDocRequest.newBuilder()
                    .setFileId(fileId)
                    .setKbId(kbId)
                    .setMinioKey(minioKey != null ? minioKey : "")
                    .build();
            @SuppressWarnings("unused")
            StatusResponse response = stub.deleteDocument(request);
            log.info("gRPC deleteDocument success: kbId={}, fileId={}", kbId, fileId);
        } catch (Exception e) {
            log.error("gRPC deleteDocument failed: kbId={}, fileId={}, error={}", kbId, fileId, e.getMessage(), e);
            throw new BusinessException("Failed to delete document on Python service: " + e.getMessage());
        }
    }
}
