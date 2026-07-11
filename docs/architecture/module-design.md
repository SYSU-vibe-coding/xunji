# 模块设计

## 1. 总体模块划分

系统划分为四个一级模块：

1. 用户端前端模块
2. 管理端前端模块
3. 主业务后端模块
4. AI 辅助服务模块

## 2. 前端模块设计

### 2.1 用户端页面模块

| 模块 | 页面/能力 | 说明 |
| --- | --- | --- |
| 认证模块 | 登录页、注册页、身份认证页 | 处理用户登录、资料提交 |
| 首页模块 | 首页、搜索、筛选、推荐列表 | 承载浏览和检索入口 |
| 发布模块 | 失物发布、招领发布 | 表单填写、图片上传、校验 |
| 认领模块 | 匹配详情、认领申请、验证流程 | 承载认领主流程 |
| 消息模块 | 通知中心、未读提醒 | 展示系统事件通知 |
| 个人中心 | 资料、积分、我的发布、我的认领 | 用户自助管理 |

### 2.2 管理端页面模块

| 模块 | 页面/能力 |
| --- | --- |
| 身份认证管理 | 认证申请列表、详情、审批 |
| 内容审核 | 失物/招领内容审核、敏感内容处理 |
| 举报处理 | 举报列表、处理记录 |
| 公告管理 | 公告发布、长期未领清单 |
| 数据统计 | 用户数、发布量、找回率、处理时长 |

## 3. 主后端模块设计（FastAPI）

### 3.1 模块清单

每个模块是 `app/` 下的一个 Python 包，结构固定为 `router / service / repository / models / schemas / deps`。

| 模块 | 职责 |
| --- | --- |
| `core` | 配置加载、日志、鉴权依赖、全局异常处理、启动钩子 |
| `common` | 统一响应、分页、业务异常基类、通用工具 |
| `db` | `Base`、`engine`、`AsyncSession` 工厂、ULID 生成 |
| `user` | 注册登录、个人资料、身份认证、角色管理 |
| `item` | 失物发布、招领发布、搜索筛选、状态变更、文件上传 |
| `job` | `durable_jobs` outbox、任务领取、退避重试、lifespan runner |
| `match` | 匹配任务触发、结果存储、匹配列表查询 |
| `claim` | 认领申请、问答验证、凭证审核、交接流程 |
| `credit` | 信誉积分计算、流水记录、权限限制 |
| `notification` | 站内消息、公告、未读统计 |
| `admin` | 审核、举报处理、统计查询、后台管理能力 |

### 3.2 分层职责

| 层 | 职责 | 可调用 |
|---|---|---|
| `router.py` | 路径定义、入参校验（pydantic）、权限依赖、调用 service、返回 Schema | `service`、`schemas` |
| `service.py` | 业务规则、事务控制（`async with session.begin()`）、跨模块编排 | 本模块 `repository`、其他模块 `service` |
| `repository.py` | 纯 SQLAlchemy 访问，不含业务判断 | `models`、`session` |
| `models.py` | SQLAlchemy ORM 声明 | — |
| `schemas.py` | pydantic DTO（Request/Response/Internal） | — |
| `deps.py` | 模块专属 FastAPI 依赖 | `service` |

### 3.3 模块调用关系

- `item` 发布/编辑事务 → 同事务写入版本化 `durable_jobs`；提交后的 `BackgroundTasks` 只唤醒 runner
- `job.runner` 领取 `MATCH` / `CLASSIFY` / `SENSITIVE`，通过业务 service 执行且不允许内部提交
- `match.service` 通过 httpx 调 AI 服务计算得分，将 `match_results` 与通知原子写入
- `claim.service` 使用 `match` 结果发起认领申请
- `claim.service` 完成后调用 `notification.service` 和 `credit.service`
- `admin` 跨模块读取数据，必须通过对应模块的 `service`，**不得绕过访问 repository**

### 3.4 模块间硬约束

- `router` 不直接 import `repository` 或 `session`，必须经 `service`
- 跨模块只 import `service` 和 `schemas`，**禁止 import 其他模块的 `repository` / `models`**
- 枚举状态统一在 `service` 层转换，`router` 不处理业务枚举转换
- 关键状态变更必须记录 `operation_logs`
- 路由全部 `async def`；DB 会话用 `AsyncSession`

## 4. AI 服务模块设计

### 4.1 子能力拆分

| 子模块 | 职责 |
| --- | --- |
| 分类模块 | 识别物品类别并生成候选标签 |
| 图像特征模块 | 生成图片特征向量 |
| 文本匹配模块 | 计算文本语义相似度 |
| 综合评分模块 | 合成图像、文本、时间、地点得分 |
| 敏感信息处理模块 | 检测证件类物品并输出脱敏建议 |

### 4.2 与主后端协作方式

- 主后端通过 `httpx.AsyncClient` 调用 AI 服务
- AI 服务不直接连接主业务数据库
- AI 服务返回纯计算结果，不持久化业务状态
- AI 失败时主后端必须支持降级（见 `matching-rules.md §2`）

## 5. 代码组织约定

### 5.1 主后端目录

```text
backend/
  pyproject.toml
  uv.lock
  alembic.ini
  alembic/
    env.py
    versions/
  app/
    main.py
    core/
    common/
    db/
    user/
      __init__.py
      router.py
      service.py
      repository.py
      models.py
      schemas.py
      deps.py
    item/
    match/
    claim/
    credit/
    notification/
    admin/
  tests/
    unit/
    integration/
    conftest.py
```

### 5.2 AI 服务目录

```text
ai-service/
  pyproject.toml
  uv.lock
  app/
    main.py
    routers/
      classify.py
      sensitive.py
      match.py
    services/
    models/            # 模型加载与推理封装
    schemas.py
  tests/
```

### 5.3 前端目录

```text
frontend/user-app/
  src/
    pages/
    components/
    api/
    stores/          # Pinia
    router/
    utils/
    styles/

frontend/admin-web/
  src/
    views/
    components/
    api/
    stores/
    router/
```
