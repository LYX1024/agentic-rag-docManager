package com.mykb.mapper;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.mykb.entity.KnowledgeFile;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import java.util.List;

@Mapper
public interface KnowledgeFileMapper extends BaseMapper<KnowledgeFile> {
    @Select("SELECT DISTINCT category FROM kb_file WHERE kb_id = #{kbId} AND category != ''")
    List<String> selectDistinctCategoriesByKbId(Long kbId);

    default IPage<KnowledgeFile> selectPageByKbId(IPage<KnowledgeFile> page, Long kbId) {
        return selectPage(page, new LambdaQueryWrapper<KnowledgeFile>()
                .eq(KnowledgeFile::getKbId, kbId)
                .orderByDesc(KnowledgeFile::getCreatedAt));
    }

    default IPage<KnowledgeFile> selectPageByKbIdAndCategory(IPage<KnowledgeFile> page, Long kbId, String category) {
        return selectPage(page, new LambdaQueryWrapper<KnowledgeFile>()
                .eq(KnowledgeFile::getKbId, kbId)
                .eq(KnowledgeFile::getCategory, category)
                .orderByDesc(KnowledgeFile::getCreatedAt));
    }

    default Long countByKbId(Long kbId) {
        return selectCount(new LambdaQueryWrapper<KnowledgeFile>()
                .eq(KnowledgeFile::getKbId, kbId));
    }
}
