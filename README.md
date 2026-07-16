# 寻迹 Xunji

> 校园失物招领平台 · 软件工程课程五人团队项目
>
> 一个结构清晰、核心流程完整、**可演示、可测试、可部署**的课程项目版本。通过「发布 → 匹配 → 验证 → 交接 → 归档」闭环提升校园失物找回效率，并降低冒领和隐私泄露风险。

**仓库地址**：<https://github.com/SYSU-vibe-coding/xunji>

---

## 一、项目功能一览

本项目按 P0 / P1 / P2 三档优先级组织，**P0/P1 主体已落地实现**，可在演示中完整跑通。

### 用户端（移动优先网页，`frontend/user-app/`）

| 模块 | 功能 | 优先级 |
| --- | --- | --- |
| 账号 | 手机号注册、密码登录、个人资料维护、注销账号 | P0 |
| 实名认证 | 提交校园身份认证资料，等待管理员审批 | P0 |
| 失物发布 | 填写名称、类别、时间、地点、描述、多图上传 | P0 |
| 招领发布 | 填写物品信息、设置保管方式与最多 3 个验证问题 | P0 |
| 物品搜索 | 按类别、状态、地点、时间排序筛选 | P0 |
| 匹配结果 | 自动/手动触发生成匹配列表，按综合得分排序展示 | P0/P1 |
| 认领与验证 | 发起认领 → 一级问答验证 → 凭证上传 → 管理员/拾获者审核 | P0/P2 |
| 交接确认 | 双方各自确认，事务内自动关闭失物/招领记录、结算信誉积分 | P0 |
| 申诉 | 认领被拒后可发起申诉，由管理员复核 | P2 |
| 站内通知 | 认领进展、审核结果、匹配提醒、公告通知；未读数角标 | P0 |
| 公告中心 | 浏览系统公告列表与详情 | P0 |
| 信誉积分 | 查看个人信誉分与变动流水（归还加分、恶意/超时扣分） | P1 |
| 敏感物品脱敏 | 证件类物品前端只展示模糊图，原图仅管理员与归属方可见 | P1 |

### 管理后台（PC 网页，`frontend/admin-web/`）

| 模块 | 功能 | 优先级 |
| --- | --- | --- |
| 管理员登录 | 独立账号密码登录（首次由环境变量引导创建） | P0 |
| 数据看板 | 发布量、找回率、平均处理时长等统计概览 | P1 |
| 实名认证审批 | 查看认证申请、通过/驳回 | P0 |
| 内容审核 | 审核失物/招领发布内容 | P0 |
| 认领管理 | 查看全部认领记录与详情 | P0 |
| 申诉处理 | 复核认领申诉并裁定 | P2 |
| 举报处理 | 查看用户举报、处置违规内容/用户 | P1 |
| 用户管理 | 查看用户列表、启用/停用账号 | P1 |
| 公告管理 | 发布系统公告 | P0 |
| 匹配监控 | 查看匹配任务与得分来源 | P1 |
| 操作日志 | 查看关键操作审计记录 | P1 |

### AI 辅助服务（独立进程，`ai-service/`）

- **物品图像分类**：辅助发布时自动归类
- **文本/图像相似度计算**：综合评分权重 `0.4×图像 + 0.3×文本 + 0.2×地点 + 0.1×时间`，阈值 70 / 高优先级 90
- **敏感物品检测**：识别证件类物品并返回脱敏标识，失败时 fail-closed（默认视为敏感）
- **未配置 `DASHSCOPE_API_KEY` 时自动降级为规则关键词基线**，无需真实模型即可演示与跑 CI

> AI 服务失败不会回滚主后端事务，按规则降级完成发布。

---

## 二、技术栈

| 层次 | 技术 |
| --- | --- |
| 用户端 / 管理端 | Vue 3 + Vite + Pinia + Element Plus + TypeScript |
| 前端共享 | `frontend/shared/`（API 类型、常量、请求封装） |
| 主后端 | Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Alembic，`uv` 管理依赖 |
| AI 服务 | Python 3.12 + FastAPI，独立进程，HTTP 调用 `/internal/ai/*` |
| 数据层 | MySQL 8 + MinIO 对象存储 |
| 部署 | Docker Compose |
| 质量 | Ruff（lint+format）+ Mypy strict + Pytest + Vitest + GitHub Actions CI |

