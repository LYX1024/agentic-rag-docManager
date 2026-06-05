package com.mykb.service;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mykb.entity.KnowledgeFile;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.DocumentClient;
import com.mykb.mapper.FileChunkMapper;
import com.mykb.mapper.KnowledgeFileMapper;
import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final MinioClient minioClient;
    private final KnowledgeFileMapper fileMapper;
    private final FileChunkMapper chunkMapper;
    private final DocumentClient documentClient;

    @Value("${minio.bucket}")
    private String bucketName;

    public KnowledgeFile uploadFile(Long kbId, MultipartFile file, String category) {
        String originalFilename = file.getOriginalFilename();
        String fileExt = "";
        if (originalFilename != null && originalFilename.contains(".")) {
            fileExt = originalFilename.substring(originalFilename.lastIndexOf("."));
        }
        String safeCategory = (category != null && !category.trim().isEmpty()) ? category.trim() : "default";
        String uuid = IdUtil.fastSimpleUUID();
        String minioKey = safeCategory.isEmpty()
                ? kbId + "/" + uuid + "/" + originalFilename
                : kbId + "/" + safeCategory + "/" + uuid + "/" + originalFilename;

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
        kf.setCategory(safeCategory);
        kf.setFileName(originalFilename);
        kf.setFileExt(fileExt);
        kf.setFileSize(file.getSize());
        kf.setFilePathInMinio(minioKey);
        kf.setStatus("UPLOADED");
        fileMapper.insert(kf);
        log.info("KnowledgeFile saved: fileId={}, kbId={}, filename={}", kf.getId(), kbId, originalFilename);

        try {
            documentClient.uploadDocument(kbId, originalFilename, fileExt, file.getSize(), minioKey);
            kf.setStatus("PARSING");
            fileMapper.updateById(kf);
            log.info("Async ingestion submitted: fileId={}", kf.getId());
        } catch (Exception e) {
            kf.setStatus("FAILED");
            kf.setErrorMsg(e.getMessage());
            fileMapper.updateById(kf);
            log.error("Failed to submit ingestion: fileId={}, error={}", kf.getId(), e.getMessage(), e);
        }

        return kf;
    }

    public IPage<KnowledgeFile> listDocuments(Long kbId, String category, int pageNum, int pageSize) {
        Page<KnowledgeFile> page = new Page<>(pageNum, pageSize);
        if (category != null && !category.isBlank()) {
            return fileMapper.selectPageByKbIdAndCategory(page, kbId, category);
        }
        return fileMapper.selectPageByKbId(page, kbId);
    }

    public List<String> getCategories(Long kbId) {
        return fileMapper.selectDistinctCategoriesByKbId(kbId);
    }

    public void deleteDocument(Long fileId) {
        KnowledgeFile kf = fileMapper.selectById(fileId);
        if (kf == null) {
            throw new BusinessException(404, "Document not found");
        }

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

        chunkMapper.deleteByFileId(fileId);
        log.info("Chunks deleted for fileId={}", fileId);

        try {
            documentClient.deleteDocument(kf.getKbId(), kf.getId(), kf.getFilePathInMinio());
        } catch (Exception e) {
            log.warn("Python document deletion failed (non-fatal): fileId={}, error={}", fileId, e.getMessage());
        }

        fileMapper.deleteById(kf.getId());
        log.info("Document deleted: fileId={}", fileId);
    }

    public String getDocumentStatus(Long fileId) {
        KnowledgeFile kf = fileMapper.selectById(fileId);
        if (kf == null) {
            throw new BusinessException(404, "Document not found");
        }
        return kf.getStatus();
    }

    public InputStream getFileContent(Long fileId) {
        KnowledgeFile kf = fileMapper.selectById(fileId);
        if (kf == null) {
            throw new BusinessException(404, "Document not found");
        }
        try {
            return minioClient.getObject(
                    io.minio.GetObjectArgs.builder()
                            .bucket(bucketName)
                            .object(kf.getFilePathInMinio())
                            .build());
        } catch (Exception e) {
            log.error("Failed to read file from MinIO: fileId={}, error={}", fileId, e.getMessage());
            throw new BusinessException("Failed to read file: " + e.getMessage());
        }
    }

    public KnowledgeFile getFile(Long fileId) {
        KnowledgeFile kf = fileMapper.selectById(fileId);
        if (kf == null) {
            throw new BusinessException(404, "Document not found");
        }
        return kf;
    }

    public void syncIngestionStatus(String minioKey, String status, int chunkCount, String errorMsg) {
        KnowledgeFile kf = fileMapper.selectOne(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<KnowledgeFile>()
                        .eq(KnowledgeFile::getFilePathInMinio, minioKey));
        if (kf == null) {
            log.warn("Ingestion callback for unknown file: minioKey={}", minioKey);
            return;
        }
        kf.setStatus(status);
        kf.setChunkCount(chunkCount);
        if (errorMsg != null && !errorMsg.isEmpty()) {
            kf.setErrorMsg(errorMsg);
        }
        fileMapper.updateById(kf);
        log.info("Ingestion status synced: fileId={}, minioKey={}, status={}, chunks={}",
                kf.getId(), minioKey, status, chunkCount);
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
