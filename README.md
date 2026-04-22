# 寻迹 Xunji

校园失物招领平台，软件工程课程五人团队项目。

## 快速入口

- **AI 或新成员**：先读 `CODEBUDDY.md`
- **文档**：`docs/`（`docs/README.md` 是索引）
- **协作约定**：`CONTRIBUTING.md`

## 仓库结构

```
frontend/    Vue 3 用户端网页 + admin-web 管理后台
backend/     FastAPI 主后端（Python 3.12 + uv）
ai-service/  Python AI 服务
deploy/      部署脚本和环境模板
docs/        全部文档
```

## 里程碑

1. P0 闭环：登录 → 发布 → 搜索 → 匹配 → 认领 → 交接 → 审核
2. P1：综合评分、信誉、举报、统计
3. P2：申诉、二级验证、邮件通知
