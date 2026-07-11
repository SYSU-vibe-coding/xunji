# 剩余 P1/P2 只读审计报告（2026-07-11）

## 1. 审计说明

| 项目 | 内容 |
| --- | --- |
| 审查基线 | `708f011 chore: 添加演示图片` |
| 审查范围 | `frontend/`、`backend/`、`ai-service/`、`deploy/`、CI、迁移、测试与文档 |
| 审查方式 | 静态只读审查，不修改代码 |
| P0 结论 | 未发现新的明确代码级 P0 |
| P1 数量 | 26 项 |
| P2 数量 | 31 项 |

严重度定义：

- P1：常见流程断链、明显数据或安全风险，或真实上线前必须处理的问题，但当前课程主流程存在绕行方案。
- P2：低概率并发风险、可维护性、性能、可访问性、可观测性、工程化和扩展性问题。

本报告排除：

- 已在 `full-code-audit-2026-07-11.md` 中发现且已修复的问题。
- 本地 `.env`、API Key 和未提交的作业要求文件内容。
- 单纯需要真实环境复核、但没有可定位代码或配置缺陷的事项。

## 2. 剩余 P1

### 2.1 安全、身份与敏感数据

| ID | 问题 | 证据 | 影响 | 最小建议 |
| --- | --- | --- | --- | --- |
| P1-01 | 敏感检测对包含 `NONE` 的歧义回复可能直接判定安全 | `ai-service/app/services/sensitive.py:33-67` | 模型回复同时包含敏感标签和 NONE 时，可能解除图片保护 | 使用严格结构化单值响应；多标签、解释文本或歧义一律 fail closed |
| P1-02 | 生产路径没有真实短信 Provider | `backend/app/user/deps.py:8-9`、`backend/app/user/service.py:64-72` | 关闭演示白名单后，新用户无法注册或验证码登录 | 实现 SMS Provider Adapter 并通过依赖注入；开发 Sender 与生产 Sender 隔离 |
| P1-03 | OTP、发送冷却和消费状态保存在进程内存 | `backend/app/user/service.py:36-89,149-165` | 多 worker、重启和并发请求下验证码不一致，冷却可绕过 | 使用 Redis/数据库保存哈希 OTP、TTL、冷却、失败次数并原子消费 |
| P1-04 | 登录、短信和验证码缺少账号/IP/设备限流 | `backend/app/user/router.py:24-48`、`backend/app/core/security.py:20-37` | 撞库、短信额度滥用；同步 PBKDF2 可阻塞事件循环 | 网关/Redis 限流与失败退避；密码校验放线程池；记录安全事件 |
| P1-05 | 参数校验日志和错误响应可能保留密码、OTP 等原始 input | `backend/app/core/exceptions.py:21-76` | 日志平台可能保存认证信息和个人数据 | 错误只保留 `loc/type/msg` 白名单字段，移除 input、body 和敏感 ctx |

### 2.2 用户、认证与积分

| ID | 问题 | 证据 | 影响 | 最小建议 |
| --- | --- | --- | --- | --- |
| P1-06 | 已认证用户可再次申请并再次获得认证积分 | `backend/app/user/service.py:296-320`、`backend/app/admin/service.py:71-87` | 可反复获得 +20 分并覆盖实名资料 | APPROVED 禁止普通重提；身份变更走独立复核；认证积分增加用户级一次性约束 |
| P1-07 | 禁用用户的发布内容和已有匹配仍公开 | `backend/app/user/service.py:246-256`、`backend/app/item/repository.py:101-106,280-285` | 其他用户可看到但无法认领，形成死入口 | 禁用事务中失效匹配；公共查询过滤非 ACTIVE 发布者；恢复后按需重算 |
| P1-08 | 积分规则仍缺少三个业务触发 | `backend/app/credit/schemas.py:4-13`、`backend/app/job/service.py:10-29` | 发布招领奖励、拒绝后未申诉、拾获者超时扣分只存在于文档/枚举 | 发布事务实现 +3 和日上限；两条延迟规则进入可重试定时任务 |

