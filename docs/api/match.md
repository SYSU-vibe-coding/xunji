# 匹配接口

规则见 `../architecture/matching-rules.md`。

## GET /api/v1/matches  · 用户

查询参数：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| bizType | enum | 条件 | `LOST` / `FOUND`；与 `bizId` 必须同时提供或同时省略 |
| bizId | string(ulid) | 条件 | 与 `bizType` 同时提供时，当前用户必须是该物品发布者 |
| pageNo, pageSize | int | 否 | |
| minScore | number | 否 | 0-100，默认 70 |

返回 list 元素：
| 字段 | 类型 |
|---|---|
| matchId | string(ulid) |
| lostItemId | string(ulid) |
| foundItemId | string(ulid) |
| imageScore, textScore, locationScore, timeScore, totalScore | decimal(5,2) |
| imageAvailable | bool | `false` 时 `imageScore=0`，前端应显示“图像未参与” |
| degraded | bool | 是否使用了降级维度 |
| scoreSource | enum | `RULE_BASED` / `TEXT_MODEL_RULES` / `MULTIMODAL_MODEL` / `LEGACY_RENORMALIZED` |
| matchStatus | MatchStatus |
| counterpart | object | 对方物品摘要：`{id, itemName, category, coverImageUrl, location, time}`；敏感或无图时 `coverImageUrl=null` |
| createdAt | datetime |

两字段均省略时返回当前用户全部匹配；两字段均提供时返回指定本人发布的物品匹配。只提供其中一个返回参数错误。

## POST /api/v1/matches/recalculate  · ADMIN / 用户（本人）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| bizType | enum | 是 | `LOST` / `FOUND` |
| bizId | string(ulid) | 是 | |

同步重算，单次最多处理 `MATCH_RECALCULATE_MAX_CANDIDATES`（默认 100）个候选。成功返回 `{status: "COMPLETED", matchedCount}`；接口不返回 `QUEUED` 或无状态查询能力的伪任务 ID。调用方应使用独立的合理超时（用户端为 60 秒），只有收到 `COMPLETED` 才显示重算完成。

## GET /api/v1/matches/{id}  · 用户（当事方）

返回匹配得分拆解、对方物品完整信息、关联认领摘要 `claimId` / `claimStatus`，以及 `canClaim`。`canClaim` 同时依据双方物品状态、现有认领、当前用户状态和信用分判断；信用分低于 30 时仍可查看匹配，但不可发起认领。

非当事方访问 → `40003`。
