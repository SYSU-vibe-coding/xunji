# 匹配接口

规则见 `../architecture/matching-rules.md`。

## GET /api/v1/matches  · 用户

查询参数：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| bizType | enum | 是 | `LOST` / `FOUND` |
| bizId | string(ulid) | 是 | 当前用户必须是该物品发布者 |
| pageNo, pageSize | int | 否 | |
| minScore | number | 否 | 0-100，默认 70 |

返回 list 元素：
| 字段 | 类型 |
|---|---|
| matchId | string(ulid) |
| lostItemId | string(ulid) |
| foundItemId | string(ulid) |
| imageScore, textScore, locationScore, timeScore, totalScore | decimal(5,2) |
| matchStatus | MatchStatus |
| counterpart | object | 对方物品摘要：`{id, itemName, category, coverImageUrl, location, time}` |
| createdAt | datetime |

仅返回当前用户为当事方（失主或拾获者）的匹配。

## POST /api/v1/matches/recalculate  · ADMIN / 用户（本人）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| bizType | enum | 是 | `LOST` / `FOUND` |
| bizId | string(ulid) | 是 | |

异步重算。返回 `{taskId, estimatedCount}`。

## GET /api/v1/matches/{id}  · 用户（当事方）

返回匹配得分拆解 + 对方物品完整信息 + `canClaim`（bool，依据 `FoundItemStatus` 与现有认领判断）。

非当事方访问 → `40003`。
