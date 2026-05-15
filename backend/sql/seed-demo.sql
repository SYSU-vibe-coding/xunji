-- ============================================================
-- Xunji demo/test seed data
-- Run after schema.sql for local backend B data testing.
-- ============================================================

SET NAMES utf8mb4;

INSERT INTO `users` (`id`, `phone`, `nickname`, `role`, `cert_status`, `campus_id`, `real_name`, `credit_score`, `status`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FA1', '13800000010', '演示认领者', 'USER', 'APPROVED', 'S20260001', '张三', 100, 'ACTIVE'),
('01ARZ3NDEKTSV4RRFFQ69G5FA2', '13800000011', '演示拾获者', 'USER', 'APPROVED', 'S20260002', '李四', 100, 'ACTIVE'),
('01ARZ3NDEKTSV4RRFFQ69G5FA3', '13800000012', '低信誉用户', 'USER', 'APPROVED', 'S20260003', '王五', 20, 'ACTIVE'),
('01ARZ3NDEKTSV4RRFFQ69G5FA4', '13800000013', '后台管理员', 'ADMIN', 'APPROVED', 'T20260001', '管理员', 100, 'ACTIVE')
ON DUPLICATE KEY UPDATE `nickname` = VALUES(`nickname`), `role` = VALUES(`role`), `credit_score` = VALUES(`credit_score`), `status` = VALUES(`status`);

INSERT INTO `lost_items` (`id`, `user_id`, `item_name`, `category`, `description`, `lost_time_start`, `lost_time_end`, `lost_location`, `subscribe_match`, `status`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FB1', '01ARZ3NDEKTSV4RRFFQ69G5FA1', '黑色雨伞', 'DAILY_USE', '伞柄有蓝色贴纸', '2026-04-20 10:00:00', '2026-04-20 12:00:00', '图书馆三楼', 1, 'SEARCHING')
ON DUPLICATE KEY UPDATE `status` = VALUES(`status`);

INSERT INTO `found_items` (`id`, `user_id`, `item_name`, `category`, `description`, `found_time`, `found_location`, `is_sensitive`, `custody_type`, `contact_preference`, `status`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FC1', '01ARZ3NDEKTSV4RRFFQ69G5FA2', '黑色雨伞', 'DAILY_USE', '伞柄有蓝色贴纸', '2026-04-20 12:20:00', '图书馆服务台', 0, 'SELF', 'IN_APP', 'PENDING'),
('01ARZ3NDEKTSV4RRFFQ69G5FC2', '01ARZ3NDEKTSV4RRFFQ69G5FA2', '校园卡', 'CERT', '已做脱敏处理', '2026-04-21 09:00:00', '饭堂门口', 1, 'SECURITY', 'IN_APP', 'PENDING')
ON DUPLICATE KEY UPDATE `status` = VALUES(`status`);

INSERT INTO `item_images` (`id`, `biz_type`, `biz_id`, `image_url`, `masked_image_url`, `sort_order`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FD1', 'FOUND', '01ARZ3NDEKTSV4RRFFQ69G5FC1', 'https://example.com/found-umbrella.jpg', NULL, 0),
('01ARZ3NDEKTSV4RRFFQ69G5FD2', 'FOUND', '01ARZ3NDEKTSV4RRFFQ69G5FC2', 'https://example.com/campus-card-raw.jpg', 'https://example.com/campus-card-masked.jpg', 0)
ON DUPLICATE KEY UPDATE `image_url` = VALUES(`image_url`), `masked_image_url` = VALUES(`masked_image_url`);

INSERT INTO `verify_questions` (`id`, `found_item_id`, `question_text`, `answer_keywords`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FE1', '01ARZ3NDEKTSV4RRFFQ69G5FC1', '伞柄有什么特征？', '["蓝色贴纸", "蓝"]')
ON DUPLICATE KEY UPDATE `question_text` = VALUES(`question_text`), `answer_keywords` = VALUES(`answer_keywords`);

INSERT INTO `match_results` (`id`, `lost_item_id`, `found_item_id`, `image_score`, `text_score`, `location_score`, `time_score`, `total_score`, `match_status`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FF1', '01ARZ3NDEKTSV4RRFFQ69G5FB1', '01ARZ3NDEKTSV4RRFFQ69G5FC1', 80.00, 90.00, 90.00, 80.00, 86.00, 'NEW')
ON DUPLICATE KEY UPDATE `total_score` = VALUES(`total_score`), `match_status` = VALUES(`match_status`);

INSERT INTO `reports` (`id`, `reporter_id`, `reported_user_id`, `target_type`, `target_id`, `reason`, `description`, `handle_status`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FG1', '01ARZ3NDEKTSV4RRFFQ69G5FA1', '01ARZ3NDEKTSV4RRFFQ69G5FA3', 'USER', '01ARZ3NDEKTSV4RRFFQ69G5FA3', '冒领风险', '用于后台举报处理演示', 'PENDING')
ON DUPLICATE KEY UPDATE `handle_status` = VALUES(`handle_status`);

INSERT INTO `notifications` (`id`, `user_id`, `notice_type`, `title`, `content`, `is_read`, `related_type`, `related_id`, `priority`) VALUES
('01ARZ3NDEKTSV4RRFFQ69G5FH1', '01ARZ3NDEKTSV4RRFFQ69G5FA1', 'MATCH_RECOMMEND', '发现疑似匹配物品', '黑色雨伞可能已被拾获', 0, 'FOUND', '01ARZ3NDEKTSV4RRFFQ69G5FC1', 'HIGH')
ON DUPLICATE KEY UPDATE `content` = VALUES(`content`), `is_read` = VALUES(`is_read`);