---

## 三、仓库结构

```
frontend/        前端
  user-app/      用户端网页（dev 5173 / docker 18080）
  admin-web/     管理后台（dev 5174 / docker 18081）
  shared/        前端共享类型与常量
backend/         FastAPI 主后端（dev 8080 / docker 8080）
  app/           业务模块：user item match claim credit notification admin job ...
  alembic/       数据库迁移脚本
  tests/         单元测试（完全离线，无需 MySQL/MinIO）
ai-service/      AI 辅助服务（dev 5000 / docker 5000）
deploy/docker/   Compose 文件与环境模板
docs/            全部文档（索引见 docs/README.md）
CODEBUDDY.md     AI/新成员上手必读的权威规则文件
```

---

## 四、部署与配置教程

提供两种方式：**Docker 一键全栈部署（推荐助教/老师演示使用）** 和 **本地开发模式**。

### 方式 A：Docker 全栈一键部署（推荐）

一次性启动 MySQL、MinIO、AI 服务、主后端、用户端、管理后台六个容器，最贴近演示环境。

#### 1. 前置要求

- Docker 与 Docker Compose（或 Podman + podman-compose）
- 可用内存 ≥ 4GB
- 释放端口：`8080 5000 9000 9001 18080 18081`（默认值，可改）

#### 2. 准备环境变量文件

```bash
cp deploy/docker/.env.example deploy/docker/.env
```

用编辑器打开 `deploy/docker/.env`，**必须填写以下非空随机值**（否则 compose 会报错拒绝启动）：

```dotenv
# 必填：数据库与根密码
MYSQL_ROOT_PASSWORD=<随机强密码>
DB_PASSWORD=<随机强密码>

# 必填：JWT 密钥（建议 ≥ 64 字符随机串）
JWT_SECRET_KEY=<openssl rand -hex 32 生成>

# 必填：首次启动创建的管理员
ADMIN_PASSWORD=<管理员登录密码>

# 必填：MinIO 对象存储密钥
MINIO_SECRET_KEY=<随机强密码>

# 必填：后端调用 AI 服务的服务令牌（≥ 32 字符）
AI_SERVICE_TOKEN=<openssl rand -hex 16 生成>
```

> `.env.example` 已默认开启 `DEBUG=true`、`BOOTSTRAP_ADMIN_ENABLED=true`、`SMS_DEBUG_ENABLED=true`，并预置两个演示手机号 `13800138000,13900139000`，填完密钥即可直接演示，无需额外配置。

#### 3. 可选项说明

- **AI 模型**：`DASHSCOPE_API_KEY` 留空即运行规则关键词基线（演示与 CI 默认使用）。若要启用真实大模型（通义千问 VL / 文本向量），填入 DashScope API Key 并按需设置 `DASHSCOPE_VL_MODEL`、`TEXT_EMBEDDING_MODEL`。
- **手机局域网演示**：若需用手机访问同一台电脑，把 `MINIO_BIND_ADDRESS=0.0.0.0`，并把 `MINIO_PUBLIC_BASE_URL` 改为电脑局域网 IP，例如 `http://192.168.1.20:9000`；用户端用 `http://192.168.1.20:18080` 打开（手机用 `localhost` 会指向手机自身）。
- **端口冲突**：通过 `USER_WEB_PORT`、`ADMIN_WEB_PORT`、`BACKEND_PORT`、`AI_SERVICE_PORT`、`MYSQL_PORT`、`MINIO_API_PORT` 等覆盖默认端口。

#### 4. 启动（两种镜像获取方式任选其一）

启动前需要决定用哪种方式获取四个应用镜像（`backend` / `ai-service` / `user-web` / `admin-web`）。两者最终运行效果一致，区别只在是否需要本地编译。

**方案 ① 拉取预构建镜像（推荐，免编译，约 1 分钟启动）**

