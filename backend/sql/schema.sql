-- ============================================================
-- Xunji (寻迹) 校园失物招领平台 - 完整数据库建表脚本
-- 目标数据库: MySQL 8.x  字符集: utf8mb4
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- -----------------------------------------------------------
-- 1. users 用户表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id`           CHAR(26)      NOT NULL COMMENT 'ULID 主键',
  `phone`        VARCHAR(20)   NOT NULL COMMENT '手机号',
  `password_hash` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '密码哈希或占位',
  `nickname`     VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '昵称',
  `avatar_url`   VARCHAR(255)  DEFAULT NULL COMMENT '头像地址',
  `role`         VARCHAR(20)   NOT NULL DEFAULT 'USER' COMMENT 'USER / STAFF / ADMIN',
  `cert_status`  VARCHAR(20)   NOT NULL DEFAULT 'UNVERIFIED' COMMENT 'UNVERIFIED / PENDING / APPROVED / REJECTED',
  `campus_id`    VARCHAR(64)   DEFAULT NULL COMMENT '学号或工号',
  `real_name`    VARCHAR(64)   DEFAULT NULL COMMENT '实名信息',
  `credit_score` INT           NOT NULL DEFAULT 100 COMMENT '信誉分',
  `status`       VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE / DISABLED / CANCELLED',
  `created_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_phone` (`phone`),
  KEY `idx_users_role` (`role`),
  KEY `idx_users_cert_status` (`cert_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- -----------------------------------------------------------
