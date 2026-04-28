# 认证与用户接口

枚举取自 `../architecture/enums.md`。错误码见 `conventions.md §7`。

## POST /api/v1/auth/login  · 公开

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| loginType | enum | 是 | `PHONE_CODE` / `PASSWORD` |
| phone | string | 是 | 11 位数字 |
| code | string | 条件 | `PHONE_CODE` 必填，6 位数字 |
| password | string | 条件 | `PASSWORD` 必填，明文 6-32 位 |

返回 `data`：
| 字段 | 类型 | 说明 |
|---|---|---|
| token | string | JWT，有效期 7 天 |
| user.id | string(ulid) | |
| user.nickname | string | |
| user.avatarUrl | string | 可空 |
| user.role | UserRole | |
| user.certStatus | CertStatus | |
| user.creditScore | int | |

不存在的手机号且 `PHONE_CODE` 登录自动注册。

错误：`41002` 验证码错 · `41005` 用户禁用

## POST /api/v1/auth/sms-code  · 公开

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| phone | string | 是 | 11 位 |

同号码 60 秒内重复请求返回 `40008`。

## GET /api/v1/users/me  · 用户

返回 `data`：
| 字段 | 类型 | 说明 |
|---|---|---|
| id | string(ulid) | |
| phone | string | 脱敏：中间 4 位 * |
| nickname | string | |
| avatarUrl | string | 可空 |
| role | UserRole | |
| certStatus | CertStatus | |
| campusId | string | 未认证时 null |
| realName | string | 未认证时 null |
| creditScore | int | |
| status | UserStatus | |

## PUT /api/v1/users/me  · 用户

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| nickname | string | 否 | 2-20 字 |
| avatarUrl | string | 否 | 合法 URL |

## POST /api/v1/users/me/certification  · 用户

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| campusId | string | 是 | 4-20 位字母数字 |
| realName | string | 是 | 2-20 字 |
| documentImageUrl | string | 是 | 来自 `/files/upload` |

业务：
- `cert_status = PENDING` 时不可重复提交 → `41004`
- `REJECTED` 后可重提，旧记录保留

## GET /api/v1/users/me/certification  · 用户

返回最近一次申请：
| 字段 | 类型 | 说明 |
|---|---|---|
| id | string(ulid) | |
| campusId | string | |
| realName | string | |
| documentImageUrl | string | |
| reviewStatus | ReviewStatus | |
| reviewComment | string | 可空 |
| reviewedAt | datetime | 可空 |
| createdAt | datetime | |

## POST /api/v1/users/me/cancel  · 用户

软注销。置 `users.status = CANCELLED`，不物理删除。
