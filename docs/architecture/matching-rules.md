# 匹配与验证规则

## 1. 匹配综合评分

分数范围 0-100。基础权重固定：

```
total_score = 0.4 * image_score
            + 0.3 * text_score
            + 0.2 * location_score
            + 0.1 * time_score
```

综合分只在**实际可用且双方都有输入信号**的维度上归一：

```
total_score = sum(available_score_i * weight_i) / sum(available_weight_i)
```

例如当前没有图像相似模型，但文本、地点、时间均可用且均为 100 分时，综合分仍为 100，而不是被图像权重封顶在 60。图像存在仅代表有输入，不代表图像维度可用。

各子分由 AI 服务（`POST /internal/ai/calculate-match`）返回，主后端根据 `imageAvailable` 和原始输入重新计算综合分，不信任远端 `totalScore`。AI 不可用时走规则降级（见 §2）。

## 2. 规则降级算法（AI 不可用）

```
image_score    = 0（无真实图像模型，不用图片存在性伪造相似度）
text_score     = keyword_overlap(lost.name+lost.desc, found.name+found.desc) * 100
location_score = 100 if same_location else (60 if same_building else 0)
hours_distance = distance(found.time, [lost.timeStart, lost.timeEnd])
time_score     = max(0, 100 - hours_distance * 2) # 距区间超过 50h 归零
```

`keyword_overlap`：英文按字母数字词元、中文按连续二元字符切分后计算 Jaccard 相似度。中文二元切分用于覆盖“雨伞 / 黑色伞 / 黑色雨伞”这类没有空格但语义明显重叠的降级场景。

拾获时刻落在失物时间区间内时 `hours_distance = 0`；在区间外时取到最近端点的小时距离。规则响应标记 `imageAvailable=false`、`degraded=true`、`scoreSource=RULE_BASED`。

## 3. 阈值与动作

| 条件 | 动作 |
|---|---|
| `total_score < 70` | 不生成 `match_results` |
| `total_score >= 70` | 生成记录，`match_status = NEW` |
| `total_score >= 90` 且 `found.category = CERT` | 附加高优先级通知：`NoticeType = MATCH_RECOMMEND` + 标记 `priority=HIGH` |

## 4. 匹配触发时机

- 新 `lost_items` 插入后 → 查 `found_items.status = PENDING` 全量做匹配
- 新 `found_items` 插入后 → 查 `lost_items.status = SEARCHING` 全量做匹配
- 用户或管理员调用 `POST /api/v1/matches/recalculate` → 同步重算指定记录，最多处理配置项 `MATCH_RECALCULATE_MAX_CANDIDATES` 个候选，成功返回 `COMPLETED`
- 发布/编辑事务内分别写入 `MATCH`、`CLASSIFY` 持久化任务；FOUND 含图片时另写 `SENSITIVE`
- lifespan runner 轮询 `durable_jobs`，多 worker 通过 `FOR UPDATE SKIP LOCKED` 互斥领取；`BackgroundTasks` 只发快速唤醒提示，不是可靠性来源
- 任务按业务版本去重，旧版本执行时若发现同类型新版本则幂等跳过；失败指数退避，超过最大次数转 `FAILED`
- `match_results` upsert 和新匹配通知在同一事务提交；重复执行不会重复创建 pair 或通知

## 5. 认领验证等级判定

规则由后端纯函数统一计算：

```
if found.category == CERT:
    base = LEVEL_3
elif found.category == ELECTRONIC:
    base = LEVEL_2
else:
    base = LEVEL_1

# 低信誉升级
if 30 <= claimant.credit_score < 60:
    base = upgrade_one_level(base)   # LEVEL_1→LEVEL_2, LEVEL_2→LEVEL_3
if claimant.credit_score < 30:
    拒绝创建认领，返回错误码 45002
return base
```

`LEVEL_1` 执行已有问答；`LEVEL_2` 执行已有问答并要求凭证；`LEVEL_3` 要求凭证且必须人工审核。系统没有可靠 OCR 实名闭环，因此不存在自动通过证件的快捷等级。

## 6. 一级问答判定

```
for each question in found_item.verify_questions:
    answer = claim.answers[question.id]
    score = keyword_hit_ratio(answer.text, question.answer_keywords)
if avg(scores) >= 0.6:  通过
else:                    不通过，状态置 REJECTED，允许申诉
```

`keyword_hit_ratio` = 命中关键词数 / 关键词总数。

失败仅返回统一的“验证未通过，请稍后重试”，不向认领者返回逐题分数或关键词命中情况。同一 `claimant + foundItem` 失败后冷却 5 分钟，滚动 24 小时最多失败 3 次；限制数据由失败认领记录持久化统计。

## 7. 敏感物品判定

FOUND 含图片时先置 `found_items.is_sensitive=1`。异步调用 AI 服务 `POST /internal/ai/detect-sensitive` 后，仅当所有图片都明确返回 `isSensitive=false`、`needsReview=false`、`degraded=false` 才置 0；超时、空结果、降级、需复核或敏感结果均保持 1。`CERT` 不允许解除敏感标记。当前未生成可信脱敏副本，因此无权限用户不展示原图。
