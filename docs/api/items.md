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
| imageUrls | string[] | 否 | ≤ 5，值为 `/files/upload` 返回的 `assetRef` |

返回 `data`：`{id, status}`（status = `SEARCHING`）

后置：发布事务内持久化 `MATCH` 与 `CLASSIFY` 任务，接口不等待 AI；数据库 outbox runner 异步执行（`matching-rules.md §4`）。

## PUT /api/v1/lost-items/{id}  · 用户（本人）

发布者可修改自己发布的失物信息。修改后 `reviewStatus` 置为 `PENDING`，进入后台内容审核；若原记录因审核驳回处于 `CLOSED`，修改提交后重新进入 `SEARCHING`。存在关联活动认领时禁止修改。

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| itemName | string | 是 | 1-100 字 |
| category | ItemCategory | 是 | |
| description | string | 否 | ≤ 500 字 |
| lostTimeStart | datetime | 是 | `yyyy-MM-dd HH:mm:ss` |
| lostTimeEnd | datetime | 是 | `>= lostTimeStart` |
| lostLocation | string | 是 | 1-100 字 |
| subscribeMatch | bool | 否 | 默认 false |
| imageUrls | string[] | 否 | ≤ 5，`assetRef`，覆盖原图片列表 |

返回 `data`：`{id, status, reviewStatus}`。

## DELETE /api/v1/lost-items/{id}  · 用户（本人）

删除是领域逻辑删除：保留失物根、图片和审计关联，仅将状态置为 `CLOSED`。已找回（`FOUND`）或存在关联活动认领的记录不可删除。

返回 `data`：`{id, status}`（status = `CLOSED`）。

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
| imageUrls | string[] | 否 | ≤ 5，`assetRef` |
| verifyQuestions | object[] | 否 | 0-3 条 |
| verifyQuestions[].questionText | string | 是 | 1-100 |
| verifyQuestions[].answerKeywords | string[] | 是 | 1-10 个，每个 ≤ 20 字 |

业务：
- `category=CERT` 始终置 `is_sensitive=1`；其他含图片记录也先置 1（待异步复核），无图普通类别置 0
- 发布事务内持久化 `MATCH`、`CLASSIFY`，含图片时再持久化 `SENSITIVE`；接口不串行等待 AI
- 只有全部图片明确非敏感、非降级且无需复核时，后台任务才将 `is_sensitive` 释放为 0；任何超时、空结果、降级或需复核均保持 1
- 返回 `{id, status, isSensitive}`（status = `PENDING`）；`isSensitive=true` 可表示敏感或尚待复核

## POST /api/v1/found-items/batch  · STAFF

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| items | object[] | 是 | 1-50 条，每条结构同上 |

返回 `{successIds, failures}`，`failures[].index` + `failures[].error`。

## PUT /api/v1/found-items/{id}  · 用户（本人）/ STAFF

发布者可修改自己发布的招领信息；STAFF 可修改其发布或代登记的招领信息。修改后 `reviewStatus` 置为 `PENDING`，进入后台内容审核。

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| itemName | string | 是 | 1-100 |
| category | ItemCategory | 是 | |
| description | string | 否 | ≤ 500 |
| foundTime | datetime | 是 | `yyyy-MM-dd HH:mm:ss` |
| foundLocation | string | 是 | 1-100 |
| custodyType | CustodyType | 是 | |
| contactPreference | ContactPreference | 是 | |
| imageUrls | string[] | 否 | ≤ 5，`assetRef`，覆盖原图片列表 |
| verifyQuestions | object[] | 否 | 0-3 条；未传则不修改验证问题 |

返回变更摘要 `{id, status, reviewStatus}`；客户端需要完整内容时重新请求详情。编辑同样原子写入新业务版本的持久化任务；旧版本任务发现新版本后不再覆盖新内容。含图片的编辑先恢复 `is_sensitive=1` 等待异步复核。

## GET /api/v1/lost-items  · 用户

查询参数：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| pageNo, pageSize | int | 否 | 见 `conventions.md §5` |
| category | ItemCategory | 否 | |
| status | LostItemStatus | 否 | |
| keyword | string | 否 | 匹配 `item_name`、`description` 或后台 AI 分类标签 |
| location | string | 否 | 模糊匹配 |
| eventTimeStart | datetime | 否 | 事件时间下界；失物按区间重叠，招领按 `foundTime >=` 过滤 |
| eventTimeEnd | datetime | 否 | 事件时间上界；失物按区间重叠，招领按 `foundTime <=` 过滤 |
| sortBy | enum | 否 | `CREATED_DESC`（默认）/ `CREATED_ASC` / `EVENT_DESC` / `EVENT_ASC`；事件时间对失物取 `lost_time_start`，对招领取 `found_time` |

返回 list 元素：
| 字段 | 类型 |
|---|---|
| id, userId, itemName, category, description | |
| lostTimeStart, lostTimeEnd, lostLocation | |
| status | LostItemStatus |
| reviewStatus | ReviewStatus |
| reviewComment | string 或 null |
| coverImageUrl | string（首张图或 null） |
| createdAt | |

