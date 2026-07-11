# 全量代码与交互逻辑审计报告（2026-07-11）

> 本文件保留 2026-07-11 修复前的审计基线，便于缺陷追踪。P0/P1 修复结果、迁移和最终验证证据见 `p0-p1-remediation-2026-07-11.md`。

## 1. 审计目标与范围

本次审计覆盖以下模块，并以“用户动作 -> 权限与前置条件 -> 状态变化 -> 连带副作用 -> 页面反馈 -> 异常恢复”为主线，而不是只检查代码格式。

- `frontend/user-app`：登录、认证、发布、搜索、匹配、认领、交接、消息、个人中心
- `frontend/admin-web`：认证审核、内容审核、举报、用户、公告、匹配任务、操作日志
- `backend`：鉴权、业务状态机、事务、并发、通知、积分、对象存储、接口契约
- `ai-service`：分类、敏感检测、匹配评分、失败降级、与主后端的集成
- `docs`、数据库迁移、部署配置和测试：需求、枚举、流程、API、验收口径的一致性

严重度定义：

| 级别 | 判断标准 |
| --- | --- |
| P0 | 可造成越权、隐私泄露、数据状态矛盾，或直接阻断课程 P0 主流程 |
| P1 | 主要功能可绕行，但常见入口、异常分支、后台处置或契约明显断链 |
| P2 | 不立即阻断主流程，但影响可用性、可解释性、可维护性或测试可信度 |

## 2. 总体结论

项目已经具备完整的页面和 API 外形，串行理想路径可在以下限制下跑通：

> 手工触发匹配 -> 从匹配页直接认领 -> 不发生拒绝或关闭 -> 由拾获者创建交接 -> 双方依次确认

但“发布 -> 自动匹配 -> 通知 -> 认领 -> 异常处理 -> 交接归档 -> 后台治理”尚未形成稳定闭环。问题根因不是单个按钮，而是以下四类系统性缺口：

1. 没有一个跨 `lost/found/match/claim/handover` 的权威状态机，规则散落在多个 service 和页面条件中。
2. 关键写操作采用“先查再写”，缺少行锁、条件更新、唯一约束和明确事务边界。
3. 页面只覆盖理想顺序，缺少错误、空数据、冲突、重试、返回上下文和通知深链。
4. 文档描述的是目标行为，测试多为 service 级 happy path，验收清单因此高估了实际完成度。

建议将 `docs/architecture/interaction-logic-model.md` 作为后续交互逻辑的权威模型。

## 3. 课程 P0 闭环核对

| 需求 | 当前结论 | 主要缺口 |
| --- | --- | --- |
| P0-01 注册登录 | 部分可用 | 固定短信验证码可接管普通账号；默认管理员启动逻辑不安全 |
| P0-02 身份认证 | 串行可用 | 重复/并发审批可覆盖结果；证件图片访问控制失效 |
| P0-03 失物发布 | 基本可用 | 发布后不触发匹配；上传中可先提交；审核策略不一致 |
| P0-04 招领发布 | 已修复 | 敏感检测已移出发布路径；无可信脱敏副本时保持原图私有 |
| P0-05 搜索筛选 | 未达标 | 状态、地点、事件时间筛选不完整，地点提示与实际查询不符 |
| P0-06 匹配展示 | 可绕行 | 只能手工/管理端触发；旧匹配不失效；聚合列表可能缺数据或跳错对象 |
| P0-07 认领验证 | 高风险 | 匹配归属未校验、空答案可提交、问答可反复试探、并发可产生多个有效认领 |
| P0-08 交接确认 | 仅串行可用 | 并发双确认可能不结案；关闭/拒绝/注销与交接不联动 |
| P0-09 站内通知 | 部分可用 | 匹配通知没有深链；订阅开关无效；停留页面不刷新 |
| P0-10 后台审核 | 部分可用 | 举报无法精确核实并下架目标；并发审核可互相覆盖；申诉无后台入口 |

## 4. P0 缺陷

### P0-01 敏感图片实际上公开，所谓脱敏 URL 仍指向原图

- 证据：`backend/app/item/service.py:940-1000`、`ai-service/app/services/sensitive.py:36-47`、`ai-service/app/services/_baseline.py:46-63`
- 触发：上传校园卡、认证证件或认领凭证后直接访问对象 URL，或访问追加 `?masked=1` 的 URL。
- 影响：MinIO bucket 被设为匿名读取；查询参数不会改变对象内容，未登录者也可能取得原图。
- 修复：bucket 改私有；数据库保存 asset ID/object key；通过鉴权下载接口签发短期 URL；真实生成独立脱敏副本；增加原图越权集成测试。

