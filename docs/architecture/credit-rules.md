# 信誉积分规则

## 1. 初始值与边界

- 新用户 `credit_score = 100`
- 允许范围 `[0, 999]`
- `< 60` 自动提升认领验证等级（见 `matching-rules.md §5`）
- `< 30` 暂停认领权限，调用认领接口返回错误码 `45002`
- 暂停认领不影响搜索和查看匹配；匹配详情返回 `canClaim=false`，创建认领仍以服务端实时信用分为准

## 2. 加减分表

所有变动写入 `credit_logs`，`reason_code` 必须为下列之一：

| reason_code | delta | 触发条件 |
|---|---|---|
| HANDOVER_SUCCESS | +10 | 交接完成（双方都确认） |
| FOUND_ITEM_PUBLISHED | +3 | 招领发布成功（每账号每日上限 5 条有效） |
| PEER_GOOD_REVIEW | +5 | 交接后对方给予好评（预留） |
| CERT_APPROVED | +20 | 校园认证通过 |
| CLAIM_REJECTED_NO_APPEAL | -5 | 认领被拒后 7 天内未申诉 |
| FRAUD_CLAIM_CONFIRMED | -30 | 举报冒领经管理员核实 |
| FAKE_PUBLISH_CONFIRMED | -20 | 虚假发布经管理员核实 |
| CLAIM_TIMEOUT_NO_REPLY | -3 | 拾获者 48h 未处理认领请求 |

## 3. 写入约定

- 积分变动与业务状态变更**必须在同一事务**
- `change_credit` 只加入调用方事务，不自行 `commit`；调用方负责与业务状态一起提交
- 更新前锁定用户行，将积分裁剪到 `[0, 999]` 后，以 `actual_delta = new_score - old_score` 作为流水、通知和审计中的变动值
- 每次变动都产生一条 `credit_logs` 记录，包含 `biz_type` 和 `biz_id`（指向触发业务）
- 边界裁剪后 `actual_delta = 0` 仍写幂等流水，通知和审计明确标注已达积分边界
- `users.credit_score` 在事务中同步更新，不依赖事后聚合
- 变动后发送 `NoticeType = CREDIT_CHANGED` 通知

## 4. 批处理规则

- `CLAIM_REJECTED_NO_APPEAL`：定时任务每日扫描 `claim_requests` 状态为 `REJECTED` 且 `updated_at <= now - 7d` 且未扣过分
- `CLAIM_TIMEOUT_NO_REPLY`：每小时扫描 `PENDING` 且 `claimed_at <= now - 48h` 的认领，向拾获者扣分
- 批处理扣分同样写 `credit_logs`，`biz_id` 指向 `claim_id`

## 5. 反作弊

- 同一 `biz_id + reason_code` 不重复扣/加分；以数据库唯一约束 `uk_credit_dedup(user_id, biz_type, biz_id, reason_code)` 兜底，并用 savepoint 回滚并发冲突中的整次积分变化而不影响外层业务事务
- `FOUND_ITEM_PUBLISHED` 按 `user_id + DATE(created_at)` 限流 5 次
