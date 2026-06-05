package com.mykb.service;

import cn.dev33.satoken.stp.StpUtil;
import cn.hutool.crypto.digest.BCrypt;
import com.mykb.dto.LoginRequest;
import com.mykb.dto.RegisterRequest;
import com.mykb.entity.User;
import com.mykb.exception.BusinessException;
import com.mykb.repository.UserRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    @PostConstruct
    public void initAdminUser() {
        Optional<User> existing = userRepository.findByUsername("admin");
        if (existing.isEmpty()) {
            User admin = new User();
            admin.setUsername("admin");
            admin.setPassword(BCrypt.hashpw("admin123"));
            admin.setEmail("admin@mykb.com");
            userRepository.save(admin);
            log.info("Admin user created (admin / admin123)");
        } else {
            log.info("Admin user already exists");
        }
    }

    public User register(RegisterRequest request) {
        Optional<User> existing = userRepository.findByUsername(request.username());
        if (existing.isPresent()) {
            throw new BusinessException(400, "Username already exists");
        }
        User user = new User();
        user.setUsername(request.username());
        user.setPassword(BCrypt.hashpw(request.password()));
        user.setEmail(request.email());
        userRepository.save(user);
        log.info("User registered: {}", user.getUsername());
        return user;
    }

    public String login(LoginRequest request) {
        User user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new BusinessException(401, "Invalid username or password"));
        if (!BCrypt.checkpw(request.password(), user.getPassword())) {
            throw new BusinessException(401, "Invalid username or password");
        }
        StpUtil.login(user.getId());
        String token = StpUtil.getTokenValue();
        log.info("User logged in: {} (id={})", user.getUsername(), user.getId());
        return token;
    }

    public User getUserById(Long id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new BusinessException(404, "User not found"));
    }
}
