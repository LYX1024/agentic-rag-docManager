package com.mykb.service;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.mykb.entity.KnowledgeFile;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.DocumentClient;
import com.mykb.mapper.KnowledgeFileMapper;
import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Slf4j
@Service
public class DocumentService {

    private final MinioClient minioClient;
    private final KnowledgeFileMapper fileMapper;
    private final DocumentClient documentClient;
    private final org.springframework.data.redis.core.StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final KBService kbService;

    public DocumentService(MinioClient minioClient, KnowledgeFileMapper fileMapper,
                           DocumentClient documentClient,
                           org.springframework.data.redis.core.StringRedisTemplate redisTemplate,
                           ObjectMapper objectMapper, KBService kbService) {
        this.minioClient = minioClient;
        this.fileMapper = fileMapper;
        this.documentClient = documentClient;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
        this.kbService = kbService;
    }

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
            // Clean up orphaned MinIO file
            try {
                minioClient.removeObject(io.minio.RemoveObjectArgs.builder()
                        .bucket(bucketName).object(minioKey).build());
            } catch (Exception ex) {
                log.warn("Failed to clean up MinIO file after upload failure: key={}", minioKey);
            }
            log.error("Failed to submit ingestion: fileId={}, error={}", kf.getId(), e.getMessage(), e);
        }

        // Evict caches
        evictDocumentListAndCategories(kbId);
        kbService.evictFileCountCache(kbId);

        return kf;
    }

    public IPage<KnowledgeFile> listDocuments(Long kbId, String category, int pageNum, int pageSize) {
        String categoryOrDefault = (category != null && !category.isBlank()) ? category : "all";
        String cacheKey = "doc:list:" + kbId + ":" + categoryOrDefault;

        // Try cache first
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                JsonNode node = objectMapper.readTree(cached);
                List<KnowledgeFile> records = objectMapper.readValue(
                        node.get("records").traverse(),
                        objectMapper.getTypeFactory().constructCollectionType(List.class, KnowledgeFile.class));
                long total = node.get("total").asLong();
                Page<KnowledgeFile> page = new Page<>(pageNum, pageSize, total);
                page.setRecords(records);
                log.info("Cache hit: {}", cacheKey);
                return page;
            }
        } catch (Exception e) {
            log.warn("Cache read failed for listDocuments: {}", e.getMessage());
        }

        // Query MySQL
        Page<KnowledgeFile> page = new Page<>(pageNum, pageSize);
        if (category != null && !category.isBlank()) {
            IPage<KnowledgeFile> result = fileMapper.selectPageByKbIdAndCategory(page, kbId, category);
            cacheDocumentsList(cacheKey, result);
            return result;
        }
        IPage<KnowledgeFile> result = fileMapper.selectPageByKbId(page, kbId);
        cacheDocumentsList(cacheKey, result);
        return result;
    }

    private void cacheDocumentsList(String cacheKey, IPage<KnowledgeFile> result) {
        try {
            Map<String, Object> cacheValue = new HashMap<>();
            cacheValue.put("records", result.getRecords());
            cacheValue.put("total", result.getTotal());
            redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(cacheValue), Duration.ofMinutes(3));
        } catch (Exception e) {
            log.warn("Cache write failed for listDocuments: {}", e.getMessage());
        }
    }

    public List<String> getCategories(Long kbId) {
        String cacheKey = "doc:categories:" + kbId;

        // Try cache first
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                log.info("Cache hit: {}", cacheKey);
                return objectMapper.readValue(cached,
                        objectMapper.getTypeFactory().constructCollectionType(List.class, String.class));
            }
        } catch (Exception e) {
            log.warn("Cache read failed for getCategories: {}", e.getMessage());
        }

        // Query MySQL
        List<String> categories = fileMapper.selectDistinctCategoriesByKbId(kbId);

        // Cache the result
        try {
            redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(categories), Duration.ofMinutes(5));
        } catch (Exception e) {
            log.warn("Cache write failed for getCategories: {}", e.getMessage());
        }

        return categories;
    }

    public void deleteDocument(Long fileId) {
        KnowledgeFile kf = fileMapper.selectById(fileId);
        if (kf == null) {
            throw new BusinessException(404, "Document not found");
        }
        Long kbId = kf.getKbId();

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

        boolean faissCleaned = true;
        try {
            documentClient.deleteDocument(kf.getKbId(), kf.getId(), kf.getFilePathInMinio());
        } catch (Exception e) {
            log.warn("Python FAISS cleanup failed, will retry later: fileId={}, error={}", fileId, e.getMessage());
            faissCleaned = false;
        }

        fileMapper.deleteById(kf.getId());

        // Evict caches
        evictDocumentListAndCategories(kbId);
        try {
            redisTemplate.delete("doc:file:" + fileId);
            redisTemplate.delete("preview:" + fileId);
        } catch (Exception e) {
            log.warn("Cache eviction failed for deleteDocument: {}", e.getMessage());
        }

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

        // Check Redis cache first
        String cacheKey = "preview:" + fileId;
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                log.debug("Preview cache hit: fileId={}", fileId);
                return new ByteArrayInputStream(java.util.Base64.getDecoder().decode(cached));
            }
        } catch (Exception e) {
            log.warn("Redis cache read failed, falling back to MinIO: {}", e.getMessage());
        }

        try {
            byte[] bytes = minioClient.getObject(
                    io.minio.GetObjectArgs.builder()
                            .bucket(bucketName)
                            .object(kf.getFilePathInMinio())
                            .build()).readAllBytes();

            // Cache in Redis for 30 min (files under 5MB)
            if (bytes.length <= 5 * 1024 * 1024) {
                try {
                    redisTemplate.opsForValue().set(cacheKey,
                            java.util.Base64.getEncoder().encodeToString(bytes),
                            Duration.ofMinutes(30));
                } catch (Exception e) {
                    log.warn("Redis cache write failed: {}", e.getMessage());
                }
            }

            return new ByteArrayInputStream(bytes);
        } catch (Exception e) {
            log.error("Failed to read file from MinIO: fileId={}, error={}", fileId, e.getMessage());
            throw new BusinessException("Failed to read file: " + e.getMessage());
        }
    }

    public KnowledgeFile getFile(Long fileId) {
        String cacheKey = "doc:file:" + fileId;

        // Try cache first
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                log.info("Cache hit: {}", cacheKey);
                return objectMapper.readValue(cached, KnowledgeFile.class);
            }
        } catch (Exception e) {
            log.warn("Cache read failed for getFile: {}", e.getMessage());
        }

        // Query MySQL
        KnowledgeFile kf = fileMapper.selectById(fileId);
        if (kf == null) {
            throw new BusinessException(404, "Document not found");
        }

        // Cache the result
        try {
            redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(kf), Duration.ofMinutes(5));
        } catch (Exception e) {
            log.warn("Cache write failed for getFile: {}", e.getMessage());
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

        // Evict caches
        Long kbId = kf.getKbId();
        evictDocumentListAndCategories(kbId);
        try {
            redisTemplate.delete("doc:file:" + kf.getId());
            redisTemplate.delete("preview:" + kf.getId());
        } catch (Exception e) {
            log.warn("Cache eviction failed for syncIngestionStatus: {}", e.getMessage());
        }

        log.info("Ingestion status synced: fileId={}, minioKey={}, status={}, chunks={}",
                kf.getId(), minioKey, status, chunkCount);
    }

    /**
     * Evict document list (all categories) and categories cache for a given KB.
     */
    private void evictDocumentListAndCategories(Long kbId) {
        try {
            Set<String> listKeys = redisTemplate.keys("doc:list:" + kbId + ":*");
            if (listKeys != null && !listKeys.isEmpty()) {
                redisTemplate.delete(listKeys);
            }
            redisTemplate.delete("doc:categories:" + kbId);
        } catch (Exception e) {
            log.warn("Document cache eviction failed: kbId={}, error={}", kbId, e.getMessage());
        }
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