### 2.3 发布、认领与交接状态机

| ID | 问题 | 证据 | 影响 | 最小建议 |
| --- | --- | --- | --- | --- |
| P1-09 | 发布幂等仍是“先查再插”，且重复指纹未真正比较事件时间 | `backend/app/item/service.py:95-122,448-480`、`backend/app/item/repository.py:152-169,354-370` | 并发双击可产生重复记录；不同事件时间的合法记录可能被误拦截 | 客户端幂等键 + 数据库原子占用；业务指纹纳入事件时间 |
| P1-10 | 缺少认领者取消、超时释放和交接重排/取消 | `backend/app/claim/router.py:64-120`、`backend/app/claim/service.py:466-500` | found 可能长期卡在 CLAIMING，双方无法继续或注销 | 增加 cancel、timeout、reschedule/cancel handover 状态迁移和终止原因 |
| P1-11 | 可以在约定交接时间前立即双确认并获得积分 | `backend/app/claim/service.py:481-610` | 协作账号可虚假交接、刷积分 | 确认时校验交接时间并设置小幅容差；异常提前确认进入审计 |
| P1-12 | 交接完成后未失效同一物品的其他活动匹配 | `backend/app/claim/service.py:548-590`、`backend/app/match/repository.py:120-155` | 其他用户仍看到已经不可认领的旧匹配 | 结案事务中将同 found/lost 的其他 NEW/READ 匹配置为 EXPIRED |
| P1-13 | 多个关键流程持有行锁时调用 MinIO 或 AI | `backend/app/claim/service.py:81-131`、`backend/app/item/service.py:320-333`、`backend/app/job/runner.py:107-117` | 外部延迟放大为数据库锁等待、超时和死锁 | 事务外获取快照和执行外部计算，短事务内用版本/CAS 落库 |

### 2.4 AI 与匹配可靠性

| ID | 问题 | 证据 | 影响 | 最小建议 |
| --- | --- | --- | --- | --- |
| P1-14 | Backend 与 AI 默认超时预算互相矛盾 | `backend/app/core/config.py:65-68`、`ai-service/app/core/config.py:42-44`、`image_fetcher.py:18-21` | 真实模型请求容易被 Backend 提前放弃，AI 仍继续消耗额度 | 定义统一端到端 deadline；为 durable AI 任务配置独立预算并传播剩余时间 |

### 2.5 用户端与管理端流程

