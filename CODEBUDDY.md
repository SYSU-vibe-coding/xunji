# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## 项目概览

校园失物招领平台"寻迹"（Xunji），软件工程课程五人团队项目，定位是**可演示的 demo**，重点在开发过程的标准化（类型、lint、测试、CI、文档齐备）。

技术栈：

- **用户端** `frontend/user-app/` — Vue 3 + Vite + Pinia（移动优先网页，浏览器直接访问，不做小程序）
- **管理后台** `frontend/admin-web/` — Vue 3 + Vite + Pinia（PC）
- **前端共享** `frontend/shared/` — API 类型、常量、请求封装
- **主后端** `backend/` — Python 3.12 + **FastAPI** + **SQLAlchemy 2.x (async)** + **Alembic**，包管理用 **uv**
- **AI 服务** `ai-service/` — Python + FastAPI，负责图像/文本匹配与敏感检测，独立进程
- **数据层** MySQL + MinIO
- **部署** `deploy/` — docker-compose、环境模板、脚本

**重要**：当前仓库只提交了少量占位文件。以 `backend/` 为例，目前只有 `pyproject.toml` 和 `README.md`；`app/`、`alembic/`、`tests/`、`uv.lock` 尚未入库。下面的目录结构和命令是初始化/补脚手架时必须遵循的约定，不代表这些文件现在已经存在。

## 按任务读文档

| 任务 | 必读文件 |
|---|---|
| 写后端接口 | `docs/api/conventions.md` + `docs/api/<模块>.md` + `docs/architecture/enums.md` |
| 写数据库模型 / 迁移 | `docs/architecture/database-design.md` + `docs/architecture/enums.md` |
| 写匹配 / 认领 / 积分逻辑 | `docs/architecture/matching-rules.md` + `docs/architecture/credit-rules.md` |
| 改业务流程 | `docs/architecture/core-flow-design.md` |
| 写 AI 服务 | `docs/api/ai-service.md` + `docs/architecture/matching-rules.md` |
| 写前端页面 | `docs/architecture/module-design.md` + 对应 `docs/api/<模块>.md` |
| 写测试 | `docs/testing/test-cases.md` + `docs/testing/acceptance-checklist.md` |
| 新增/修改枚举或错误码 | `docs/architecture/enums.md` + `docs/api/conventions.md` |
| 判断需求是否在范围内 | `docs/project-management/requirements-baseline.md` |

## 常用命令（脚手架落库后执行；初始化时遵循此约定）

### 主后端（`backend/`，FastAPI + uv）

若当前还没有 `app/`、`alembic/` 或 `tests/`，先按本文后面的“后端目标包结构”补齐脚手架，再执行启动 / 迁移 / 测试命令。

```bash
cd backend

# 环境
uv sync                                                  # 安装 / 同步依赖（根据 pyproject.toml + uv.lock）
uv run uvicorn app.main:app --reload --port 8080         # 本地启动
uv run python -m app.cli <command>                       # 如有自定义 CLI

# 数据库迁移（Alembic）
uv run alembic upgrade head                              # 应用最新迁移
uv run alembic revision --autogenerate -m "add xxx"      # 自动生成迁移
uv run alembic downgrade -1                              # 回滚一步

# 测试
uv run pytest                                            # 全部
uv run pytest tests/unit/claim/test_service.py           # 单文件
uv run pytest tests/unit/claim/test_service.py::test_handover_confirm  # 单用例
uv run pytest -k "claim and not slow"                    # 表达式过滤
uv run pytest --cov=app --cov-report=term-missing        # 覆盖率

# 质量
uv run ruff check .                                      # lint
uv run ruff format .                                     # 格式化
uv run mypy app                                          # 类型检查
```

### AI 服务（`ai-service/`，FastAPI + uv）

若 `ai-service/` 仍只有占位 `README`，先按 `docs/architecture/module-design.md §5.2` 搭骨架，再执行下列命令。

```bash
cd ai-service
uv sync
uv run uvicorn app.main:app --reload --port 5000
uv run pytest
uv run pytest tests/test_match.py::test_score
uv run ruff check .
```

### 用户端（`frontend/user-app/`）与管理后台（`frontend/admin-web/`）

```bash
cd frontend/user-app      # 或 frontend/admin-web
pnpm install
pnpm dev                   # 本地开发
pnpm build                 # 生产构建
pnpm test:unit -- FileName # 单测过滤
pnpm lint
```

### 本地联调（`deploy/`）

仅在 `deploy/docker/` 下的 compose 文件已提交后执行。

```bash
cd deploy
docker compose up -d mysql minio    # 仅启动依赖
docker compose up -d                # 启动全部服务
```

## 硬性规则（违反必返工）

### 通用
1. **枚举值**只使用 `docs/architecture/enums.md` 中定义的，不自创中文状态、不自造英文码
2. **时间格式**：请求/响应 body 中统一 `yyyy-MM-dd HH:mm:ss`（北京时间）；顶层 `timestamp` 用 ISO 8601
3. **JSON 字段** `camelCase`，**数据库字段** `snake_case`；ORM 模型与 pydantic Schema **绝不复用同一个类**
4. **状态变更**必须写 `operation_logs`
5. **敏感图片原图**不返回前端，只返回 `masked_image_url`
6. **接口返回结构**遵守 `docs/api/conventions.md §4` 的 `{code, message, data, requestId, timestamp}`
7. **字段/枚举/状态变更**先改文档再改代码
8. **AI 服务失败**不得使主后端事务回滚，按 `docs/api/ai-service.md` 降级

