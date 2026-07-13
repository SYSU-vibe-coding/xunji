# 管理后台接口

所有接口要求 `role = ADMIN`，未满足返回 `48002`。

## GET /api/v1/admin/certifications

查询参数：`reviewStatus` (ReviewStatus) / `pageNo` / `pageSize`

返回 list 元素：`{id, userId, nickname, campusId, realName, documentImageUrl, reviewStatus, reviewComment, createdAt}`

`documentImageUrl` 是按管理员权限动态签发的敏感短时 URL，不是数据库持久值；对象不可用时为 `null`。

## POST /api/v1/admin/certifications/{id}/review

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| action | enum | 是 | `APPROVE` / `REJECT` |
| comment | string | 条件 | `REJECT` 必填，≤ 200 |

效果：
- APPROVE：`cert_status = APPROVED` + 加 20 分（`CERT_APPROVED`） + 通知
- REJECT：`cert_status = REJECTED` + 通知
- 写 `operation_logs`（action `CERT_APPROVE/CERT_REJECT`）
- 仅 `PENDING` 可审核；审核对象使用行锁和条件更新，重复或并发审核返回 `48001`
- `comment` 原样保存到 `reviewComment`，并写入通知和审计日志；同一认证不会重复加分

## GET /api/v1/admin/items/review

查询参数：`bizType` (`LOST`/`FOUND`) / `targetId`（精确 ID）/ `pageNo` / `pageSize`

不传 `bizType` 时，失物和招领先按 `createdAt DESC, id DESC` 统一排序，再执行全局分页，不会分别截断后拼接。返回项包含持久化的 `reviewComment`。

## POST /api/v1/admin/items/{bizType}/{id}/review

路径：`bizType` = `lost` / `found`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| action | enum | 是 | `APPROVE` / `REJECT` |
| comment | string | 条件 | `REJECT` 必填 |

REJECT 效果：对应物品 `status = CLOSED`，通知发布者。

仅 `reviewStatus = PENDING` 可审核；重复或并发审核返回 `48001`。`comment` 原样保存，并进入通知和结构化审计日志。

## GET /api/v1/admin/items/{bizType}/{id}

返回单条审核详情，不依赖列表分页定位。响应包含物品描述、事件时间/地点、业务与审核状态、`reviewComment`、发布者摘要、管理员权限下动态签发的图片 URL；招领信息还包含不泄露答案关键字的 `verifyQuestions`。`bizType` 不区分大小写，仅支持 `LOST/FOUND`。

## GET /api/v1/admin/reports

查询参数：`handleStatus` (ReportHandleStatus) / `targetType` / `pageNo` / `pageSize`

返回 list 元素：`{id, reporterId, reportedUserId, targetType, targetId, reason, description, handleStatus, createdAt}`

## POST /api/v1/admin/reports/{id}/handle

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| action | enum | 是 | `VALID` / `INVALID` |
| result | string | 条件 | `VALID` 必填，≤ 200 |
| creditDelta | int | 否 | 兼容字段；若传入必须与后端强制规则完全一致 |
| reasonCode | CreditReasonCode | 否 | 兼容字段；若传入必须与后端强制规则完全一致 |

效果：
- `VALID`：置 `CLOSED`；`LOST_ITEM/FOUND_ITEM` 强制 `FAKE_PUBLISH_CONFIRMED/-20`，`CLAIM_REQUEST` 强制 `FRAUD_CLAIM_CONFIRMED/-30`
- `VALID` 物品举报会下架目标、失效匹配并终止关联活动认领；认领举报会终止目标认领
- `INVALID`：置 `REJECTED`
- 两种结果均要求精确目标仍存在；不存在返回 `47001`
- 仅 `PENDING/PROCESSING` 可处理，重复或并发处理返回 `48001`
- 通知举报人和被举报人，完整处理规则、结果和联动数量写入结构化审计日志
- `INVALID` 不扣分、不下架；正分或不匹配的处罚参数返回 `40001`

## GET /api/v1/admin/claims

管理员认领治理队列。查询参数：`reviewStatus`（可选，不传返回全部状态）/ `pageNo` / `pageSize`。

返回项包含 `appealReason`、`rejectReason`、`claimant`、`finder`、完整招领上下文、认领时间、问答校验来源和认领状态。管理员复用 `POST /api/v1/claims/{id}/review` 裁决申诉；仅 `APPEALING` 可由管理员裁决，`APPROVE/REJECT` 使用既有认领 CAS 状态迁移，状态已变化时返回 `44003`。

## GET /api/v1/admin/claims/{id}

返回管理员认领详情，包括申诉理由、原拒绝理由、双方用户、招领时间地点与描述、问答/凭证/交接数据。`answers[]` 在普通认领详情的基础上增加仅管理员可见的 `referenceAnswers[]`，该字段为认领提交时保存的参考答案快照；同时返回 `verificationSource`（`ClaimVerificationSource`）与 `verificationDegraded`，用于区分小模型语义校验、关键词规则降级和无需问答的记录，枚举值见 `../architecture/enums.md`。

## POST /api/v1/admin/announcements

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| title | string | 是 | 1-100 |
| content | string | 是 | 1-5000 |
| publishNow | bool | 否 | 默认 true；false 则 `status = DRAFT` |

`publishNow = true` 时，在公告创建事务内按批次为所有 `ACTIVE` 用户生成 `SYSTEM_ANNOUNCEMENT` 通知。

## GET /api/v1/admin/announcements

查询参数：`status`（`DRAFT/PUBLISHED/OFFLINE`）/ `pageNo` / `pageSize`。返回公告内容、状态、创建/更新时间和发布人/发布时间，管理端可见全部生命周期状态。

## POST /api/v1/admin/announcements/{id}/publish

将 `DRAFT` 条件更新为 `PUBLISHED`，记录发布人和发布时间，并在同一事务中按批次为所有 `ACTIVE` 用户生成 `SYSTEM_ANNOUNCEMENT` 通知，通知的 `relatedType = ANNOUNCEMENT`、`relatedId = 公告 ID`。重复调用已发布公告幂等成功，不会重复生成通知；`OFFLINE` 不可重新发布。

## POST /api/v1/admin/announcements/{id}/offline

将 `PUBLISHED` 条件更新为 `OFFLINE`。重复下线幂等成功；草稿不可下线。下线后公开列表、公开详情和既有通知深链均无法读取该公告。

## GET /api/v1/admin/dashboard

返回：
| 字段 | 类型 | 说明 |
|---|---|---|
| totalUsers | int | |
| totalLost | int | |
| totalFound | int | |
| handedOverCount | int | |
| recoveryRate | decimal(5,2) | 已归还 / 总发布 |
| avgHandleHours | decimal(8,2) | 从发布到交接平均时长 |
| pendingCertifications | int | |
| pendingReports | int | |

## GET /api/v1/admin/users

查询参数：`role` / `status` / `keyword`（手机/昵称/学号）/ `userId`（精确 ID）/ `pageNo` / `pageSize`

## POST /api/v1/admin/users/{id}/status

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| status | UserStatus | 是 | 仅 `ACTIVE` / `DISABLED` |
| reason | string | 条件 | `DISABLED` 必填 |

仅允许 `ACTIVE <-> DISABLED`。`CANCELLED` 是终态，不能恢复为 `ACTIVE`；用户参与活动认领或交接时禁止禁用并返回 `40005`。原因写入通知和结构化审计日志。
