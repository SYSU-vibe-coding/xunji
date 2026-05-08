# 认领与交接接口

验证等级与规则见 `../architecture/matching-rules.md §5-6`。状态枚举 `ClaimReviewStatus` 见 `../architecture/enums.md`。

## POST /api/v1/claims  · 用户

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| matchId | string(ulid) | 否 | 若来自匹配列表则传 |
| foundItemId | string(ulid) | 是 | |
| answers | object[] | 条件 | 非 `FAST_TRACK` 必填 |
| answers[].questionId | string(ulid) | 是 | |
| answers[].answerText | string | 是 | ≤ 200 字 |
| proofImageUrls | string[] | 条件 | `LEVEL_2` 必填，1-5 张 |

业务：
- 后端按 `matching-rules.md §5` 判定 `verify_level` 并写入
- `FAST_TRACK` 直接置 `APPROVED`
- `LEVEL_1` 判定问答 → `ANSWER_PASSED` 或 `REJECTED`
- `LEVEL_2` 初始 `PROOF_PENDING`（若凭证已传则 `ANSWER_PASSED`，等拾获者审）
- 已存在进行中认领 → `44001`
- 信誉 `< 30` → `45002`

返回：`{id, verifyLevel, reviewStatus}`

## GET /api/v1/claims/my  · 用户

查询参数：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| role | enum | 否 | `CLAIMANT`（默认）/ `FINDER` |
| reviewStatus | ClaimReviewStatus | 否 | 支持多值逗号分隔 |
| pageNo, pageSize | int | 否 | |

返回 list 元素：`{id, foundItemId, itemName, verifyLevel, reviewStatus, updatedAt}`

## GET /api/v1/claims/{id}  · ADMIN / 用户（当事方）

返回：
| 字段 | 类型 | 说明 |
|---|---|---|
| id, matchId, foundItemId, claimantId | | |
| verifyLevel | VerifyLevel | |
| reviewStatus | ClaimReviewStatus | |
| rejectReason | string | 可空 |
| answers | object[] | `{questionId, questionText, answerText, matchScore}` |
| proofImageUrls | string[] | |
| handover | object | 可空，见下 |
| claimedAt, updatedAt | datetime | |

## POST /api/v1/claims/{id}/review  · ADMIN / 用户（拾获者）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| action | enum | 是 | `APPROVE` / `REJECT` |
| comment | string | 条件 | `REJECT` 必填，≤ 200 字 |

状态转移：
- `PENDING/ANSWER_PASSED/PROOF_PENDING` + APPROVE → `APPROVED`
- 同上 + REJECT → `REJECTED`
- 其他状态 → `44003`

非拾获者且非 `ADMIN` → `44006`

## POST /api/v1/claims/{id}/proofs  · 用户（认领者）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| proofImageUrls | string[] | 是 | 1-5 张 |
| proofText | string | 否 | ≤ 500 |

仅 `PROOF_PENDING` 可用。成功后置 `ANSWER_PASSED`。

## POST /api/v1/claims/{id}/appeal  · 用户（认领者）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| reason | string | 是 | 1-500 字 |

仅 `REJECTED` 且未申诉过可用。置 `APPEALING`，由 ADMIN 再次 review。重复申诉 → `44007`。

## POST /api/v1/claims/{id}/handover  · 用户（认领者或拾获者）

仅 `APPROVED` 可用。

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| method | HandoverMethod | 是 | |
| handoverLocation | string | 是 | 1-100 |
| handoverTime | datetime | 是 | `> now` |

返回 `{handoverId}`。

## POST /api/v1/claims/{id}/handover/confirm  · 用户（认领者或拾获者）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| role | enum | 是 | `OWNER`（认领者）/ `FINDER`（拾获者） |

事务内执行：
1. 标记对应方 `*_confirmed = 1`
2. 双方都确认 → `handover_records.completed_at = now`
3. `claim_requests.review_status = HANDED_OVER`
4. `found_items.status = RETURNED`；若该认领来自匹配结果（`matchId` 非空），同步将关联 `lost_items.status = FOUND`
5. 写积分（见 `../architecture/credit-rules.md` `HANDOVER_SUCCESS`）
6. 发 `NoticeType = HANDOVER_REMINDER` 给双方

任一步失败整体回滚。
