# 物品接口

枚举取自 `../architecture/enums.md`。

## POST /api/v1/lost-items  · 用户

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| itemName | string | 是 | 1-100 字 |
| category | ItemCategory | 是 | |
| description | string | 否 | ≤ 500 字 |
| lostTimeStart | datetime | 是 | `yyyy-MM-dd HH:mm:ss` |
| lostTimeEnd | datetime | 是 | `>= lostTimeStart` |
| lostLocation | string | 是 | 1-100 字 |
| subscribeMatch | bool | 否 | 默认 false |
| imageUrls | string[] | 否 | ≤ 5，来自 `/files/upload` |

返回 `data`：`{id, status}`（status = `SEARCHING`）

后置：异步触发匹配（`matching-rules.md §4`）

## PUT /api/v1/lost-items/{id}  · 用户（本人）

发布者可修改自己发布的失物信息。修改后 `reviewStatus` 置为 `PENDING`，进入后台内容审核；若原记录因审核驳回处于 `CLOSED`，修改提交后重新进入 `SEARCHING`。

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| itemName | string | 是 | 1-100 字 |
| category | ItemCategory | 是 | |
| description | string | 否 | ≤ 500 字 |
| lostTimeStart | datetime | 是 | `yyyy-MM-dd HH:mm:ss` |
| lostTimeEnd | datetime | 是 | `>= lostTimeStart` |
| lostLocation | string | 是 | 1-100 字 |
| subscribeMatch | bool | 否 | 默认 false |
| imageUrls | string[] | 否 | ≤ 5，覆盖原图片列表 |

返回 `data`：`{id, status, reviewStatus}`。

## DELETE /api/v1/lost-items/{id}  · 用户（本人）

发布者可删除自己发布的失物信息；已找回（`FOUND`）记录不可删除。

返回 `data`：`{id, status}`（status = `DELETED`）。

## POST /api/v1/found-items  · 用户 / STAFF

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| itemName | string | 是 | 1-100 |
| category | ItemCategory | 是 | |
| description | string | 否 | ≤ 500 |
| foundTime | datetime | 是 | |
| foundLocation | string | 是 | 1-100 |
| custodyType | CustodyType | 是 | |
| contactPreference | ContactPreference | 是 | |
| imageUrls | string[] | 否 | ≤ 5 |
| verifyQuestions | object[] | 否 | 0-3 条 |
| verifyQuestions[].questionText | string | 是 | 1-100 |
| verifyQuestions[].answerKeywords | string[] | 是 | 1-10 个，每个 ≤ 20 字 |

业务：
- `category = CERT` 或 AI 判定敏感 → 置 `is_sensitive = 1`，调用 AI 脱敏（见 `ai-service.md`）
- 返回 `{id, status, isSensitive}`（status = `PENDING`）

## POST /api/v1/found-items/batch  · STAFF

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| items | object[] | 是 | 1-50 条，每条结构同上 |

返回 `{successIds, failures}`，`failures[].index` + `failures[].error`。

## GET /api/v1/lost-items  · 用户

查询参数：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| pageNo, pageSize | int | 否 | 见 `conventions.md §5` |
| category | ItemCategory | 否 | |
| status | LostItemStatus | 否 | |
| keyword | string | 否 | 匹配 `item_name` 或 `description` |
| location | string | 否 | 模糊匹配 |
| sortBy | enum | 否 | `CREATED_DESC`（默认）/ `CREATED_ASC` |

返回 list 元素：
| 字段 | 类型 |
|---|---|
| id, userId, itemName, category, description | |
| lostTimeStart, lostTimeEnd, lostLocation | |
| status | LostItemStatus |
| reviewStatus | ReviewStatus |
| coverImageUrl | string（首张图或 null） |
| createdAt | |

**不返回** `ai_tags` 原值。

## GET /api/v1/found-items  · 用户

查询参数：同上 + `isSensitive` (bool) + `custodyType`。

返回 list 元素：同 lost 类似，额外：
- `reviewStatus`：ReviewStatus
- `isSensitive`：true 时 `coverImageUrl` 返回脱敏图
- `custodyType` / `contactPreference`

## GET /api/v1/lost-items/{id}  · 用户

返回完整字段 + `reviewStatus` + `imageUrls[]` + `matchCount`（仅发布者本人可见）。非发布者仅看公开字段。

## GET /api/v1/found-items/{id}  · 用户

返回完整字段 + `reviewStatus` + `imageUrls[]`（敏感则为脱敏图数组）+ `verifyQuestions[]`（**仅 questionText，不返回 answerKeywords**）+ `hasActiveClaim`（bool）。

## PATCH /api/v1/lost-items/{id}/status  · 用户（本人）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| status | LostItemStatus | 是 | 仅允许 `FOUND` 或 `CLOSED` |

`SEARCHING → FOUND/CLOSED`，其他转移返回 `40005`。

## PATCH /api/v1/found-items/{id}/status  · ADMIN / 用户（本人）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| status | FoundItemStatus | 是 | 允许 `CLOSED`（主动关闭） |

`PENDING → CLOSED` 可；`CLAIMING/RETURNED` 不可手动改。

## POST /api/v1/files/upload  · 用户

`multipart/form-data`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| file | file | 是 | 见 `conventions.md §8` |
| bizType | BizType | 是 | |

返回：
| 字段 | 类型 |
|---|---|
| url | string |
| contentType | string |
| size | long（字节） |
| uploadedAt | datetime |