### Python 专属
9. **分层**：`router` 只负责入参校验和调用 `service`；`service` 持业务逻辑并调用 `repository`；`repository` 是 SQLAlchemy 访问层。**router 不得直接 import repository 或 session**
10. **跨模块**：A 模块只能 import B 模块的 `service` 或 `schemas`，**禁止 import 其他模块的 `repository` / `models`**
11. **全异步**：路由用 `async def`，DB 用 `AsyncSession`，HTTP 用 `httpx.AsyncClient`；禁止在 async 上下文里写阻塞 IO
12. **事务边界**：涉及多表写入（典型如 `claim/handover/confirm`）必须 `async with session.begin():` 显式包裹；禁止依赖隐式提交
13. **DTO/ORM 分离**：pydantic `BaseModel` 做入参出参，SQLAlchemy `DeclarativeBase` 做持久化；**禁止把 ORM 对象直接返回给路由**，必须用 `model_validate` 转成 Schema
14. **类型注解强制**：公共函数、方法、返回值必须标注类型；`mypy app` 不得有错
15. **ID 策略**：所有业务主键用 **ULID**（字符串，26 位），不用自增也不用雪花。入库前在 service 层生成

## 架构关键点（需串多个文件才能建立的全局观）

- **单体后端 + 独立 AI 服务**：主后端是 FastAPI 模块化单体，AI 服务是独立 Python 进程，两者通过 HTTP 调用（前缀 `/internal/ai`，见 `docs/api/ai-service.md`）。AI 服务不连业务数据库，调用失败时主后端按规则降级完成发布，不得回滚主事务。
- **匹配异步**：发布接口返回 200 后用 FastAPI `BackgroundTasks` 或 worker 触发匹配任务，不阻塞用户。综合评分权重固定为 `0.4×图像 + 0.3×文本 + 0.2×地点 + 0.1×时间`，阈值 70 / 高优先级 90，详见 `docs/architecture/matching-rules.md §1-3`。
- **认领状态机是业务核心**：`PENDING → ANSWER_PASSED → PROOF_PENDING → APPROVED → HANDED_OVER`（另有 `REJECTED`、`APPEALING` 支线）。验证等级由物品类别 + 用户信誉动态决定（`matching-rules.md §5`），其中 `FAST_TRACK` 专供敏感证件走 OCR 自动比对实名信息。
- **交接是事务边界**：`POST /claims/{id}/handover/confirm` 双方都确认时，一个 `async with session.begin():` 内完成：更新认领状态、同步关闭失物/招领、写积分流水、发通知。任一步 raise 整体回滚（见 `docs/api/claim.md` 末尾）。
- **敏感物品分层展示**：`found_items.is_sensitive = 1` 的物品前端**只**返回 `masked_image_url`，原图仅 ADMIN 和归属方可访问，对象存储 URL 签名有效期压到 1 小时。
- **信誉积分双写**：积分变动必须与业务状态在同一事务内写入，并同步落 `credit_logs`，去重依赖 `(user_id, biz_type, biz_id, reason_code)` 唯一索引（`credit-rules.md §5`）。

## 后端目标包结构（初始化完成后）

```
backend/
  pyproject.toml
  uv.lock
  alembic.ini
  alembic/
    env.py
    versions/           # 迁移脚本
  app/
    main.py             # FastAPI 应用工厂 & 路由注册
    core/               # 配置、日志、依赖注入、鉴权、全局异常
    common/             # 通用响应、分页、异常类、工具
    db/                 # Base、engine、session、ULID 生成
    user/               # 用户、认证
      router.py
      service.py
      repository.py
      models.py         # SQLAlchemy ORM
      schemas.py        # pydantic DTO
      deps.py           # 模块级依赖（如 get_current_user）
    item/               # 失物、招领、搜索、上传
    match/              # 匹配任务与结果
    claim/              # 认领、问答、凭证、交接
    credit/             # 信誉积分
    notification/       # 站内消息
    admin/              # 后台、举报、公告、统计
  tests/
    unit/<module>/
    integration/
    conftest.py
```

## 分支与提交（摘自 `CONTRIBUTING.md`）

- 分支：`main` / `develop` / `feature/<name>` / `fix/<name>`
- 提交格式示例：
  - `feat(FR-02): add lost item publish api`
  - `fix(FR-05): correct claim review status transition`
  - `docs: update database model`
- 每个 PR 单一聚焦；接口 / 数据库 / 流程变更必须同步更新文档

## 提交前自检

- [ ] `uv run ruff check .` 通过
- [ ] `uv run mypy app` 通过
- [ ] `uv run pytest` 通过
- [ ] 新增/修改枚举值已写入 `docs/architecture/enums.md`
- [ ] 新增/修改接口已更新对应 `docs/api/*.md` 字段表
- [ ] 数据库字段变更：新增 `alembic/versions/` 迁移 + 更新 `docs/architecture/database-design.md`
- [ ] 提交信息遵守 `CONTRIBUTING.md`，关联 FR 编号

## 跳过阅读（非 AI 相关）

`docs/project-management/` 下除 `requirements-baseline.md` 外（风险、WBS、排期）主要给人读，写代码时跳过。