**不返回** `ai_tags` 原值。

发布或编辑成功后，持久化 runner 独立调用 AI 分类并将 `{tags, suggestedCategory, confidence, source, degraded}` 作为 JSON 写入 `ai_tags`。建议类别不会覆盖用户选择的 `category`；分类失败不会回滚发布，会按配置退避重试并在达到上限后将任务标记为 `FAILED`。

## GET /api/v1/found-items  · 用户

查询参数：同上 + `isSensitive` (bool) + `custodyType`。

返回 list 元素：同 lost 类似，额外：
- `reviewStatus`：ReviewStatus
- `reviewComment`：审核意见，无意见时为 null
- `isSensitive`：true 时，仅发布者/管理员可收到短时原图 URL；其他用户的 `coverImageUrl` 为 null
- `custodyType` / `contactPreference`

## GET /api/v1/me/lost-items  · 用户

我的发布-失物列表。查询参数同 `GET /api/v1/lost-items`，但只返回当前登录用户发布的失物记录；用于个人中心管理页，可传 `includeClosed=true` 查看历史记录。

返回分页结构，list 元素同 `GET /api/v1/lost-items`。

## GET /api/v1/me/found-items  · 用户

我的发布-招领列表。查询参数同 `GET /api/v1/found-items`，但只返回当前登录用户发布或代登记归属当前用户的招领记录；用于个人中心管理页，可传 `includeClosed=true` 查看历史记录。

返回分页结构，list 元素同 `GET /api/v1/found-items`。

## GET /api/v1/lost-items/{id}  · 用户

返回完整字段 + `reviewStatus` + `reviewComment`（可为 null）+ `imageUrls[]`（短时展示 URL）+ `matchCount`（仅发布者本人可见）。`category=CERT` 视为敏感：仅发布者/管理员获得敏感短签名原图，其他用户的 `imageUrls=[]`、`coverImageUrl=null`。发布者额外收到 `imageRefs[]` 用于编辑，编辑时不得回传 `imageUrls`；未迁移到含 uploader 路径格式的 legacy key 不会出现在 `imageRefs`，需按迁移说明复制或重新上传。

## GET /api/v1/found-items/{id}  · 用户

返回完整字段 + `reviewStatus` + `reviewComment`（可为 null）+ `imageUrls[]`（短时展示 URL）+ `verifyQuestions[]`（**仅 questionText，不返回 answerKeywords**）+ `hasActiveClaim`（bool）。敏感记录对非发布者/非管理员返回 `imageUrls=[]` 且 `isSensitive=true`；发布者额外收到 `imageRefs[]` 用于编辑。

审核可见性统一采用“新建自动后审通过、编辑需复审”：新建记录初始 `reviewStatus=APPROVED`；编辑后置 `PENDING`。公共列表及非 owner 详情只返回 `APPROVED`，owner 可查看自己的 `PENDING/REJECTED`，管理员可查看全部。匹配和认领也只消费 `APPROVED`。

## PATCH /api/v1/lost-items/{id}/status  · 用户（本人）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| status | LostItemStatus | 是 | 仅允许 `FOUND` 或 `CLOSED` |

`SEARCHING → FOUND/CLOSED`，其他转移返回 `40005`。存在关联活动认领时，标记 `FOUND`、关闭、编辑和删除均返回清晰冲突；举报确认有效由管理员事务先锁失物并终止关联认领后再下架。

## PATCH /api/v1/found-items/{id}/status  · ADMIN / 用户（本人）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| status | FoundItemStatus | 是 | 允许 `CLOSED`（主动关闭） |

`PENDING/CLAIMING → CLOSED` 可；`RETURNED/CLOSED` 不可手动改。`CLAIMING` 关闭时需同时终止未完成的认领流程，避免继续交接。

## POST /api/v1/files/upload  · 用户

`multipart/form-data`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| file | file | 是 | 见 `conventions.md §8` |
| bizType | BizType | 是 | |

返回：
| 字段 | 类型 | 说明 |
|---|---|---|
| assetRef | string | 稳定引用，业务提交和编辑使用 |
| previewUrl | string | 短时预览 URL，不得持久化或回写 |
| contentType | string | 服务端识别并重编码后的真实 MIME |
| size | long（字节） | 重编码后的对象大小 |
| uploadedAt | datetime | 上传时间 |

## POST /api/v1/reports  · 用户

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| targetType | ReportTargetType | 是 | `LOST_ITEM` / `FOUND_ITEM` / `CLAIM_REQUEST` |
| targetId | string(ulid) | 是 | 必须精确存在 |
| reason | string | 是 | 1-100 |
| description | string | 否 | ≤ 500 |

同一用户不可重复举报同一目标，重复返回 `47002`；精确目标不存在返回 `47001`。返回 `{id, handleStatus}`，初始状态为 `PENDING`。
