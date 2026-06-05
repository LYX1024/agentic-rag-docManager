package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.common.Common;
import com.mykb.proto.document.DocumentServiceGrpc;
import com.mykb.proto.document.DocumentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DocumentClient {

    private final DocumentServiceGrpc.DocumentServiceBlockingStub stub;

    public DocumentService.UploadDocumentResponse uploadDocument(String kbId, String fileName, String fileExt,
                                                                  Long fileSize, String minioKey) {
        try {
            Common.FileRef fileRef = Common.FileRef.newBuilder()
                    .setFileName(fileName)
                    .setFileExt(fileExt)
                    .setFileSize(fileSize)
                    .setMinioKey(minioKey)
                    .build();
            DocumentService.UploadDocumentRequest request = DocumentService.UploadDocumentRequest.newBuilder()
                    .setKbId(kbId)
                    .setFile(fileRef)
                    .build();
            DocumentService.UploadDocumentResponse response = stub.uploadDocument(request);
            log.info("gRPC uploadDocument success: kbId={}, file={}, docId={}", kbId, fileName, response.getDocId());
            return response;
        } catch (Exception e) {
            log.error("gRPC uploadDocument failed: kbId={}, file={}, error={}", kbId, fileName, e.getMessage(), e);
            throw new BusinessException("Failed to upload document to Python service: " + e.getMessage());
        }
    }

    public void deleteDocument(Long kbId, String docId) {
        try {
            DocumentService.DeleteDocumentRequest request = DocumentService.DeleteDocumentRequest.newBuilder()
                    .setKbId(kbId.toString())
                    .setDocId(docId)
                    .build();
            stub.deleteDocument(request);
            log.info("gRPC deleteDocument success: kbId={}, docId={}", kbId, docId);
        } catch (Exception e) {
            log.error("gRPC deleteDocument failed: kbId={}, docId={}, error={}", kbId, docId, e.getMessage(), e);
            throw new BusinessException("Failed to delete document on Python service: " + e.getMessage());
        }
    }
}
