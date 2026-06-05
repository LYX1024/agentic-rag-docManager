package com.mykb.service;

import cn.hutool.core.util.IdUtil;
import com.mykb.entity.KnowledgeFile;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.DocumentClient;
import com.mykb.proto.document.DocumentService;
import com.mykb.repository.FileChunkRepository;
import com.mykb.repository.KnowledgeFileRepository;
import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final MinioClient minioClient;
    private final KnowledgeFileRepository fileRepository;
    private final FileChunkRepository chunkRepository;
    private final DocumentClient documentClient;

    @Value("${minio.bucket-name}")
    private String bucketName;

    @Transactional
    public KnowledgeFile uploadFile(Long kbId, MultipartFile file) {
        String originalFilename = file.getOriginalFilename();
        String fileExt = "";
        if (originalFilename != null && originalFilename.contains(".")) {
            fileExt = originalFilename.substring(originalFilename.lastIndexOf("."));
        }
        String uuid = IdUtil.fastSimpleUUID();
        String minioKey = kbId + "/" + uuid + "/" + originalFilename;

        try {
            ensureBucketExists();

            try (InputStream inputStream = file.getInputStream()) {
                minioClient.putObject(
                        PutObjectArgs.builder()
                                .bucket(bucketName)
                                .object(minioKey)
                                .stream(inputStream, file.getSize(), -1)
                                .contentType(file.getContentType())
                                .build()
                );
            }
            log.info("File uploaded to MinIO: bucket={}, key={}", bucketName, minioKey);
        } catch (Exception e) {
            log.error("MinIO upload failed: {}", e.getMessage(), e);
            throw new BusinessException("File upload to MinIO failed: " + e.getMessage());
        }

        KnowledgeFile kf = new KnowledgeFile();
        kf.setKbId(kbId);
        kf.setFileName(originalFilename);
        kf.setFileExt(fileExt);
        kf.setFileSize(file.getSize());
        kf.setFilePathInMinio(minioKey);
        kf.setStatus("UPLOADED");
        KnowledgeFile saved = fileRepository.save(kf);
        log.info("KnowledgeFile saved: fileId={}, kbId={}, filename={}", saved.getId(), kbId, originalFilename);

        try {
            documentClient.uploadDocument(kbId.toString(), originalFilename, fileExt, file.getSize(), minioKey);
            saved.setStatus("COMPLETED");
            fileRepository.save(saved);
            log.info("Document processing completed by Python service: fileId={}", saved.getId());
        } catch (Exception e) {
            saved.setStatus("FAILED");
            saved.setErrorMsg(e.getMessage());
            fileRepository.save(saved);
            log.error("Python document processing failed: fileId={}, error={}", saved.getId(), e.getMessage(), e);
            throw new BusinessException("Document uploaded to MinIO but Python processing failed: " + e.getMessage());
        }

        return saved;
    }

    public Page<KnowledgeFile> listDocuments(Long kbId, PageRequest pageRequest) {
        return fileRepository.findByKbId(kbId, pageRequest);
    }

    @Transactional
    public void deleteDocument(Long fileId) {
        KnowledgeFile kf = fileRepository.findById(fileId)
                .orElseThrow(() -> new BusinessException(404, "Document not found"));

        try {
            minioClient.removeObject(
                    RemoveObjectArgs.builder()
                            .bucket(bucketName)
                            .object(kf.getFilePathInMinio())
                            .build()
            );
            log.info("File removed from MinIO: key={}", kf.getFilePathInMinio());
        } catch (Exception e) {
            log.warn("MinIO deletion failed (non-fatal): key={}, error={}", kf.getFilePathInMinio(), e.getMessage());
        }

        chunkRepository.deleteByFileId(fileId);
        log.info("Chunks deleted for fileId={}", fileId);

        try {
            documentClient.deleteDocument(kf.getKbId(), kf.getId().toString());
        } catch (Exception e) {
            log.warn("Python document deletion failed (non-fatal): fileId={}, error={}", fileId, e.getMessage());
        }

        fileRepository.delete(kf);
        log.info("Document deleted: fileId={}", fileId);
    }

    public String getDocumentStatus(Long fileId) {
        KnowledgeFile kf = fileRepository.findById(fileId)
                .orElseThrow(() -> new BusinessException(404, "Document not found"));
        return kf.getStatus();
    }

    private void ensureBucketExists() {
        try {
            boolean exists = minioClient.bucketExists(
                    BucketExistsArgs.builder().bucket(bucketName).build()
            );
            if (!exists) {
                minioClient.makeBucket(
                        MakeBucketArgs.builder().bucket(bucketName).build()
                );
                log.info("MinIO bucket created: {}", bucketName);
            }
        } catch (Exception e) {
            log.error("Failed to ensure MinIO bucket exists: {}", e.getMessage(), e);
            throw new BusinessException("MinIO bucket initialization failed: " + e.getMessage());
        }
    }
}
