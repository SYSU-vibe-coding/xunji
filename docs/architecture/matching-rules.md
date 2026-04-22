# 匹配与验证规则

## 1. 匹配综合评分

分数范围 0-100。权重固定：

```
total_score = 0.4 * image_score
            + 0.3 * text_score
            + 0.2 * location_score
            + 0.1 * time_score
```

各子分由 AI 服务（`POST /internal/ai/calculate-match`）返回。AI 不可用时走规则降级（见 §2）。

## 2. 规则降级算法（AI 不可用）

```
image_score    = 0（没图或无 AI，直接 0）
text_score     = keyword_overlap(lost.name+lost.desc, found.name+found.desc) * 100
location_score = 100 if same_location else (60 if same_building else 0)
time_score     = max(0, 100 - |hours_diff| * 2)   # 超过 50h 归零
```

`keyword_overlap`：按字符串分词后 Jaccard 相似度。

## 3. 阈值与动作

| 条件 | 动作 |
|---|---|
| `total_score < 70` | 不生成 `match_results` |
| `total_score >= 70` | 生成记录，`match_status = NEW` |
| `total_score >= 90` 且 `found.category = CERT` | 附加高优先级通知：`NoticeType = MATCH_RECOMMEND` + 标记 `priority=HIGH` |

## 4. 匹配触发时机

- 新 `lost_items` 插入后 → 查 `found_items.status = PENDING` 全量做匹配
- 新 `found_items` 插入后 → 查 `lost_items.status = SEARCHING` 全量做匹配
- 管理员调用 `POST /api/v1/matches/recalculate` → 指定记录重算
- 以上均异步执行，不阻塞发布接口

## 5. 认领验证等级判定

按顺序命中第一条即返回：

```
if found.category == CERT and claimant.cert_status == APPROVED:
    return FAST_TRACK
if found.category == ELECTRONIC:
    base = LEVEL_2
elif found 属于高价值（由管理员打标，预留扩展）:
    base = LEVEL_3
else:
    base = LEVEL_1

# 低信誉升级
if claimant.credit_score < 60:
    base = upgrade_one_level(base)   # LEVEL_1→LEVEL_2, LEVEL_2→LEVEL_3
if claimant.credit_score < 30:
    拒绝创建认领，返回错误码 45002
return base
```

`FAST_TRACK` 分支：系统比对 `claimant.real_name + campus_id` 与招领物品 OCR 出的证件信息（由 AI 服务返回的 `sensitiveType/maskedImageUrl` 同时带上 `recognizedFields`），一致则直接置 `ANSWER_PASSED`，并跳过问答。

## 6. 一级问答判定

```
for each question in found_item.verify_questions:
    answer = claim.answers[question.id]
    score = keyword_hit_ratio(answer.text, question.answer_keywords)
if avg(scores) >= 0.6:  通过
else:                    不通过，状态置 REJECTED，允许申诉
```

`keyword_hit_ratio` = 命中关键词数 / 关键词总数。

## 7. 敏感物品判定

AI 服务 `POST /internal/ai/detect-sensitive` 返回 `isSensitive=true` → `found_items.is_sensitive = 1`，图片保存 `masked_image_url`，前端**永远**只展示脱敏图。
