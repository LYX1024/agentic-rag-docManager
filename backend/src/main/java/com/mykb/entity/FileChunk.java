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
@TableName("kb_chunk")
public class FileChunk {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("file_id")
    private Long fileId;

    @TableField("chunk_index")
    private Integer chunkIndex;

    @TableField("chunk_text_hash")
    private String chunkTextHash;

    @TableField("vs_doc_id")
    private String vsDocId;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