| ID | 问题 | 证据 | 影响 | 最小建议 |
| --- | --- | --- | --- | --- |
| P1-15 | 管理端在 320～880px 下基本不可用 | `admin-web/src/components/AdminSidebar.vue:68-78`、`AdminLayout.vue:47-59` | 固定 232px 侧栏挤压主内容，移动端无法完成审核 | 移动端隐藏侧栏，使用顶栏按钮 + Drawer；表格提供横向滚动或卡片模式 |
| P1-16 | 用户端时间范围面板在 320px 下可能达到 646px | `PublishLostView.vue:117-126`、`SearchView.vue:352-361`、`MyItemsView.vue:593-602` | 小屏可能无法选择结束时间或确认，阻断发布/搜索/编辑 | 移动端拆成两个独立 datetime picker，或将范围面板改为单列 |
| P1-17 | 内容审核详情存在旧请求覆盖新目标 | `admin-web/src/views/ContentReviewView.vue:102-115,388-403` | 快速点击时可能审核错误物品 | selected ID + latest request guard/AbortController；响应 ID 不匹配则丢弃 |
| P1-18 | “我的发布”详情存在异步串线 | `user-app/src/views/profile/MyItemsView.vue:256-289,456-468` | URL 已切到 B，抽屉却显示 A，编辑/关闭可能作用于错误记录 | 使用 `loadingTargetId` 和请求序号，只合并同 ID 请求 |
| P1-19 | 搜索结果存在旧响应覆盖新筛选 | `user-app/src/views/SearchView.vue:55-96,184-190` | URL/控件与列表、总数可能来自不同筛选条件 | 请求序号或 AbortController；只有最新请求能修改状态 |
| P1-20 | 管理员权限撤销后不一定结束会话 | `admin-web/src/api/http.ts:23-45,97-129` | 旧 profile 继续放行路由，后台页面持续报错 | 将 48002/管理员禁止错误视为后台会话失效并退出 |
| P1-21 | 用户 profile 恢复失败会进入 `profile=null` 半登录态 | `user-app/src/stores/auth.ts:52-65`、`AppLayout.vue:15-20` | 本人物品可能被判为他人，显示错误操作按钮 | 增加全局 session 初始化 loading/error/retry，未确认身份前不渲染权限操作 |
| P1-22 | 公告草稿无法重新查看全文和编辑 | `admin-web/src/views/AnnouncementView.vue:76-80,183-229` | 草稿只能盲目发布或永久搁置 | 增加详情/编辑入口和更新 API；短期不能支持则移除草稿承诺 |
| P1-23 | 内容审核没有默认待审核队列和状态筛选 | `admin-web/src/views/ContentReviewView.vue:75-89,213-230` | PENDING 被大量历史记录淹没 | 查询契约增加 reviewStatus，默认 PENDING，提供已处理历史筛选 |
| P1-24 | 历史物品仍显示服务端禁止的编辑/删除动作 | `MyItemsView.vue:739-770`、`ItemDetailView.vue:334-355` | 用户完成表单和上传后才收到冲突 | 建立前端 capability matrix，或由详情 API 返回 canEdit/canDelete/canClose |
| P1-25 | 认证图片 nullable 契约被 shared 和管理端收窄 | `shared/src/types/user.ts:69-75`、`shared/src/types/admin.ts:31-40` | 图片不可用时仍显示查看与审批按钮 | 类型改为 `string | null`；缺图时明确提示并禁止普通审批 |
| P1-26 | 删除现有头像后仍保留旧头像 | `ImageUploader.vue:105-110`、`ProfileView.vue:40-60` | 页面提示成功，但 avatarRef 被省略，服务端不清空 | 使用 `avatarRef: string | null` 或 clearAvatar 显式清空契约 |

## 3. 剩余 P2

### 3.1 并发、数据与任务

| ID | 问题 | 证据 | 建议 |
| --- | --- | --- | --- |
| P2-01 | 聚合流程锁顺序仍不完全一致，死锁后没有事务重试 | user/claim/item service 多条锁路径 | 定义全局锁顺序；对 MySQL deadlock/serialization failure 做有限整事务重试 |
| P2-02 | 凭证补交接受超出契约的状态并可重复追加同一引用 | `backend/app/claim/service.py:323-345` | 明确补充材料语义；限制状态并对 claim + assetRef 去重/覆盖 |
| P2-03 | 多个分页列表存在 N+1 查询 | item/claim/match service 列表转换逻辑 | 批量加载图片、用户、问题、举报计数和活动认领 |
| P2-04 | 全量匹配仍是无界 O(L×F) 且逐 pair 调用 AI | `backend/app/match/jobs.py:237-325` | 类别/时间/地点候选召回，缓存向量，提供批量评分与熔断 |
| P2-05 | 匹配缺少模型、算法、输入版本和评分历史 | `backend/app/match/models.py:19-31` | 增加 modelName、algorithmVersion、scoredAt、inputVersion 和历史记录 |
| P2-06 | Durable FAILED 没有管理列表、告警和安全重试入口 | `backend/app/job/runner.py:128-155` | 管理员任务页、错误分类、积压指标和带版本检查的 retry |
| P2-07 | 管理员全量匹配仍是进程内任务 | `backend/app/match/jobs.py:47-109` | 持久化任务和租约，多 worker 单实例执行，停机等待任务 |
| P2-08 | 公告发布在一个 HTTP 事务内同步 fan-out | `backend/app/admin/service.py:503-552` | 公告 + outbox 同事务，后台分片通知并增加幂等约束 |
| P2-09 | 对象存储没有资产绑定状态和孤儿文件 GC | `backend/app/core/object_storage.py:84-117` | 建立资产表、引用状态和保留期，定时清理未绑定/零引用对象 |
| P2-10 | 普通图片预签名 URL 下架后最长 7 天仍有效 | `backend/app/core/config.py:49-50` | 缩短签名时间；高撤权场景使用鉴权代理或可撤销 token |
| P2-11 | 多数核心关系没有数据库外键 | 0001/0002 迁移、claim/match models | 审计孤儿数据后逐步增加 FK 与明确删除策略 |
| P2-12 | 数据库密码直接拼进 URL | `backend/app/core/config.py:20-26` | 使用 SQLAlchemy `URL.create()`，增加特殊字符密码测试 |