我们通过 CI 自动将每次发版的四个应用镜像发布到 GitHub Container Registry（GHCR）。只需在 `.env` 里把 `XUNJI_TAG` 设为已发布版本号，compose 即直接拉取远端镜像，跳过本地编译：

```bash
# 编辑 deploy/docker/.env，添加一行（可用版本见 https://github.com/SYSU-vibe-coding/xunji/pkgs）
XUNJI_TAG=v1.1.1

# 拉取镜像
docker compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml pull

# 启动（无需 --build）
docker compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml up -d
```

适用场景：助教/老师验收、答辩演示、任何想快速跑起来查看功能的环境。无需安装 Node/Python/uv/pnpm 工具链，只要 Docker。

**方案 ② 本地构建镜像（需编译，首次约 10–15 分钟）**

不设置 `XUNJI_TAG`（或留空）时，compose 回退到 `local` 标签并触发本地构建。适合二次开发、改了源码需要即时生效的场景：

```bash
# 确保 .env 中 XUNJI_TAG 留空或未设置
# 构建并启动（首次会编译四个应用镜像）
docker compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml up --build -d
```

如需只构建不启动，可单独执行：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml build
```

> 两种方式的后续操作（查看日志、停止、重置数据）完全相同，见下文。

#### 5. 启动后自动执行的初始化

无论哪种方式，`backend` 容器启动时都会自动执行 `alembic upgrade head` 应用数据库迁移，无需手动建表；`BOOTSTRAP_ADMIN_ENABLED=true` 时会在首次启动时创建管理员账号。

#### 6. 访问入口

| 服务 | 地址 |
| --- | --- |
| 用户端网页 | http://localhost:18080 |
| 管理后台 | http://localhost:18081 |
| 后端健康检查 | http://localhost:8080/health |
| 后端接口文档（Swagger） | http://localhost:8080/docs |
| AI 服务健康检查 | http://localhost:5000/health |
| MinIO 控制台 | http://localhost:9001 |
| MySQL | 127.0.0.1:3306 |

#### 7. 默认账号与演示登录

- **管理员**：账号 `admin`，手机号 `19900000000`，密码为你填写的 `ADMIN_PASSWORD`（首次启动时由 `BOOTSTRAP_ADMIN_ENABLED=true` 自动创建）。
- **演示用户**：用 `13800138000` 或 `13900139000` 注册/登录，会命中演示短信白名单，验证码会在后端日志中输出（不发送真实短信）。
- **安全提醒**：演示完成后请将 `.env` 中的 `BOOTSTRAP_ADMIN_ENABLED` 改回 `false`，避免后续启动重复创建管理员。

#### 8. 重置本地数据

```bash
docker compose -f deploy/docker/docker-compose.yml down -v
```

`-v` 会删除 MySQL 与 MinIO 的数据卷，下次启动等同于全新部署。

#### 9. 仅构建前端（后端由外部提供时）

```bash
cd deploy/docker
docker compose -f docker-compose.frontend.yml up --build
```

该编排默认通过 `BACKEND_UPSTREAM=http://host.docker.internal:8080` 代理 `/api/v1` 到宿主机后端，可按需覆盖。

> Podman 用户见 `deploy/docker/README.md` 中的 rootless / host-network 适配说明。

---

### 方式 B：本地开发模式（分别启动各服务）

适合二次开发与调试。仅启动基础设施依赖，应用在本地以热重载方式运行。

#### 1. 启动依赖（MySQL + MinIO）

```bash
cd deploy
docker compose up -d mysql minio
```

#### 2. 主后端（`backend/`）

```bash
cd backend
uv sync                                              # 安装依赖
uv run alembic upgrade head                          # 应用迁移（首次必做）
uv run uvicorn app.main:app --reload --port 8080     # 启动
```

后端启动会校验安全配置：占位 `JWT_SECRET_KEY` / `ADMIN_PASSWORD` 会被拒绝，除非 `DEBUG=true`。CORS 默认关闭跨域，需通过 `CORS_ALLOWED_ORIGINS` 显式放行前端地址。

#### 3. AI 服务（`ai-service/`）

