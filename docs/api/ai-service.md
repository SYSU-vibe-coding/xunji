# AI 服务内部接口

仅主后端调用，不对前端暴露。路径前缀 `/internal/ai`。默认超时 3s，失败不得阻塞主后端事务，走 `matching-rules.md §2` 规则降级。

## POST /internal/ai/classify-item

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| imageUrls | string[] | 否 | ≤ 5 |
| itemName | string | 否 | |
| description | string | 否 | |

至少 `imageUrls` 或 `itemName` 其一。

返回：
| 字段 | 类型 | 说明 |
|---|---|---|
| category | ItemCategory | AI 建议类别 |
| tags | string[] | ≤ 10 个标签 |
| confidence | decimal(5,2) | 0-100 |
| degraded | bool | 是否使用关键词规则降级 |
| source | enum | `VISION_MODEL` / `KEYWORD_RULES` |

## POST /internal/ai/detect-sensitive

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| imageUrl | string | 是 | 单张图 |

返回：
| 字段 | 类型 | 说明 |
|---|---|---|
| isSensitive | bool | |
| sensitiveType | enum | `ID_CARD` / `CAMPUS_CARD` / `BANK_CARD` / `OTHER` / null |
| maskedImageUrl | string | 可空；当前检测能力不生成可信脱敏副本 |
| recognizedFields | object | 可空，`{name, idNumber, campusId}`，仅管理员可见 |
| degraded | bool | 是否为降级结果；主后端不会据降级结果解除敏感保护 |
| needsReview | bool | 是否需要人工复核；true 时保持敏感保护 |

主后端异步逐图调用此接口。只有同一招领的所有图片均明确返回 `isSensitive=false`、`degraded=false`、`needsReview=false` 才允许公开；超时或空结果由持久化任务重试，期间保持 `is_sensitive=1`。

## POST /internal/ai/calculate-match

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| lostItem | object | 是 | 含 `name, description, location, time, timeEnd, imageUrls[]`；`time/timeEnd` 是失物区间 |
| foundItem | object | 是 | 含 `name, description, location, time, imageUrls[]`；`time` 是拾获时刻 |

返回：
| 字段 | 类型 | 范围 |
|---|---|---|
| imageScore | decimal(5,2) | 0-100 |
| textScore | decimal(5,2) | 0-100 |
| locationScore | decimal(5,2) | 0-100 |
| timeScore | decimal(5,2) | 0-100 |
| totalScore | decimal(5,2) | 按 `matching-rules.md §1` 加权 |
| imageAvailable | bool | 是否有真实图像相似模型参与 |
| degraded | bool | 是否含规则降级维度 |
| scoreSource | enum | `RULE_BASED` / `TEXT_MODEL_RULES` / `MULTIMODAL_MODEL` |

## 降级约定

- 超时 / 非 2xx / 网络异常 → 主后端忽略 AI 结果，走规则降级

## POST /internal/ai/verify-claim-answers

批量校验认领问答的语义一致性，一次 1-3 道题。请求项为 `{questionText, referenceAnswers, answerText}`；`referenceAnswers` 仅在内部服务间传递，不写日志、不返回前端。

返回 `{scores, passed, degraded, source}`：`scores` 与请求顺序一致，平均分 `>=60` 时 `passed=true`。`source=TEXT_MODEL` 表示语义模型成功；模型不可用时按关键词命中率返回 `source=KEYWORD_RULES`、`degraded=true`。
- 主后端记录 `50002` 到日志但不抛给前端
- AI 服务独立部署，重启不影响主后端
- 当前未配置图像相似模型，必须返回 `imageScore=0`、`imageAvailable=false`；图片存在性不得作为图像相似度
- 公网图片只允许 `AI_ALLOWED_IMAGE_HOSTS`；私网 IP 或单标签主机只允许精确命中 `AI_TRUSTED_PRIVATE_IMAGE_HOSTS`，后者不支持通配符
