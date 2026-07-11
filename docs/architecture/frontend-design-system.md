# 用户端前端设计系统

## 1. 技术选型

用户端继续使用 `Vue 3 + Vue Router + Pinia + Element Plus + SCSS`。本轮不引入 Vant、Naive UI、Ant Design Vue 或第二套组件库。

原因：

- Element Plus 已覆盖表单、Drawer、Dialog、Tabs、Badge、分页、Skeleton 和反馈组件。
- 混用组件库会形成两套颜色、圆角、表单校验、弹层层级和交互状态，反而降低上线可信度。
- 当前问题来自信息架构、设计令牌、响应式和可访问性不统一，不是组件数量不足。
- 保持单一组件系统可以降低包体、主题覆盖和长期维护成本。

后续适合引入的是工程质量工具，而不是另一套 UI：

| 工具 | 用途 | 建议阶段 |
| --- | --- | --- |
| Playwright | 双用户发布、认领、交接浏览器回归 | 上线前必须 |
| Storybook / Histoire | 独立展示和评审业务组件 | 组件继续增加时 |
| axe-core | 自动化可访问性检查 | 上线前建议 |
| Sentry | 前端异常和接口失败观测 | 对外部署时 |

## 2. 信息架构

移动端主导航固定为五槽：

```text
首页 | 检索 | 发布 | 消息 | 我的
```

- 发布永远位于第三槽，即几何中心。
- 公告属于消息中心，不单独占据一级导航。
- 消息中心使用“通知 / 公告”两个 Tab，未读数只统计通知。
- 公告详情、通知详情返回时必须恢复消息中心上下文。
- 匹配和我的认领属于业务快捷入口，在首页和桌面 Sidebar 提供。

## 3. 设计令牌

权威令牌定义在 `frontend/user-app/src/styles/global.scss`：

- 品牌与语义色：`--xunji-primary`、`--xunji-success`、`--xunji-warning`、`--xunji-danger`
- 表面与文字：`--xunji-bg`、`--xunji-surface`、`--xunji-text-*`
- 间距：`--xunji-space-*`
- 圆角：`--xunji-radius-*`
- 尺寸：`--xunji-touch-target`、`--xunji-header-height-*`、`--xunji-dock-height`
- 层级：`--xunji-z-*`
- 动效：`--xunji-motion-*`、`--xunji-ease-*`

页面不得继续新增没有语义的品牌色硬编码。Element Plus 的 CSS 变量只在 `element-overrides.scss` 映射到上述令牌。

## 4. 响应式规则

| 范围 | 布局规则 |
| --- | --- |
| `> 1180px` | Sidebar + 多列内容 + 完整筛选栏 |
| `721px - 1180px` | Sidebar 保留，筛选栏两列 |
| `<= 880px` | 隐藏 Sidebar，显示五槽 Dock，移动 Header |
| `<= 720px` | 单列内容，高级筛选进入底部 Drawer |
| `<= 390px` | 紧凑间距、分页和触控布局 |

所有壳层必须使用 `100dvh` 和 `env(safe-area-inset-*)`，移动内容底部必须通过 `--xunji-dock-height` 避让固定 Dock。

## 5. 交互和可访问性

- 所有触控目标最小 `44px`。
- 导航使用 `RouterLink`，动作使用 `button`，不使用只有 `@click` 的 `div/card`。
- 当前导航使用 `aria-current="page"`，图标按钮必须有 `aria-label`。
- 全局提供 `:focus-visible`；不能只用颜色表示未读、错误或当前状态。
- 弹层优先使用 Element Plus Drawer/Dialog，复用焦点陷阱、ESC 和滚动锁定。
- 支持 `prefers-reduced-motion`。
- 读请求必须区分 loading、error、empty、success；错误不能伪装成空数据。

## 6. 页面视觉层级

- 首页是唯一保留强品牌 Hero 的主页面。
- 检索、消息和个人中心使用安静的内容标题与浅色 Surface，不重复强渐变。
- 首页优先级：最新招领、常用业务、可信数据、消息提醒。
- 个人中心在移动端使用列表行，在桌面使用双列业务卡片。
- 数据指标必须来自真实 API total，不得用当前页数量伪装全局统计。

## 7. 上线验收尺寸

至少人工或 Playwright 覆盖：

- 320 × 568
- 360 × 800
- 390 × 844
- 768 × 1024
- 900 × 700
- 1440 × 900

同时验证 iOS 底部 Home Indicator、横屏左右安全区、软键盘弹出、Tab/Enter/Escape 键盘操作和 200% 页面缩放。
