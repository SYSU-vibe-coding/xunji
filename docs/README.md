# 文档总览

> AI 首次进入项目请优先读仓库根目录的 **`CODEBUDDY.md`**，本文件为索引补充。

## 目录

| 目录 | 用途 |
|---|---|
| `architecture/` | 系统架构、模块、数据库、枚举、规则、部署 |
| `api/` | 对外 REST API 与内部 AI 接口 |
| `project-management/` | 需求基线、排期、分工（主要给人读） |
| `testing/` | 测试策略、用例、验收清单 |

## 关键入口

- **枚举字典**：`architecture/enums.md`（唯一权威）
- **API 约定**：`api/conventions.md`（错误码、时间、幂等、鉴权）
- **接口索引**：`api/README.md`
- **业务规则**：`architecture/matching-rules.md`、`architecture/credit-rules.md`

## 维护铁律

1. 字段/枚举变更 → 先改 `enums.md` + 对应 `api/*.md`，再改代码
2. 数据库变更 → `database-design.md` + `backend/alembic/versions/` 迁移脚本
3. 需求优先级变更 → `project-management/requirements-baseline.md`
4. 每次迭代结束 → 更新 `testing/` 下覆盖范围

## 当前范围

P0 闭环：登录认证 → 失物/招领发布 → 搜索 → 匹配 → 认领与一级验证 → 交接 → 管理员审核。  
P1/P2 详见 `project-management/requirements-baseline.md`。
