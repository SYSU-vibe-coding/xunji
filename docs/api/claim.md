# 认领与交接接口

验证等级与规则见 `../architecture/matching-rules.md §5-6`。状态枚举 `ClaimReviewStatus` 见 `../architecture/enums.md`。

## POST /api/v1/claims  · 用户

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| matchId | string(ulid) | 否 | 若来自匹配列表则传 |
| foundItemId | string(ulid) | 是 | |
| answers | object[] | 条件 | `LEVEL_1/LEVEL_2` 且招领设置了问题时，必须完整提交 |
| answers[].questionId | string(ulid) | 是 | |
| answers[].answerText | string | 是 | ≤ 200 字 |
| proofImageUrls | string[] | 条件 | `LEVEL_2/LEVEL_3` 必需；可在创建时提交，或进入 `PROOF_PENDING` 后补交 |

业务：
- 后端按纯规则判定 `verify_level`：`CERT=LEVEL_3`、`ELECTRONIC=LEVEL_2`、其他 `LEVEL_1`；信誉 30-59 再升级一级
- `LEVEL_1` 判定已有问答，平均关键词命中率 `>=0.6` 后置 `ANSWER_PASSED`
- `LEVEL_2` 要求已有问答通过和凭证；缺凭证为 `PROOF_PENDING`，齐备后为 `ANSWER_PASSED`
- `LEVEL_3` 要求凭证并保持人工审核路径；缺凭证为 `PROOF_PENDING`，齐备后为 `PENDING`
- 问答失败写入通用失败记录并返回 `44004`，5 分钟冷却，滚动 24 小时最多 3 次；错误、拒绝原因及认领者详情均不泄露关键词或命中分数
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
| proofImageUrls | string[] | 仅双方/管理员可见的敏感短签名 URL；对象不可用时为空数组/省略该项 |
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
| proofImageUrls | string[] | 是 | 1-5 个当前认领者的 `CLAIM_PROOF assetRef` |
| proofText | string | 否 | ≤ 500 |

仅 `PROOF_PENDING` 可用。`LEVEL_2` 成功后置 `ANSWER_PASSED`；`LEVEL_3` 成功后置 `PENDING`，继续人工审核。

## POST /api/v1/claims/{id}/appeal  · 用户（认领者）

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| reason | string | 是 | 1-500 字 |

仅 `REJECTED` 且未申诉过可用。置 `APPEALING`，并通知所有 `ACTIVE ADMIN`，由管理员再次 review。重复申诉 → `44007`。

管理员通过 `GET /api/v1/admin/claims?reviewStatus=APPEALING` 查看申诉队列，通过 `GET /api/v1/admin/claims/{id}` 查看包含原拒绝理由、申诉理由、双方和物品信息的详情；审批复用 `POST /api/v1/claims/{id}/review`。

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