### P0-02 固定短信验证码在所有环境返回，可接管已知手机号账号

- 证据：`backend/app/user/service.py:28-55`、`backend/app/user/service.py:106-115`
- 触发：对任意已注册手机号请求验证码，读取响应调试码后验证码登录。
- 影响：无需控制手机即可登录普通用户账号，验证码成功后也未一次性消费。
- 修复：仅显式本地开发环境允许调试码；使用随机、限时、一次性 OTP；增加手机号/IP/设备限流。课程演示可使用白名单演示账号，不能对任意号码开放。

### P0-03 启动过程会重置管理员密码、角色和状态

- 证据：`backend/app/core/bootstrap.py:10-36`、`backend/app/core/config.py:31-38`
- 触发：服务使用默认配置重启，或管理员账号与普通用户昵称冲突。
- 影响：已有管理员密码被恢复为配置值，被禁用账号重新激活，普通用户可能因昵称匹配被提升。
- 修复：bootstrap 只允许首次创建；已有账号绝不重置；后台账号使用独立唯一字段；非开发环境发现默认密钥/密码时拒绝启动。

### P0-04 证件自动快捷通道未做 OCR 实名比对

- 证据：`backend/app/claim/service.py:396-412`、`ai-service/app/services/sensitive.py:36-47`、`docs/architecture/matching-rules.md:42-64`
- 触发：任意已认证用户认领任意 `CERT` 招领。
- 影响：系统直接把认领置为 `APPROVED`，没有核对证件姓名和校园编号，形成冒领通道。
- 修复：OCR 与实名匹配落地前移除证件自动快捷等级；证件统一使用凭证和人工审核。

### P0-05 匹配认领未校验当前用户是否为关联失物发布者

- 证据：`backend/app/claim/service.py:67-79`、`backend/app/claim/service.py:345-353`
- 触发：普通用户取得他人的 `matchId`，对该匹配中的招领发起认领并完成交接。
- 影响：交接完成会把匹配关联的他人失物置为 `FOUND`。
- 修复：事务内校验 `lost.user_id == current_user.id`、两侧业务状态和审核状态，并锁定 match、lost、found。

### P0-06 同一招领可并发创建多个有效认领

- 证据：`backend/app/claim/service.py:67-104`、`backend/app/claim/repository.py:27-33`、`backend/alembic/versions/20260428_0002_backend_b_tables.py:38-56`
- 触发：两个用户同时认领同一招领。
- 影响：“先查询活动认领，再插入”的竞态可让两个请求同时通过，继而创建多个交接和积分流水。
- 修复：锁定 found 行；用数据库约束或 reservation 表保证一个 found 只有一个活动认领；审批时再次检查冲突。

### P0-07 拒绝、关闭、注销与认领/交接没有级联规则

- 证据：`backend/app/claim/service.py:177-218`、`backend/app/item/service.py:684-714`、`backend/app/claim/service.py:270-353`、`backend/app/user/service.py:248-264`
- 触发：认领被拒绝、`CLAIMING` 招领被关闭、交接中用户注销或禁用。
- 影响：招领可能永久停在 `CLAIMING`；已关闭物品仍能完成交接并变为 `RETURNED`；另一方无法继续完成流程。
- 修复：建立统一领域状态转换服务；拒绝后无活动认领则恢复 `PENDING`；关闭时事务化终止 claim/handover 并通知双方；活动交接期间限制注销或提供管理员接管。

### P0-08 双方并发确认交接可能都成功，但系统不执行结案

- 证据：`backend/app/claim/service.py:315-394`、`backend/app/claim/repository.py:123-132`
- 触发：双方几乎同时点击确认。
- 影响：两个请求都可能先读到双方未确认，各自只更新一侧，最终两个标志虽为真，但没有请求观察到完成条件，claim 仍非 `HANDED_OVER`。
- 修复：锁定 handover/claim 行或原子更新后重新读取；完成物品、积分、通知必须在同一事务内且可幂等重试。

### P0-09 Compose 数据库结构与 Alembic 不一致