### 3.2 业务契约与时间

| ID | 问题 | 证据 | 建议 |
| --- | --- | --- | --- |
| P2-13 | `USER` 举报枚举与实现不一致 | `docs/architecture/enums.md:118-124`、item schemas | 不支持则移除枚举；支持则补目标详情、处罚与测试 |
| P2-14 | `PHONE` 联系偏好没有实际联系方式能力 | item/claim detail response | 仅 APPROVED 后提供临时/脱敏联系方式或站内转接 |
| P2-15 | 认证审核和公告发布时间混用 UTC naive 与北京墙钟 | user/admin service 与 common utils | 统一全项目 UTC 或北京墙钟策略，禁止混写 |
| P2-16 | BizError 仍统一 HTTP 200，请求 ID 未跨服务传播 | exceptions/response/ai_client | 映射标准 HTTP 状态；增加 request context 中间件并透传 AI |
| P2-17 | 认证申请没有 realName 快照 | user cert model/service | 申请表保存姓名快照，历史列表读取申请值 |

### 3.3 前端可访问性、性能与测试

| ID | 问题 | 证据 | 建议 |
| --- | --- | --- | --- |
| P2-18 | 部分卡片、账户菜单和表格行不是键盘可操作元素 | MyClaims、AdminHeader、Dashboard | 改用 RouterLink/button，表格行内提供真实操作 |
| P2-19 | SPA 路由切换不更新标题或移动焦点 | 两端 router/layout | route meta title、afterEach 更新标题、main 焦点和 skip link |
| P2-20 | REPORT 通知显示为按钮但没有目标页面 | interaction.ts、NotificationsView | 无目标时渲染为非按钮，或增加“我的举报”详情页 |
| P2-21 | AdminLayout 使用 fullPath 作为 key | `admin-web/src/layouts/AdminLayout.vue:23-28` | 使用 route name/path，query 由页面 watcher 处理 |
| P2-22 | Element Plus 全量 CSS 和静态资源缓存策略不足 | 两端 main/vite/nginx | 按组件引入样式；assets immutable、index no-cache、gzip/Brotli |
| P2-23 | 图片没有 lazy loading、async decoding 和缩略尺寸 | ItemCard、ItemDetail、MyItems | 增加原生懒加载，后端提供缩略图/srcset |
| P2-24 | 认证字段和图片 MIME 前端预检不足 | CertificationView、ImageUploader | 表单规则对齐后端；MIME 预检和内联错误 |
| P2-25 | 管理端不遵守 reduced-motion | admin global.scss | 复用用户端 reduced-motion 全局规则 |
| P2-26 | 前端缺少组件测试和 Playwright | 两端 package/tests | Vue Test Utils + Playwright，覆盖 Dock、消息 Tab、竞态、上传和管理审核 |

### 3.4 部署、安全与可观测性

