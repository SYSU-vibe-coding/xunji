# 数据库设计

> 所有枚举字段（`status`、`category`、`role` 等）取值见 `enums.md`，本文只标类型不再列枚举值。
>
> **实现约定**：Python 侧用 SQLAlchemy 2.x 声明式 ORM 映射各表，`models.py` 放 ORM，`schemas.py` 放 pydantic DTO，两者严格分离。表结构变更走 Alembic 迁移（`backend/alembic/versions/`），不手写 SQL 脚本。所有 `id` 字段类型为 `CHAR(26)`（ULID 字符串），在 service 层生成后插入。

## 1. 设计原则

- 先满足核心业务闭环，再预留扩展字段
- 核心业务实体单独建表，不做过度范式化
- 图片、凭证等大文件只存 URL，不直接存二进制
- 状态字段采用明确枚举值，不使用模糊文本
- 所有核心表保留 `created_at`、`updated_at` 字段

## 2. 核心实体关系

主要关系如下：

- 一个用户可以发布多条失物信息
- 一个用户可以发布多条招领信息
- 一条招领信息可包含 0 到 3 个验证问题
- 一条失物和一条招领之间可产生多条匹配记录
- 一次认领请求通常来源于一条匹配记录
- 一次认领请求最多生成一条交接记录
- 一个用户会产生多条消息、多条积分流水、多条举报记录

## 3. 表结构设计

### 3.1 `users` 用户表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| phone | varchar(20) | 手机号，唯一 |
| password_hash | varchar(255) | 密码哈希或占位值 |
| nickname | varchar(64) | 昵称 |
| avatar_url | varchar(255) | 头像地址 |
| role | varchar(20) | 见 `enums.md` UserRole |
| cert_status | varchar(20) | 见 `enums.md` CertStatus |
| campus_id | varchar(64) | 学号或工号 |
| real_name | varchar(64) | 实名信息，可选 |
| credit_score | int | 信誉分 |
| status | varchar(20) | 见 `enums.md` UserStatus |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

索引建议：

- `uk_users_phone(phone)`
- `idx_users_role(role)`
- `idx_users_cert_status(cert_status)`

### 3.2 `user_cert_requests` 认证申请表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| user_id | char(26) | 申请用户 |
| campus_id | varchar(64) | 学号/工号 |
| document_image_url | varchar(255) | 证件图片 |
| review_status | varchar(20) | 见 `enums.md` ReviewStatus |
| review_comment | varchar(255) | 审批意见 |
| reviewer_id | char(26) | 审核人 |
| reviewed_at | datetime | 审核时间 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 3.3 `lost_items` 失物表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| user_id | char(26) | 发布者 |
| item_name | varchar(100) | 物品名称 |
| category | varchar(30) | 分类 |
| description | text | 描述 |
| lost_time_start | datetime | 丢失开始时间 |
| lost_time_end | datetime | 丢失结束时间 |
| lost_location | varchar(255) | 丢失地点 |
| subscribe_match | tinyint | 是否订阅匹配 |
| status | varchar(20) | 见 `enums.md` LostItemStatus |
| ai_tags | varchar(255) | AI 生成标签，逗号分隔或 JSON |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

索引建议：

- `idx_lost_items_user_id(user_id)`
- `idx_lost_items_category_status(category, status)`
- `idx_lost_items_location(lost_location)`

### 3.4 `found_items` 招领表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| user_id | char(26) | 发布者 |
| item_name | varchar(100) | 物品名称 |
| category | varchar(30) | 分类 |
| description | text | 描述 |
| found_time | datetime | 拾获时间 |
| found_location | varchar(255) | 拾获地点 |
| is_sensitive | tinyint | 是否敏感物品 |
| custody_type | varchar(30) | 见 `enums.md` CustodyType |
| contact_preference | varchar(30) | 见 `enums.md` ContactPreference |
| status | varchar(20) | 见 `enums.md` FoundItemStatus |
| ai_tags | varchar(255) | AI 标签 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 3.5 `item_images` 物品图片表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| biz_type | varchar(20) | 见 `enums.md` BizType |
| biz_id | char(26) | 业务主键 |
| image_url | varchar(255) | 图片地址 |
| masked_image_url | varchar(255) | 脱敏后图片地址 |
| sort_order | int | 排序 |
| created_at | datetime | 创建时间 |

### 3.6 `verify_questions` 验证问题表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| found_item_id | char(26) | 对应招领物品 |
| question_text | varchar(255) | 问题内容 |
| answer_keywords | varchar(255) | 关键词答案 |
| created_at | datetime | 创建时间 |