- 证据：`deploy/docker/docker-compose.yml:16-20`、`backend/sql/schema.sql:197-212`、`backend/alembic/versions/20260428_0002_backend_b_tables.py:71-85`
- 触发：按 compose 使用手写 schema 初始化后并发创建交接。
- 影响：手写 schema 缺少 Alembic 中的 `UNIQUE(claim_id)`，可能出现多个 handover，后续单记录查询报错。
- 修复：部署统一执行 `alembic upgrade head`，停止维护第二份手写建表真相源。

### P0-10 发布后从未调度自动匹配

- 证据：`backend/app/item/service.py:82-137`、`backend/app/item/service.py:356-440`、`backend/app/item/service.py:1015-1027`、`backend/app/core/config.py:64-66`
- 触发：用户正常发布，不手工重算且管理员不运行全量任务。
- 影响：不会生成匹配或通知；发布页“自动匹配”承诺不成立。
- 修复：物品与版本化 `durable_jobs` 在同一事务提交；lifespan runner 可靠领取、退避重试和回收崩溃任务，`BackgroundTasks` 仅作唤醒提示。

### P0-11 认领问题允许空答案提交并生成不可恢复的拒绝记录

- 证据：`frontend/user-app/src/views/ItemDetailView.vue:121-136`、`frontend/user-app/src/views/MatchListView.vue:130-141`、`backend/app/claim/service.py:407-438`
- 触发：验证问题未填或只填一部分时提交。
- 影响：前端过滤空项但不拦截，后端把缺失答案视为失败并创建 `REJECTED`；用户只能申诉或反复尝试。
- 修复：两个入口共用同一认领表单和校验；答案数量必须等于问题数量；请求中禁用重复提交；失败尝试应有明确冷却/补充机制。

### P0-12 举报治理不能完成“核实 -> 下架 -> 正确处罚”

- 证据：`frontend/admin-web/src/views/ReportListView.vue:30-95`、`frontend/admin-web/src/views/ContentReviewView.vue:141-159`、`backend/app/admin/service.py:164-207`
- 触发：管理员处理虚假失物/招领举报。
- 影响：目标链接不能精确定位；已 `APPROVED` 内容通常无法关闭；举报有效也不下架目标；前端固定发送错误的 `FRAUD_CLAIM_CONFIRMED/-10` 组合。
- 修复：提供目标详情和精确路由；“确认违规”在一个事务内处理举报、下架内容、信用、通知和日志；后端校验处罚规则组合。

### P0-13 工作区存在本地明文凭据

- 证据：`deploy/docker/.env`、`backend/.env.remote`（当前未被 Git 跟踪）
- 触发：共享整个目录、备份、演示打包或误执行强制添加。
- 影响：第三方模型额度和远程数据库可能泄露。
- 修复：立即轮换相关 token/口令；改用 secret 文件、容器 secret 或进程环境变量；打包脚本显式排除本地凭据。

## 5. P1 缺陷

