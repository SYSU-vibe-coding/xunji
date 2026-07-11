# P0/P1 修复追踪报告（2026-07-11）

## 1. 修复范围

本轮以 `full-code-audit-2026-07-11.md` 为基线，修复用户端、管理端、主后端、AI 服务、对象存储、数据库迁移和部署配置中的 P0/P1 问题。

修复原则：

- 权限和状态约束必须由后端保证，前端隐藏按钮只用于改善体验。
- 跨实体状态变化必须有统一锁顺序、CAS、唯一约束和事务边界。
- AI 失败不得放宽敏感信息保护，也不得伪造不存在的模型能力。
- 异步任务必须先持久化，再由 runner 执行；`BackgroundTasks` 只负责唤醒。
- 页面必须区分 loading、empty、error、success 和 conflict。

## 2. 已完成修复

### 2.1 认证与部署安全

- 短信验证码改为随机、限时、一次性消费并增加发送冷却。
- 调试验证码仅在 `DEBUG + SMS_DEBUG_ENABLED + SMS_DEMO_PHONES` 同时满足时返回。
- 管理员 bootstrap 默认关闭，只在显式开启且管理员不存在时创建，不再重置已有账号。
- 移除密码明文回退。
- 非本地环境使用默认 JWT 或管理员密码时拒绝启动。
- AI 内部接口使用 `X-Service-Token`，端口默认只绑定回环地址。
- CORS 改为显式来源白名单。
- MySQL、MinIO、JWT、管理员和 AI 凭据在 Compose 中改为必填。
- MySQL 和 MinIO 默认只绑定 `127.0.0.1`。
- `.dockerignore` 排除真实 `.env` 文件，只放行示例文件。

### 2.2 私有对象存储

- MinIO bucket 强制私有并主动删除匿名 bucket policy。
- 图片真实解码、限制字节和像素、按真实格式重编码并剥离 EXIF。
- 数据库存储 `asset://object-key`，不保存永久 URL或短期签名 URL。
- 资产 key 包含业务类型和上传者，提交时验证所有权、业务类型和对象存在性。
- API 按角色动态签发普通或敏感短期 URL。
- 敏感 FOUND、CERT、CLAIM_PROOF 和 CERT 类 LOST 不向无权用户签发原图。
- 编辑使用 `imageRefs`，不再把展示 URL 回写为原始资产。
- AI 使用独立的内部短期签名，AI 服务下载后转为 data URI，不把内网 MinIO URL转交给云模型。

### 2.3 认领与交接状态机

- 发起认领锁定 found、match、lost 和双方用户，并验证匹配归属和审核状态。
- 同一 found 通过 CAS 和活动状态检查保证最多一个有效认领。
- `FAST_TRACK` 已关闭；CERT、电子设备和低信誉用户按更严格等级处理。
- 问答要求问题集合完整，按关键词命中比例平均值判定。
- 失败认领增加冷却和 24 小时尝试上限。
- 拒绝认领会释放 found 和 match。
- 新增 `TERMINATED`，关闭 found、举报下架时终止活动 claim/handover。
- CLAIMING 状态禁止修改影响认领证据的招领内容。
- 交接创建幂等，双方确认使用锁和 CAS，重复确认幂等。
- 结案事务统一更新 claim、found、合法关联 lost、match、积分、通知和日志。
- 用户注销或禁用在存在活动认领/交接时被阻止。

### 2.4 匹配与 AI

- `(lost_item_id, found_item_id)` 增加数据库唯一约束和原子 upsert。
- 匹配候选只包含审核通过、活动且发布者不同的记录。
- 低分重算、物品编辑或关闭会将旧匹配置为 `EXPIRED`。
- “我的匹配”直接按用户关联查询，不再受前 10 条发布限制。
- 查看详情执行 `NEW -> READ`，合法认领执行 `READ/NEW -> CLAIMED`。
- 匹配通知遵守订阅开关，并使用 `relatedType=MATCH` 深链。
- 没有图像模型时返回 `imageAvailable=false`，不再伪造 50/60 分。
- 综合分只对真实可用维度重新归一。
- 时间评分使用拾获时刻到失物时间区间的小时距离。
- 文本模型只比较名称和描述，不重复计算地点和时间。
- AI 分类结果作为标签和建议保存，不自动覆盖用户类别。
- 用户手工重算明确为同步 `COMPLETED`，不再返回伪异步任务状态。

### 2.5 Durable Job / Outbox

- 新增 `durable_jobs` 表和 runner。
- 发布、编辑与 MATCH、CLASSIFY、SENSITIVE 任务在同一事务落库。
- 任务支持领取锁、版本去重、失败退避、最大尝试次数和遗留 RUNNING 回收。
- `BackgroundTasks` 仅唤醒 runner，进程退出不会丢失数据库中的任务。
- FOUND 含图片时默认敏感，只有所有检测明确安全才解除敏感状态。
- 匹配结果、通知和任务完成状态在同一事务提交。

### 2.6 搜索与用户端交互

- 搜索支持类别、业务状态、地点、事件时间区间和事件时间排序。
- 搜索条件、分页和模式写入 URL。
- 匹配、物品、通知入口保留 `matchId` 和正确业务方向。
- 两个认领入口共享完整答案校验并防重复提交。
- 上传中禁止提交，上传模型保存 assetRef、展示 previewUrl。
- 我的发布改为 lost/found 独立分页，并支持从详情精确定位。
- 同时展示业务状态、审核状态和审核意见。
- 关键读页面区分错误和空数据并提供重试。
- 冲突错误触发数据刷新，不继续使用过期按钮。
- 登录、注册和验证码发送使用 single-flight；资料加载失败回滚新会话。
- 移动端 dock 固定，弹窗和高影响操作在窄屏可达。
- 用户端新增公告列表和详情入口。

