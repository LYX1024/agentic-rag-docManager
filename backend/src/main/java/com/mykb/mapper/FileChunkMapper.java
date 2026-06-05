package com.mykb.mapper;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.mykb.entity.FileChunk;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface FileChunkMapper extends BaseMapper<FileChunk> {
    default List<FileChunk> selectByFileId(Long fileId) {
        return selectList(new LambdaQueryWrapper<FileChunk>()
                .eq(FileChunk::getFileId, fileId));
    }

    default void deleteByFileId(Long fileId) {
        delete(new LambdaQueryWrapper<FileChunk>()
                .eq(FileChunk::getFileId, fileId));
    }
}