| ID | 问题 | 证据 | 影响与修复方向 |
| --- | --- | --- | --- |
| P1-01 | 从匹配详情进入物品后丢失 `matchId` | `frontend/user-app/src/views/MatchListView.vue:103-105`、`ItemDetailView.vue:121-136` | 交接后关联失物不自动找回；深链必须保留并验证 match 上下文 |
| P1-02 | 匹配通知不可跳转 | `frontend/user-app/src/views/NotificationsView.vue:42-59`、`backend/app/match/jobs.py:365-394` | 后端写 `MATCH`，共享枚举和前端不认识；增加权威枚举及 `/matches/:id` 深链 |
| P1-03 | 搜索未达到 P0 基线 | `frontend/user-app/src/views/SearchView.vue:30-125`、`backend/app/item/repository.py:50-57` | 缺状态、地点、事件时间；地点 placeholder 与请求不符；筛选应写入 URL |
| P1-04 | 审核策略互相矛盾 | `backend/app/item/service.py:97-110`、`backend/app/item/repository.py:25-73` | 新建直接批准，编辑待审仍可公开；必须明确预审或后审并统一查询、匹配、认领规则 |
| P1-05 | 管理员并发审批可覆盖结论 | `backend/app/user/service.py:137-154`、`backend/app/admin/service.py:164-173` | 缺少 `WHERE status=PENDING` 的 CAS；使用条件更新，冲突返回 `48001` |
| P1-06 | 申诉无管理端处理入口 | `frontend/admin-web/src/router/index.ts:18-40`、`backend/app/claim/service.py:177-218` | 用户可进入 `APPEALING`，管理员无法发现、查看理由或复核 |
| P1-07 | 公告“发布成功”但用户不可见 | `frontend/admin-web/src/views/AnnouncementView.vue:29-91`、`backend/app/admin/router.py:97-105` | 只有创建接口，无用户读取、通知和上下线闭环 |
| P1-08 | 多数列表把失败显示为空数据 | 用户端 `SearchView.vue:48-55`；管理端 `DashboardView.vue:26-41` | 用户无法区分无数据与系统故障；统一 loading/error/empty/success 四态并提供重试 |
| P1-09 | 网络错误会清除有效登录态 | 两端 `src/api/http.ts`、`src/stores/auth.ts` | `FORBIDDEN` 和临时网络错误被当作 token 失效；只在明确 401/禁用时清会话 |
| P1-10 | 上传中仍可提交主表单 | `frontend/user-app/src/components/ImageUploader.vue:41-57` | 记录可能缺图且产生孤儿对象；上传组件应向父级暴露 uploading/error |
| P1-11 | 匹配重算是假异步 | `backend/app/match/service.py:155-160`、`frontend/user-app/src/views/MatchListView.vue:84-99` | 前端 15 秒超时后可能显示失败但后端已写入；改为真实任务或明确同步契约 |
| P1-12 | 旧匹配不失效且 pair 无唯一键 | `backend/app/match/service.py:310-325`、`backend/app/match/models.py:10-26` | 编辑、关闭或降分后旧结果仍可见；增加 pair 唯一约束、版本和 `EXPIRED` 生命周期 |
| P1-13 | 图像相似度是固定占位分 | `ai-service/app/services/_baseline.py:114-123`、`backend/app/match/scoring.py:43-52` | 完全不同图片也显示图像得分；未实现模型时标记 unavailable 并重归一权重 |
| P1-14 | AI 分类和标签未接业务 | `backend/app/core/ai_client.py:63-83`、`backend/app/item/service.py:82-137` | `ai_tags` 从不写入，搜索也不消费；分类应作为异步建议而非孤立接口 |
| P1-15 | 已修复：敏感检测异步且 fail closed | `backend/app/item/service.py`、`backend/app/job/runner.py` | 含图片默认敏感；仅全部明确安全时解除，失败由 durable job 重试 |
| P1-16 | “我的匹配”只覆盖每类前 10 个物品 | `backend/app/match/service.py:88-109`、`backend/app/item/repository.py:25-36` | 历史发布的匹配不可达；直接 JOIN 按 user_id 查询 |
| P1-17 | 后台全部内容分页会漏记录 | `backend/app/item/service.py:805-858` | 对 lost/found 分别 offset 后拼接截断；应 UNION 后统一排序和分页 |
| P1-18 | 积分读改写和幂等存在竞态 | `backend/app/credit/service.py:40-59`、`backend/app/user/service.py:122-128` | 并发可能丢分，边界裁剪后流水 delta 不真实；原子更新并记录实际变化 |
| P1-19 | AI 内部接口无鉴权且映射宿主端口 | `ai-service/app/main.py:47-70`、`deploy/docker/docker-compose.yml:44-58` | 可被滥用模型额度和任意 URL；只放内部网络并增加 service token、URL 白名单和限流 |
| P1-20 | 问答失败可反复试探关键词 | `backend/app/claim/repository.py:9-33`、`backend/app/claim/service.py:481-518` | `REJECTED` 后可重试且认领者看到逐题分数；隐藏 oracle，限制次数并设置冷却 |
| P1-21 | 管理审核缺少目标详情与二次确认 | `frontend/admin-web/src/views/ContentReviewView.vue:102-159` | 只能看摘要，认证/内容高影响操作可单击重复提交；提供详情、确认和逐行 loading |
| P1-22 | 前后端通知已读契约漂移 | `frontend/user-app/src/api/notification.ts:22-27`、`backend/app/notification/service.py:59-72` | TypeScript 声明与运行时结构不同；增加响应 schema 与契约测试 |

## 6. P2 缺陷与工程风险

