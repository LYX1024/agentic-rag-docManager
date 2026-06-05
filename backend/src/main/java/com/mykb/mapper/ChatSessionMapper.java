package com.mykb.mapper;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.mykb.entity.ChatSession;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface ChatSessionMapper extends BaseMapper<ChatSession> {
    default List<ChatSession> selectByUserId(Long userId) {
        return selectList(new LambdaQueryWrapper<ChatSession>()
                .eq(ChatSession::getUserId, userId)
                .orderByDesc(ChatSession::getUpdatedAt));
    }

    default List<ChatSession> selectByUserIdAndKbId(Long userId, Long kbId) {
        return selectList(new LambdaQueryWrapper<ChatSession>()
                .eq(ChatSession::getUserId, userId)
                .eq(ChatSession::getKbId, kbId)
                .orderByDesc(ChatSession::getUpdatedAt));
    }
}
