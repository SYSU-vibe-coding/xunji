# 架构文档

## 文档清单

| 文件 | 说明 | AI 何时读 |
|---|---|---|
| `system-overview.md` | 系统定位、目标、技术栈 | 第一次了解项目 |
| `module-design.md` | 前后端模块划分与包结构 | 新建模块 / 前端目录 |
| `database-design.md` | 表结构、索引、一致性要求 | 写 SQL / 实体类 |
| `enums.md` | **全项目枚举字典**（唯一权威） | 任何涉及状态/类型的代码 |
| `matching-rules.md` | 匹配公式、阈值、验证等级判定 | 写匹配、认领逻辑 |
| `credit-rules.md` | 信誉积分加减规则与反作弊 | 写积分相关代码 |
| `core-flow-design.md` | 关键业务流程概述 | 理解跨模块流程 |
| `deployment-design.md` | 部署与配置约定 | 写 Dockerfile / CI |

## 使用建议

- 开发前先读 `module-design.md` 认包结构
- 写接口前先读 `../api/conventions.md` + `enums.md`
- 涉及状态/枚举变更：必须先改 `enums.md`
