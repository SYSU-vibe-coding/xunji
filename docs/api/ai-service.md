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

## POST /internal/ai/detect-sensitive

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| imageUrl | string | 是 | 单张图 |

返回：
| 字段 | 类型 | 说明 |
|---|---|---|
| isSensitive | bool | |
| sensitiveType | enum | `ID_CARD` / `CAMPUS_CARD` / `BANK_CARD` / `OTHER` / null |
| maskedImageUrl | string | 脱敏后图片 URL（`isSensitive=true` 必返） |
| recognizedFields | object | 可空，`{name, idNumber, campusId}`，仅管理员可见 |

## POST /internal/ai/calculate-match

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| lostItem | object | 是 | 含 `name, description, location, time, imageUrls[]` |
| foundItem | object | 是 | 同上 |

返回：
| 字段 | 类型 | 范围 |
|---|---|---|
| imageScore | decimal(5,2) | 0-100 |
| textScore | decimal(5,2) | 0-100 |
| locationScore | decimal(5,2) | 0-100 |
| timeScore | decimal(5,2) | 0-100 |
| totalScore | decimal(5,2) | 按 `matching-rules.md §1` 加权 |

## 降级约定

- 超时 / 非 2xx / 网络异常 → 主后端忽略 AI 结果，走规则降级
- 主后端记录 `50002` 到日志但不抛给前端
- AI 服务独立部署，重启不影响主后端