```bash
cd ai-service
uv sync
uv run uvicorn app.main:app --reload --port 5000
```

#### 4. 前端（`frontend/user-app/` 与 `frontend/admin-web/`）

```bash
cd frontend/user-app      # 或 frontend/admin-web
pnpm install
pnpm dev                  # user-app: 5173 / admin-web: 5174
```

若前端跨域调用本地后端，需把前端地址加入后端 `CORS_ALLOWED_ORIGINS`。

---

## 五、质量与测试命令

### 后端

```bash
cd backend
uv run ruff check .                                   # lint
uv run ruff format .                                  # 格式化（CI 用 --check）
uv run mypy app                                       # 类型检查（strict 模式）
uv run pytest                                         # 全部测试（完全离线，无需 MySQL/MinIO）
uv run pytest tests/unit/claim/test_service.py::test_handover_confirm   # 单用例
uv run pytest --cov=app --cov-report=term-missing    # 覆盖率
```

> 后端测试使用内存 SQLite + 模拟 MinIO，**无需任何外部服务即可运行**。`asyncio_mode = "auto"`，异步测试函数无需加 `@pytest.mark.asyncio`。

### AI 服务

```bash
cd ai-service
uv run ruff check . && uv run ruff format --check . && uv run mypy app
uv run pytest
```

### 前端

```bash
cd frontend/user-app      # 或 frontend/admin-web
pnpm lint                  # vue-tsc --noEmit 类型检查（无 eslint）
pnpm test:unit --run       # vitest
pnpm build                 # vue-tsc --noEmit && vite build
```

CI（`.github/workflows/ci.yml`）在 `main`/`develop` 推送与 PR 时会依次执行以上命令并构建 Docker 镜像做冒烟测试。

---

## 六、文档索引

| 想了解 | 去看 |
| --- | --- |
| 文档总索引 | `docs/README.md` |
| 接口约定与错误码 | `docs/api/conventions.md` |
| 接口索引表 | `docs/api/README.md` |
| 枚举字典 | `docs/architecture/enums.md` |
| 匹配规则 | `docs/architecture/matching-rules.md` |
| 信誉积分规则 | `docs/architecture/credit-rules.md` |
| 数据库设计 | `docs/architecture/database-design.md` |
| 核心业务流程 | `docs/architecture/core-flow-design.md` |
| 需求基线与范围 | `docs/project-management/requirements-baseline.md` |
| 测试用例与验收清单 | `docs/testing/` |
| 协作与提交规范 | `CONTRIBUTING.md` |

---

## 七、里程碑

1. **P0 闭环**：登录 → 发布 → 搜索 → 匹配 → 认领 → 交接 → 审核
2. **P1**：综合评分、信誉、举报、统计看板、批量录入、敏感脱敏
3. **P2**：申诉、二级凭证审核、邮件通知、长期未领公告、更强 AI 模型

---

## 八、分支与提交约定

- 分支：`main`（发布）/ `develop`（集成）/ `feature/<name>` / `fix/<name>`
- 提交格式：`feat(FR-02): add lost item publish api`、`fix(FR-05): ...`、`docs: ...`
- PR 单一聚焦，关联 FR/issue，接口/数据库/流程变更须同步更新文档

---

## 九、团队成员

| 成员 | GitHub | 主要角色 |
| --- | --- | --- |
| 朱梓涵 | [@handsomezhuzhu](https://github.com/handsomezhuzhu) | 项目统筹 · 后端 A（用户/认证/物品/上传）· 集成与质量 |
| 周星辰 | [@stevezxc](https://github.com/stevezxc) | 前端负责人（用户端 + 管理端） |
| 林洪宽 | [@lin-hongkuan](https://github.com/lin-hongkuan) | AI 与匹配负责人 |
| 郭焜华 | [@gkh-gbh](https://github.com/gkh-gbh) | 后端 B（认领/交接/通知/积分/举报/治理） |
| 程文韬 | [@sptlayzner](https://github.com/sptlayzner) | 文档与过程协作 |

各成员各阶段具体贡献与交付物责任分配详见 `report/07-团队报告/`。
