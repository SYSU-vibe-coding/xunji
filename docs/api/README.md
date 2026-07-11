# API 文档

## 阅读顺序

1. `conventions.md` — 通用规则（时间/错误码/幂等/鉴权/文件）
2. `../architecture/enums.md` — 枚举字典
3. 按需读对应模块文档

## 接口索引

权限写法见 `conventions.md §9`，统一使用 `公开` / `用户` / `STAFF` / `ADMIN` 及其带上下文限定的形式。

### 认证（`auth.md`）
| 方法 | 路径 | 权限 |
|---|---|---|
| POST | /api/v1/auth/login | 公开 |
| POST | /api/v1/auth/sms-code | 公开 |
| GET | /api/v1/users/me | 用户 |
| PUT | /api/v1/users/me | 用户 |
| POST | /api/v1/users/me/certification | 用户 |
| GET | /api/v1/users/me/certification | 用户 |
| POST | /api/v1/users/me/cancel | 用户 |

### 物品（`items.md`）
| 方法 | 路径 | 权限 |
|---|---|---|
| POST | /api/v1/lost-items | 用户 |
| POST | /api/v1/found-items | 用户 / STAFF |
| POST | /api/v1/found-items/batch | STAFF |
| GET | /api/v1/lost-items | 用户 |
| GET | /api/v1/found-items | 用户 |
| GET | /api/v1/me/lost-items | 用户 |
| GET | /api/v1/me/found-items | 用户 |
| GET | /api/v1/lost-items/{id} | 用户 |
| GET | /api/v1/found-items/{id} | 用户 |
| PUT | /api/v1/found-items/{id} | 用户（本人）/ STAFF |
| PATCH | /api/v1/lost-items/{id}/status | 用户（本人） |
| PATCH | /api/v1/found-items/{id}/status | ADMIN / 用户（本人） |
| POST | /api/v1/reports | 用户 |
| POST | /api/v1/files/upload | 用户 |

### 匹配（`match.md`）
| 方法 | 路径 | 权限 |
|---|---|---|
| GET | /api/v1/matches | 用户 |
| POST | /api/v1/matches/recalculate | ADMIN / 用户（本人） |
| GET | /api/v1/matches/{id} | 用户（当事方） |

### 认领（`claim.md`）
| 方法 | 路径 | 权限 |
|---|---|---|
| POST | /api/v1/claims | 用户 |
| GET | /api/v1/claims/my | 用户 |
| GET | /api/v1/claims/{id} | ADMIN / 用户（当事方） |
| POST | /api/v1/claims/{id}/review | ADMIN / 用户（拾获者） |
| POST | /api/v1/claims/{id}/proofs | 用户（认领者） |
| POST | /api/v1/claims/{id}/appeal | 用户（认领者） |
| POST | /api/v1/claims/{id}/handover | 用户（认领者或拾获者） |
| POST | /api/v1/claims/{id}/handover/confirm | 用户（认领者或拾获者） |

### 通知（`notification.md`）
| 方法 | 路径 | 权限 |
|---|---|---|
| GET | /api/v1/notifications | 用户 |
| GET | /api/v1/notifications/unread-count | 用户 |
| POST | /api/v1/notifications/{id}/read | 用户 |
| POST | /api/v1/notifications/read-all | 用户 |
| GET | /api/v1/announcements | 公开 |
| GET | /api/v1/announcements/{id} | 公开 |

### 后台（`admin.md`）
| 方法 | 路径 | 权限 |
|---|---|---|
| GET | /api/v1/admin/certifications | ADMIN |
| POST | /api/v1/admin/certifications/{id}/review | ADMIN |
| GET | /api/v1/admin/items/review | ADMIN |
| POST | /api/v1/admin/items/{bizType}/{id}/review | ADMIN |
| GET | /api/v1/admin/reports | ADMIN |
| POST | /api/v1/admin/reports/{id}/handle | ADMIN |
| GET | /api/v1/admin/claims | ADMIN |
| GET | /api/v1/admin/claims/{id} | ADMIN |
| POST | /api/v1/admin/announcements | ADMIN |
| GET | /api/v1/admin/dashboard | ADMIN |
| GET | /api/v1/admin/users | ADMIN |
| POST | /api/v1/admin/users/{id}/status | ADMIN |

### AI 内部（`ai-service.md`）
| 方法 | 路径 |
|---|---|
| POST | /internal/ai/classify-item |
| POST | /internal/ai/detect-sensitive |
| POST | /internal/ai/calculate-match |

## 维护规则

- 接口字段或枚举变更：先改文档（本目录 + `enums.md`）再改代码
- 新增接口：同步更新本索引表
- 请求/响应示例省略 `code/message/timestamp` 等外层字段（见 `conventions.md §4`）
