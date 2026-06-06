package com.mykb.service;

import cn.dev33.satoken.stp.StpUtil;
import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.mykb.dto.LoginRequest;
import com.mykb.dto.RegisterRequest;
import com.mykb.entity.User;
import com.mykb.exception.BusinessException;
import com.mykb.mapper.UserMapper;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserService {

    private final UserMapper userMapper;

    @PostConstruct
    public void initAdminUser() {
        User existing = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, "admin"));
        if (existing == null) {
            User admin = new User();
            admin.setUsername("admin");
            admin.setPassword(BCrypt.hashpw("admin123"));
            admin.setEmail("admin@mykb.com");
            userMapper.insert(admin);
            log.info("Default admin user created");
        } else {
            log.info("Admin user already exists");
        }
    }

    public User register(RegisterRequest request) {
        User existing = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, request.username()));
        if (existing != null) {
            throw new BusinessException(400, "Username already exists");
        }
        User user = new User();
        user.setUsername(request.username());
        user.setPassword(BCrypt.hashpw(request.password()));
        user.setEmail(request.email());
        userMapper.insert(user);
        log.info("User registered: {}", user.getUsername());
        return user;
    }

    public String login(LoginRequest request) {
        User user = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, request.username()));
        if (user == null) {
            throw new BusinessException(401, "Invalid username or password");
        }
        if (!BCrypt.checkpw(request.password(), user.getPassword())) {
            throw new BusinessException(401, "Invalid username or password");
        }
        StpUtil.login(user.getId());
        String token = StpUtil.getTokenValue();
        log.info("User logged in: {} (id={})", user.getUsername(), user.getId());
        return token;
    }

    public User getUserById(Long id) {
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new BusinessException(404, "User not found");
        }
        return user;
    }
}