| ID | 问题 | 证据 | 建议 |
| --- | --- | --- | --- |
| P2-27 | Production secret 仍依赖环境变量，MinIO 使用 root 凭据 | compose | Podman/Docker secrets；拆分 MinIO root 与 bucket-scoped service account |
| P2-28 | 健康检查不覆盖 DB/MinIO，Podman host 缺完整 readiness | compose 与 health endpoints | liveness/readiness 分离，增加 DB/MinIO/AI 探针与 service_healthy |
| P2-29 | 缺少结构化日志、指标、告警、日志轮转和 trace | response/exceptions/compose | request ID、结构化脱敏日志、任务积压/降级率指标和容量控制 |
| P2-30 | GitHub Actions 有 Node 20 弃用和缓存警告 | `.github/workflows/ci.yml` | 升级 action major，验证 cache key 和权限 |
| P2-31 | 容器仍以 root 运行，基础镜像未锁 digest | 四个 Dockerfile | 非 root、只读 rootfs、cap_drop、SBOM、漏洞扫描、镜像 digest |

## 4. 上线部署专项 P1

以下属于 P1 中与真实部署直接相关的问题，应在公开部署前单独关闭：

| 问题 | 证据 | 当前状态 |
| --- | --- | --- |
| Production overlay 默认浏览器 MinIO 地址不可达 | `docker-compose.production.yml`、`MINIO_PUBLIC_BASE_URL` | 需要统一 HTTPS 网关或后端鉴权下载 |
| Production overlay 仍直接暴露 HTTP Backend/前端，没有 TLS | production/base compose | 需要只公开 443，内部化 Backend/AI/MinIO |
| Podman host 模式 Nginx upstream 替换字符串不匹配 | `docker-compose.podman-host.yml:102-117` | host-network 回退路径可能 502 |
| Nginx 默认 1 MiB 与 10 MiB 上传契约冲突 | 两端 `nginx.conf` | 需要统一设置 11～12 MiB |
| 0007 举报去重迁移可能删除已处理记录且不迁移引用 | `20260711_0007_report_unique_target.py:19-43` | 应人工核对或按状态优先迁移 |
| 缺少可执行备份/恢复与迁移单实例流程 | compose、deploy scripts、迁移文档 | 当前只写“部署前备份”，没有恢复演练 |
| CI 未覆盖 MySQL、MinIO、并发、完整容器和浏览器 P0 | CI 与 tests | 当前绿色 CI 不能证明真实部署闭环 |

## 5. 推荐处理顺序

### 阶段 A：安全与数据正确性

1. 敏感检测严格结构化解析。
2. 参数校验日志脱敏。
3. 提前交接刷分和重复认证奖励。
4. 交接完成后其他匹配失效。
5. 0007 举报迁移安全合并。

### 阶段 B：移动端和常见流程

1. 管理端移动导航。
2. 用户端移动时间范围控件。
3. 内容详情、我的发布和搜索请求竞态。
4. 认领取消、超时释放和交接重排。
5. 草稿编辑、待审核队列和 capability matrix。

### 阶段 C：生产可部署性

1. 统一 HTTPS 网关与 Production MinIO 访问方案。
2. 修复 Podman host upstream 和 Nginx 上传限制。
3. 接入真实 SMS、集中式 OTP 和限流。
4. 统一 AI 端到端 deadline。
5. 提供迁移、备份和恢复脚本及演练记录。

### 阶段 D：质量门禁和运维

1. MySQL/MinIO 集成与并发测试。
2. Playwright 双用户 + 管理员 P0 流程。
3. Durable Job 管理、指标和告警。
4. N+1、候选召回、批量 AI 和静态资源优化。
5. Secret、镜像、容器权限和文档真实性清理。

## 6. 验收口径

问题只有在同时满足以下条件时才应从本报告移除：

1. 代码或配置修复已经合并。
2. 对应单元/组件/集成测试已加入。
3. CI 中执行该测试且通过。
4. 涉及 MySQL、MinIO、容器或浏览器的事项有真实环境证据。
5. API、枚举、架构和验收文档同步更新。
