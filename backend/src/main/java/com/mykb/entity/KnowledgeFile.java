package com.mykb.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("kb_file")
public class KnowledgeFile {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("kb_id")
    private Long kbId;

    private String category;

    @TableField("file_name")
    private String fileName;

    @TableField("file_ext")
    private String fileExt;

    @TableField("file_size")
    private Long fileSize;

    @TableField("file_path_in_minio")
    private String filePathInMinio;

    @TableField("file_version")
    private Integer fileVersion = 1;

    private String status = "UPLOADED";

    @TableField("error_msg")
    private String errorMsg;

    @TableField("chunk_count")
    private Integer chunkCount = 0;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