### 3.7 `match_results` 匹配结果表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| lost_item_id | char(26) | 失物 ID |
| found_item_id | char(26) | 招领 ID |
| image_score | decimal(5,2) | 图像相似度 |
| text_score | decimal(5,2) | 文本相似度 |
| location_score | decimal(5,2) | 地点匹配度 |
| time_score | decimal(5,2) | 时间匹配度 |
| total_score | decimal(5,2) | 综合评分 |
| match_status | varchar(20) | 见 `enums.md` MatchStatus |
| created_at | datetime | 创建时间 |

索引建议：

- `idx_match_lost_item(lost_item_id)`
- `idx_match_found_item(found_item_id)`
- `idx_match_total_score(total_score)`

### 3.8 `claim_requests` 认领请求表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| match_id | char(26) | 来源匹配记录，可空 |
| found_item_id | char(26) | 招领物品 |
| claimant_id | char(26) | 认领人 |
| verify_level | varchar(20) | 见 `enums.md` VerifyLevel |
| review_status | varchar(20) | 见 `enums.md` ClaimReviewStatus |
| reject_reason | varchar(255) | 拒绝原因 |
| proof_text | varchar(500) | 认领者补充凭证说明 |
| appeal_reason | varchar(500) | 申诉理由 |
| claimed_at | datetime | 发起时间 |
| updated_at | datetime | 更新时间 |

### 3.9 `claim_answers` 认领回答表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| claim_id | char(26) | 认领请求 |
| question_id | char(26) | 验证问题 |
| question_text | varchar(255) | 验证问题文本快照 |
| answer_text | varchar(255) | 用户回答 |
| match_score | decimal(5,2) | 回答匹配度 |
| created_at | datetime | 创建时间 |

### 3.10 `handover_records` 交接记录表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| claim_id | char(26) | 认领请求 |
| method | varchar(20) | 见 `enums.md` HandoverMethod |
| handover_location | varchar(255) | 交接地点 |
| handover_time | datetime | 交接时间 |
| owner_confirmed | tinyint | 失主是否确认 |
| finder_confirmed | tinyint | 拾获者是否确认 |
| completed_at | datetime | 完成时间 |
| created_at | datetime | 创建时间 |

### 3.11 `credit_logs` 积分流水表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| user_id | char(26) | 用户 |
| delta_score | int | 变动分值 |
| reason_code | varchar(50) | 见 `credit-rules.md` |
| reason_text | varchar(255) | 原因描述 |
| biz_type | varchar(30) | 关联业务类型 |
| biz_id | char(26) | 关联业务 ID |
| created_at | datetime | 创建时间 |

### 3.12 `notifications` 通知表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| user_id | char(26) | 接收用户 |
| notice_type | varchar(30) | 见 `enums.md` NoticeType |
| title | varchar(100) | 标题 |
| content | varchar(500) | 内容 |
| is_read | tinyint | 是否已读 |
| related_type | varchar(30) | 关联业务类型 |
| related_id | char(26) | 关联业务 ID |
| priority | varchar(20) | 见 `enums.md` NotificationPriority |
| created_at | datetime | 创建时间 |

### 3.13 `reports` 举报表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| reporter_id | char(26) | 举报人 |
| reported_user_id | char(26) | 被举报人 |
| target_type | varchar(30) | 见 `enums.md` ReportTargetType |
| target_id | char(26) | 目标记录 |
| reason | varchar(100) | 举报原因 |
| description | varchar(500) | 详细说明 |
| handle_status | varchar(20) | 见 `enums.md` ReportHandleStatus |
| handle_result | varchar(255) | 处理结果 |
| handler_id | char(26) | 处理人 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 3.14 `announcements` 公告表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| title | varchar(100) | 公告标题 |
| content | text | 公告内容 |
| status | varchar(20) | 见 `enums.md` AnnouncementStatus |
| published_by | char(26) | 发布人 |
| published_at | datetime | 发布时间 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 3.15 `operation_logs` 操作日志表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | char(26) | 主键 |
| operator_id | char(26) | 操作人 |
| operator_role | varchar(20) | 操作角色 |
| biz_type | varchar(30) | 业务类型 |
| biz_id | char(26) | 业务主键 |
| action | varchar(50) | 见 `enums.md` OperationAction |
| detail | varchar(500) | 操作说明 |
| created_at | datetime | 创建时间 |

## 4. 数据一致性要求

- 交接完成时，用 `async with session.begin():` 在一个事务内更新：认领状态、失物状态、招领状态、积分流水
- 管理员审核操作必须同时记录日志和审批结果
- 删除类操作优先采用逻辑删除或状态关闭，不直接物理删除核心业务数据

## 5. 数据安全要求

- 证件类图片原图只允许管理员和受控服务访问
- 敏感字段展示时由后端统一脱敏
- 关键表的状态变更记录操作日志