### 2.7 管理端治理

- 认证、内容和举报审批使用行锁/CAS，状态变化返回冲突而非覆盖。
- 举报处罚规则由后端强制校验；有效物品举报同时下架内容、终止流程、扣分、通知和审计。
- 举报目标支持精确详情，不再依赖普通列表人工查找。
- 新增认领申诉队列、详情和管理员复核入口。
- 内容审核详情展示描述、时间、图片、问题、状态和审核意见。
- 公告支持草稿、发布、下线、用户列表/详情和通知深链。
- CANCELLED 用户不可恢复为 ACTIVE。
- 高影响操作增加确认、原因、逐行 loading 和冲突刷新。
- 操作日志筛选值与后端 action 对齐。
- 管理列表区分错误和空数据，筛选分页写入 URL并防旧响应覆盖。

### 2.8 数据一致性与契约

- 积分锁定用户，记录边界裁剪后的实际 delta。
- 信用流水唯一冲突在 savepoint 内转换为幂等结果，不破坏外层业务事务。
- 举报增加 `(reporter_id, target_type, target_id)` 唯一约束。
- 认证提交锁定用户，审批确认当前最新申请。
- 失物删除改为逻辑 CLOSED。
- Compose 停止使用 `schema.sql` 初始化，backend 启动前执行 Alembic。
- 通知已读响应、match 参数组合、claim 枚举和敏感响应 nullable 契约已统一。

## 3. 数据库迁移

本轮新增迁移：

| Revision | 内容 |
| --- | --- |
| `20260711_0004` | 匹配 pair 唯一约束及重复数据清理 |
| `20260711_0005` | 内容审核意见字段 |
| `20260711_0006` | 匹配评分来源、降级和图像可用性字段 |
| `20260711_0007` | 举报唯一约束及相关一致性修复 |
| `20260711_0008` | durable job/outbox 表、索引和约束 |

当前 Alembic 单一 head：`20260711_0008`。

`20260711_0004` 在本工作区按“尚未发布”处理：迁移先建立重复 match 的 `old_id -> keeper_id` 映射，重写 `claim_requests.match_id` 与 `notifications(related_type=MATCH).related_id`，之后才删除重复行并添加唯一约束。若某个外部环境已经执行过旧版 0004，不能通过重跑迁移恢复已删除引用，必须在备份和业务数据核对基础上编写该环境专用修复脚本。

部署前必须备份数据库并在 MySQL 8.4 环境执行：

```bash
cd backend
uv run alembic upgrade head
```

曾使用 `schema.sql` 初始化且没有 `alembic_version` 的数据库，必须先比对真实结构再决定迁移或 stamp，不得直接盲目执行 `alembic stamp head`。

## 4. 自动化验证

| 模块 | 验证 | 结果 |
| --- | --- | --- |
| backend | Ruff | 通过 |
| backend | Mypy | 80 个源文件通过 |
| backend | Pytest | 197 passed |
| backend | Alembic | 单一 head `20260711_0008` |
| ai-service | Ruff | 通过 |
| ai-service | Mypy | 14 个源文件通过 |
| ai-service | Pytest | 59 passed |
| user-app | Vitest | 15 passed |
| user-app | production build | 通过 |
| admin-web | Vitest | 15 passed |
| admin-web | production build | 通过 |

## 5. 仍需环境验证

最终只读回归没有发现仍可复现的代码级 P0/P1。以下不是继续用单元测试可以消除的风险：

- 当前环境没有 Docker CLI，Compose 只完成配置展开验证，没有运行全套容器 smoke。
- SQLite 无法完全证明 MySQL 的 `FOR UPDATE SKIP LOCKED`、CAS 和并发等待行为。
- 新迁移尚未在真实 MySQL 数据副本上执行。
- 需要验证私有 MinIO 的匿名访问拒绝、浏览器预签名 URL 和 AI 内部签名链路。
- 工作区中曾存在本地明文第三方 token 和远程数据库口令，必须在对应平台轮换；仅加入 ignore 不能使旧凭据恢复安全。
- 尚缺 Playwright 双用户加管理员的真实浏览器 P0 流程。
- 当前没有真实脱敏图生成器；无权用户看到空图而不是伪脱敏图，这是安全降级，但 P1 视觉脱敏能力仍可后续实现。
- FAILED durable job 暂无后台重试页面，当前通过日志和数据库观测。

## 6. 推荐验收顺序

1. 轮换全部曾暴露的本地凭据，生成非默认部署密钥。
2. 在测试数据库备份上执行 `alembic upgrade head`。
3. 启动 MySQL、MinIO、AI、backend 和两个前端。
4. 验证 MinIO 匿名访问拒绝及各角色图片权限。
5. 执行发布 -> durable job -> 匹配通知 -> 认领 -> 审核 -> 双确认交接。
6. 执行拒绝、申诉、关闭、举报下架和账号禁用异常分支。
7. 执行并发认领、并发审批和并发双确认。
8. 通过后再更新浏览器验收项，不以单元测试代替端到端证据。