| ID | 问题 | 建议 |
| --- | --- | --- |
| P2-01 | 交接后的双方评价未实现 | 当前需求文档标为预留；若答辩要展示，先补需求、状态、一次性评价约束和积分防重 |
| P2-02 | 通知/详情停留时不刷新 | 最低限度增加手动刷新和页面可见时轮询，关键事件再考虑 SSE |
| P2-03 | 固定像素对话框在手机端溢出 | 统一 `min(560px, 94vw)` 或移动端全屏，底部按钮允许换行 |
| P2-04 | 搜索和后台筛选不写 URL | 将模式、关键词、状态、页码同步到 route query，保证返回、刷新和分享可恢复 |
| P2-05 | 操作日志筛选枚举与实际 action 不一致 | 由权威枚举生成前后端选项，日志保存 old/new/reason |
| P2-06 | 管理端匹配间隔只存内存 | 持久化配置并记录管理员与 old/new；多 worker 使用单实例锁 |
| P2-07 | 业务错误统一 HTTP 200 | 使用 401/403/404/409/422/500，并保留业务 code；有利于网关、监控和客户端处理 |
| P2-08 | 成功响应 request ID 不透传 | 中间件统一 request ID，并传给 AI 服务和结构化日志 |
| P2-09 | 时间格式依赖服务器本地时区 | 数据库存 UTC，读写时显式绑定时区，不依赖操作系统 `TZ` |
| P2-10 | 两个前端没有业务交互测试 | 增加组件/API mock 和 Playwright 双用户 P0 旅程；移除 `--passWithNoTests` |
| P2-11 | 后端没有 MySQL/MinIO 集成测试 | SQLite 单测无法发现迁移、锁、唯一约束和对象权限问题 |
| P2-12 | 多个 API/枚举存在漂移 | 从单一枚举/Schema 源生成前端类型，CI 增加 OpenAPI diff 或契约测试 |

## 7. 验收与测试可信度

本次实际执行结果：

| 模块 | 命令 | 结果 |
| --- | --- | --- |
| backend | `uv run ruff check .` | 通过 |
| backend | `uv run mypy app` | 通过，74 个源文件无类型错误 |
| backend | `uv run pytest` | 80 passed |
| ai-service | `uv run ruff check .` | 通过 |
| ai-service | `uv run mypy app` | 通过，12 个源文件无类型错误 |
| ai-service | `uv run pytest` | 34 passed |
| user-app | `pnpm test:unit && pnpm build` | 4 tests passed，生产构建通过 |
| admin-web | `pnpm test:unit && pnpm build` | 3 tests passed，生产构建通过 |

这些结果证明代码可编译、静态规则基本合格、已有单元测试通过，但不能证明交互闭环正确：

- 两个前端共 7 个测试都只覆盖格式化工具。
- 后端测试以 SQLite 和串行 service happy path 为主，没有 MySQL/MinIO 集成测试。
- 没有并发认领、并发审批、并发双确认测试。
- 没有“发布后自动匹配”的 HTTP/任务端到端测试。
- 没有通知深链、浏览器返回上下文、上传中提交和错误四态测试。
- 敏感图片测试只验证响应字段，没有验证对象存储匿名访问。
- `docs/testing/acceptance-checklist.md:19-24`、`:30-41` 的部分勾选应改为“单元路径通过，端到端待验证”。

## 8. 建议修复顺序

### 阶段 A：立即止血

1. MinIO 改私有，关闭伪脱敏和证件自动快捷通道。
2. 关闭非本地环境 debug SMS，修正管理员 bootstrap，轮换工作区凭据。
3. AI 服务取消公网暴露并增加服务鉴权。

### 阶段 B：建立状态机和事务边界

1. 以 `docs/architecture/interaction-logic-model.md` 的迁移表为评审基线。
2. 增加活动认领、match pair、handover 的数据库唯一性保障。
3. 对认领创建、审批、关闭、交接确认使用行锁/CAS 和显式事务。
4. 增加 claim 的取消/终止语义，统一拒绝、关闭、注销的级联处理。

### 阶段 C：修复 P0 用户旅程

1. 接通发布后匹配任务和通知。
2. 修复 `matchId` 深链、通知 MATCH 跳转、匹配方向和旧匹配失效。
3. 补齐搜索地点、状态、事件时间和 URL 状态。
4. 统一认领表单校验、上传状态和页面四态。

### 阶段 D：补齐后台治理

1. 举报目标详情、违规下架、处罚和日志同事务。
2. 申诉队列和复核详情。
3. 审批 CAS、二次确认、逐行 loading 和冲突刷新。
4. 公告用户可见性及生命周期。

### 阶段 E：用测试证明闭环

1. Playwright 覆盖两个用户和一个管理员的完整 P0 流程。
2. MySQL 下运行并发认领、并发审批、并发双确认测试。
3. MinIO 私有对象与短时 URL 越权测试。
4. OpenAPI/共享枚举契约测试。
5. 更新验收清单，只勾选真实浏览器端到端通过的条目。
