# 认证与用户接口

枚举取自 `../architecture/enums.md`。错误码见 `conventions.md §7`。

## POST /api/v1/auth/login  · 公开

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| loginType | enum | 是 | `PHONE_CODE` / `PASSWORD` |
| phone | string | 条件 | 用户手机号登录时必填，11 位数字 |
| account | string | 条件 | 后台账号登录时必填，3-64 位 |
| code | string | 条件 | `PHONE_CODE` 必填，6 位数字 |
| password | string | 条件 | `PASSWORD` 必填，6-32 位 |

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

用户注册后使用手机号密码登录；后台管理员使用账号密码登录。管理员账号不允许通过验证码登录。

错误：`41002` 验证码错 · `41005` 用户禁用

## POST /api/v1/auth/register  · 公开

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| phone | string | 是 | 11 位数字 |
| code | string | 是 | 6 位数字 |
| password | string | 是 | 6-32 位 |
| nickname | string | 是 | 2-20 字 |

返回同 `/auth/login`。手机号已注册返回 `41001`。

## POST /api/v1/auth/sms-code  · 公开

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| phone | string | 是 | 11 位 |

同号码 60 秒内重复请求返回 `40008`。

课程演示仅在服务端同时开启 `DEBUG`、`SMS_DEBUG_ENABLED` 且号码精确命中 `SMS_DEMO_PHONES` 时返回 `debugCode`。非白名单号码必须走真实短信 sender；sender 未配置或发送失败返回 `41006`，且不会生成或保存用户无法取得的验证码。

## GET /api/v1/users/me  · 用户

返回 `data`：
| 字段 | 类型 | 说明 |
|---|---|---|
| id | string(ulid) | |
| phone | string | 脱敏：中间 4 位 * |
| nickname | string | |
| avatarUrl | string | 可空 |
| avatarRef | string | 可空，仅本人编辑使用的稳定引用 |
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
| avatarRef | string | 否 | `bizType=USER` 上传返回的 `assetRef` |

## POST /api/v1/users/me/certification  · 用户

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| campusId | string | 是 | 4-20 位字母数字 |
| realName | string | 是 | 2-20 字 |
| documentImageRef | string | 是 | `bizType=CERT` 上传返回的 `assetRef` |

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
| documentImageUrl | string / null | 敏感短签名 URL；对象不可用时为 null |
| documentImageRef | string | 稳定引用，仅申请人本人重提时使用；未迁移的 legacy key 可为 null |
| reviewStatus | ReviewStatus | |
| reviewComment | string | 可空 |
| reviewedAt | datetime | 可空 |
| createdAt | datetime | |

## POST /api/v1/users/me/cancel  · 用户

软注销。确认不存在活动认领或交接后，在同一事务中关闭该用户全部 `SEARCHING` 失物与 `PENDING` 招领、失效关联 match 和尚未执行的 durable job，再置 `users.status = CANCELLED`；受影响的其他失物发布者会收到匹配失效提醒。存在活动认领或交接时返回 `40005`，需先完成流程；`CANCELLED` 是终态，后台也不能恢复为 `ACTIVE`。
