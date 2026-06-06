package com.mykb.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.mykb.entity.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapper<User> {
}
