# 管理后台接口

所有接口要求 `role = ADMIN`，未满足返回 `48002`。

## GET /api/v1/admin/certifications

查询参数：`reviewStatus` (ReviewStatus) / `pageNo` / `pageSize`

返回 list 元素：`{id, userId, nickname, campusId, realName, documentImageUrl, reviewStatus, createdAt}`

## POST /api/v1/admin/certifications/{id}/review

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| action | enum | 是 | `APPROVE` / `REJECT` |
| comment | string | 条件 | `REJECT` 必填，≤ 200 |

效果：
- APPROVE：`cert_status = APPROVED` + 加 20 分（`CERT_APPROVED`） + 通知
- REJECT：`cert_status = REJECTED` + 通知
- 写 `operation_logs`（action `CERT_APPROVE/CERT_REJECT`）

## GET /api/v1/admin/items/review

查询参数：`bizType` (`LOST`/`FOUND`) / `pageNo` / `pageSize`

返回：待审核物品列表（新发布 24h 内或被举报的）。

## POST /api/v1/admin/items/{bizType}/{id}/review

路径：`bizType` = `lost` / `found`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| action | enum | 是 | `APPROVE` / `REJECT` |
| comment | string | 条件 | `REJECT` 必填 |

REJECT 效果：对应物品 `status = CLOSED`，通知发布者。

## GET /api/v1/admin/reports

查询参数：`handleStatus` (ReportHandleStatus) / `targetType` / `pageNo` / `pageSize`

返回 list 元素：`{id, reporterId, reportedUserId, targetType, targetId, reason, description, handleStatus, createdAt}`

## POST /api/v1/admin/reports/{id}/handle

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| action | enum | 是 | `VALID` / `INVALID` |
| result | string | 条件 | `VALID` 必填，≤ 200 |
| creditDelta | int | 否 | `VALID` 可携带，通常 `-30`（冒领）或 `-20`（虚假）|
| reasonCode | CreditReasonCode | 条件 | 有 `creditDelta` 必填 |

效果：
- `VALID`：置 `CLOSED` + 对被举报人扣分（见 `credit-rules.md`）
- `INVALID`：置 `REJECTED`
- 通知举报人处理结果

## POST /api/v1/admin/announcements

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| title | string | 是 | 1-100 |
| content | string | 是 | 1-5000 |
| publishNow | bool | 否 | 默认 true；false 则 `status = DRAFT` |

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

查询参数：`role` / `status` / `keyword`（手机/昵称/学号）/ `pageNo` / `pageSize`

## POST /api/v1/admin/users/{id}/status

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| status | UserStatus | 是 | |
| reason | string | 条件 | `DISABLED` 必填 |
