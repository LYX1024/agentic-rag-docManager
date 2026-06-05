-- Application user with least privileges (preferred over root for backend connection)
CREATE USER IF NOT EXISTS 'mykb_app'@'%' IDENTIFIED BY 'mykb_app_pass';
GRANT SELECT, INSERT, UPDATE, DELETE ON mykb.* TO 'mykb_app'@'%';
FLUSH PRIVILEGES;

-- ==================== User Table ====================
CREATE TABLE IF NOT EXISTS `user` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password` VARCHAR(128) NOT NULL,
    `email` VARCHAR(100),
    `avatar` VARCHAR(255),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Knowledge Base Table ====================
CREATE TABLE IF NOT EXISTS `kb_info` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `vs_type` VARCHAR(20) NOT NULL DEFAULT 'FAISS',
    `embed_model` VARCHAR(50) NOT NULL DEFAULT 'bge-m3',
    `user_id` BIGINT NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Knowledge File Table ====================
CREATE TABLE IF NOT EXISTS `kb_file` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `kb_id` BIGINT NOT NULL,
    `category` VARCHAR(100) DEFAULT '',
    `file_name` VARCHAR(255) NOT NULL,
    `file_ext` VARCHAR(20),
    `file_size` BIGINT,
    `file_path_in_minio` VARCHAR(500),
    `file_version` INT DEFAULT 1,
    `status` VARCHAR(20) DEFAULT 'UPLOADED',
    `error_msg` TEXT,
    `chunk_count` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`kb_id`) REFERENCES `kb_info`(`id`) ON DELETE CASCADE,
    INDEX `idx_kb_file_kb_id` (`kb_id`),
    INDEX `idx_kb_file_status` (`status`),
    INDEX `idx_kb_file_category` (`kb_id`, `category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== File Chunk Table ====================
CREATE TABLE IF NOT EXISTS `kb_chunk` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `file_id` BIGINT NOT NULL,
    `chunk_index` INT NOT NULL,
    `chunk_text_hash` VARCHAR(64) NOT NULL,
    `vs_doc_id` VARCHAR(255),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`file_id`) REFERENCES `kb_file`(`id`) ON DELETE CASCADE,
    INDEX `idx_kb_chunk_file_id` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Chat Session Table ====================
CREATE TABLE IF NOT EXISTS `chat_session` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `user_id` BIGINT NOT NULL,
    `kb_id` BIGINT,
    `title` VARCHAR(200),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`),
    FOREIGN KEY (`kb_id`) REFERENCES `kb_info`(`id`),
    INDEX `idx_chat_session_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Chat Message Table ====================
CREATE TABLE IF NOT EXISTS `chat_message` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `session_id` BIGINT NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    `content` TEXT NOT NULL,
    `sources` JSON,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`session_id`) REFERENCES `chat_session`(`id`) ON DELETE CASCADE,
    INDEX `idx_chat_message_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