-- 2. user_cert_requests 认证申请表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `user_cert_requests`;
CREATE TABLE `user_cert_requests` (
  `id`                 CHAR(26)     NOT NULL,
  `user_id`            CHAR(26)     NOT NULL,
  `campus_id`          VARCHAR(64)  NOT NULL COMMENT '学号/工号',
  `document_image_url` VARCHAR(255) NOT NULL COMMENT '证件图片 URL',
  `review_status`      VARCHAR(20)  NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING / APPROVED / REJECTED',
  `review_comment`     VARCHAR(255) DEFAULT NULL COMMENT '审批意见',
  `reviewer_id`        CHAR(26)     DEFAULT NULL COMMENT '审核人',
  `reviewed_at`        DATETIME     DEFAULT NULL,
  `created_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_cert_user_id` (`user_id`),
  KEY `idx_cert_status` (`review_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='认证申请表';

-- -----------------------------------------------------------
-- 3. lost_items 失物表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `lost_items`;
CREATE TABLE `lost_items` (
  `id`              CHAR(26)     NOT NULL,
  `user_id`         CHAR(26)     NOT NULL,
  `item_name`       VARCHAR(100) NOT NULL,
  `category`        VARCHAR(30)  NOT NULL COMMENT 'CERT / ELECTRONIC / DAILY_USE / BOOK / OTHER',
  `description`     TEXT         DEFAULT NULL,
  `lost_time_start` DATETIME     NOT NULL,
  `lost_time_end`   DATETIME     NOT NULL,
  `lost_location`   VARCHAR(255) NOT NULL,
  `subscribe_match` TINYINT      NOT NULL DEFAULT 0,
  `status`          VARCHAR(20)  NOT NULL DEFAULT 'SEARCHING' COMMENT 'SEARCHING / FOUND / CLOSED',
  `review_status`   VARCHAR(20)  NOT NULL DEFAULT 'APPROVED' COMMENT 'PENDING / APPROVED / REJECTED',
  `ai_tags`         VARCHAR(255) DEFAULT NULL,
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_lost_items_user_id` (`user_id`),
  KEY `idx_lost_items_category_status` (`category`, `status`),
  KEY `idx_lost_items_review_status` (`review_status`),
  KEY `idx_lost_items_location` (`lost_location`(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='失物表';

-- -----------------------------------------------------------
-- 4. found_items 招领表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `found_items`;
CREATE TABLE `found_items` (
  `id`                 CHAR(26)     NOT NULL,
  `user_id`            CHAR(26)     NOT NULL,
  `item_name`          VARCHAR(100) NOT NULL,
  `category`           VARCHAR(30)  NOT NULL,
  `description`        TEXT         DEFAULT NULL,
  `found_time`         DATETIME     NOT NULL,
  `found_location`     VARCHAR(255) NOT NULL,
  `is_sensitive`       TINYINT      NOT NULL DEFAULT 0,
  `custody_type`       VARCHAR(30)  NOT NULL COMMENT 'SELF / SECURITY / OFFICE',
  `contact_preference` VARCHAR(30)  NOT NULL COMMENT 'IN_APP / PHONE',
  `status`             VARCHAR(20)  NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING / CLAIMING / RETURNED / CLOSED',
  `review_status`      VARCHAR(20)  NOT NULL DEFAULT 'APPROVED' COMMENT 'PENDING / APPROVED / REJECTED',
  `ai_tags`            VARCHAR(255) DEFAULT NULL,
  `created_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_found_items_user_id` (`user_id`),
  KEY `idx_found_items_category_status` (`category`, `status`),
  KEY `idx_found_items_review_status` (`review_status`),
  KEY `idx_found_items_location` (`found_location`(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='招领表';

-- -----------------------------------------------------------
-- 5. item_images 物品图片表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `item_images`;
CREATE TABLE `item_images` (
  `id`               CHAR(26)     NOT NULL,
  `biz_type`         VARCHAR(20)  NOT NULL COMMENT 'LOST / FOUND / CLAIM_PROOF / CERT',
  `biz_id`           CHAR(26)     NOT NULL COMMENT '关联业务 ID',
  `image_url`        VARCHAR(255) NOT NULL,
  `masked_image_url` VARCHAR(255) DEFAULT NULL COMMENT '脱敏图片地址',
  `sort_order`       INT          NOT NULL DEFAULT 0,
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_item_images_biz` (`biz_type`, `biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='物品图片表';

-- -----------------------------------------------------------
-- 6. verify_questions 验证问题表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `verify_questions`;
CREATE TABLE `verify_questions` (
  `id`              CHAR(26)     NOT NULL,
  `found_item_id`   CHAR(26)     NOT NULL,
  `question_text`   VARCHAR(255) NOT NULL,
  `answer_keywords` VARCHAR(255) NOT NULL COMMENT '关键词，JSON 数组',
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_verify_found_item` (`found_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验证问题表';

-- -----------------------------------------------------------
-- 7. match_results 匹配结果表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `match_results`;
CREATE TABLE `match_results` (
  `id`             CHAR(26)      NOT NULL,
  `lost_item_id`   CHAR(26)      NOT NULL,
  `found_item_id`  CHAR(26)      NOT NULL,
  `image_score`    DECIMAL(5,2)  DEFAULT 0.00,
  `text_score`     DECIMAL(5,2)  DEFAULT 0.00,
  `location_score` DECIMAL(5,2)  DEFAULT 0.00,
  `time_score`     DECIMAL(5,2)  DEFAULT 0.00,
  `total_score`    DECIMAL(5,2)  DEFAULT 0.00 COMMENT '0.4*img + 0.3*txt + 0.2*loc + 0.1*time',
  `match_status`   VARCHAR(20)   NOT NULL DEFAULT 'NEW' COMMENT 'NEW / READ / CLAIMED / EXPIRED',
  `created_at`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_match_lost_item` (`lost_item_id`),
  KEY `idx_match_found_item` (`found_item_id`),
  KEY `idx_match_total_score` (`total_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='匹配结果表';

-- -----------------------------------------------------------
-- 8. claim_requests 认领请求表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `claim_requests`;
CREATE TABLE `claim_requests` (
  `id`            CHAR(26)     NOT NULL,
  `match_id`      CHAR(26)     DEFAULT NULL,
  `found_item_id` CHAR(26)     NOT NULL,
  `claimant_id`   CHAR(26)     NOT NULL,
  `verify_level`  VARCHAR(20)  NOT NULL COMMENT 'LEVEL_1 / LEVEL_2 / LEVEL_3 / FAST_TRACK',
  `review_status` VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
  `reject_reason` VARCHAR(255) DEFAULT NULL,
  `proof_text`    VARCHAR(500) DEFAULT NULL COMMENT '认领者补充凭证说明',
  `appeal_reason` VARCHAR(500) DEFAULT NULL COMMENT '申诉理由',
  `claimed_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_claim_match` (`match_id`),
  KEY `idx_claim_found_item` (`found_item_id`),
  KEY `idx_claim_claimant` (`claimant_id`),
  KEY `idx_claim_status` (`review_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='认领请求表';

-- -----------------------------------------------------------
-- 9. claim_answers 认领回答表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `claim_answers`;
CREATE TABLE `claim_answers` (
  `id`            CHAR(26)      NOT NULL,
  `claim_id`      CHAR(26)      NOT NULL,
  `question_id`   CHAR(26)      NOT NULL,
  `question_text` VARCHAR(255)  NOT NULL,
  `answer_text`   VARCHAR(255)  NOT NULL,
  `match_score`   DECIMAL(5,2)  DEFAULT 0.00,
  `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_answer_claim` (`claim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='认领回答表';

-- -----------------------------------------------------------
-- 10. handover_records 交接记录表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `handover_records`;
CREATE TABLE `handover_records` (
  `id`                CHAR(26)     NOT NULL,
  `claim_id`          CHAR(26)     NOT NULL,
  `method`            VARCHAR(20)  NOT NULL COMMENT 'MEETUP / PICKUP_POINT',
  `handover_location` VARCHAR(255) DEFAULT NULL,
  `handover_time`     DATETIME     DEFAULT NULL,
  `owner_confirmed`   TINYINT      NOT NULL DEFAULT 0,
  `finder_confirmed`  TINYINT      NOT NULL DEFAULT 0,
  `completed_at`      DATETIME     DEFAULT NULL,
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_handover_claim` (`claim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交接记录表';

-- -----------------------------------------------------------
-- 11. credit_logs 积分流水表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `credit_logs`;
CREATE TABLE `credit_logs` (
  `id`          CHAR(26)     NOT NULL,
  `user_id`     CHAR(26)     NOT NULL,
  `delta_score` INT          NOT NULL COMMENT '变动分值(正/负)',
  `reason_code` VARCHAR(50)  NOT NULL,
  `reason_text` VARCHAR(255) DEFAULT NULL,
  `biz_type`    VARCHAR(30)  NOT NULL,
  `biz_id`      CHAR(26)     NOT NULL,
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_credit_user` (`user_id`),
  UNIQUE KEY `uk_credit_dedup` (`user_id`, `biz_type`, `biz_id`, `reason_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分流水表';

-- -----------------------------------------------------------
-- 12. notifications 通知表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
  `id`           CHAR(26)     NOT NULL,
  `user_id`      CHAR(26)     NOT NULL,
  `notice_type`  VARCHAR(30)  NOT NULL,
  `title`        VARCHAR(100) NOT NULL,
  `content`      VARCHAR(500) DEFAULT NULL,
  `is_read`      TINYINT      NOT NULL DEFAULT 0,
  `related_type` VARCHAR(30)  DEFAULT NULL,
  `related_id`   CHAR(26)     DEFAULT NULL,
  `priority`     VARCHAR(20)  NOT NULL DEFAULT 'NORMAL' COMMENT 'NORMAL / HIGH',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_notif_user_read` (`user_id`, `is_read`),
  KEY `idx_notif_type` (`notice_type`),
  KEY `idx_notif_related` (`related_type`, `related_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知表';

-- -----------------------------------------------------------
-- 13. reports 举报表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `reports`;
CREATE TABLE `reports` (
  `id`               CHAR(26)     NOT NULL,
  `reporter_id`      CHAR(26)     NOT NULL,
  `reported_user_id` CHAR(26)     DEFAULT NULL,
  `target_type`      VARCHAR(30)  NOT NULL COMMENT 'LOST_ITEM / FOUND_ITEM / CLAIM_REQUEST / USER',
  `target_id`        CHAR(26)     NOT NULL,
  `reason`           VARCHAR(100) NOT NULL,
  `description`      VARCHAR(500) DEFAULT NULL,
  `handle_status`    VARCHAR(20)  NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING / PROCESSING / CLOSED / REJECTED',
  `handle_result`    VARCHAR(255) DEFAULT NULL,
  `handler_id`       CHAR(26)     DEFAULT NULL,
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_report_reporter` (`reporter_id`),
  KEY `idx_report_status` (`handle_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='举报表';

-- -----------------------------------------------------------
-- 14. announcements 公告表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `announcements`;
CREATE TABLE `announcements` (
  `id`           CHAR(26)     NOT NULL,
  `title`        VARCHAR(100) NOT NULL,
  `content`      TEXT         DEFAULT NULL,
  `status`       VARCHAR(20)  NOT NULL DEFAULT 'DRAFT' COMMENT 'DRAFT / PUBLISHED / OFFLINE',
  `published_by` CHAR(26)     DEFAULT NULL,
  `published_at` DATETIME     DEFAULT NULL,
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_announce_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公告表';

-- -----------------------------------------------------------
-- 15. operation_logs 操作日志表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `operation_logs`;
CREATE TABLE `operation_logs` (
  `id`            CHAR(26)     NOT NULL,
  `operator_id`   CHAR(26)     NOT NULL,
  `operator_role` VARCHAR(20)  NOT NULL,
  `biz_type`      VARCHAR(30)  NOT NULL,
  `biz_id`        CHAR(26)     NOT NULL,
  `action`        VARCHAR(50)  NOT NULL,
  `detail`        VARCHAR(500) DEFAULT NULL,
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_oplog_operator` (`operator_id`),
  KEY `idx_oplog_biz` (`biz_type`, `biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

SET FOREIGN_KEY_CHECKS = 1;
