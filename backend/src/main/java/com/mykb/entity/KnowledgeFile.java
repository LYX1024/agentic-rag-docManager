package com.mykb.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "kb_file", indexes = {
    @Index(name = "idx_kb_file_kb_id", columnList = "kb_id"),
    @Index(name = "idx_kb_file_status", columnList = "status"),
    @Index(name = "idx_kb_file_category", columnList = "kb_id, category")
})
public class KnowledgeFile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "kb_id", nullable = false)
    private Long kbId;

    @Column(length = 100)
    private String category = "";

    @Column(name = "file_name", nullable = false, length = 255)
    private String fileName;

    @Column(name = "file_ext", length = 20)
    private String fileExt;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "file_path_in_minio", length = 500)
    private String filePathInMinio;

    @Column(name = "file_version")
    private Integer fileVersion = 1;

    @Column(length = 20)
    private String status = "UPLOADED";

    @Column(name = "error_msg", columnDefinition = "TEXT")
    private String errorMsg;

    @Column(name = "chunk_count")
    private Integer chunkCount = 0;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
