# API 约定

## 1. 总体

- 协议：HTTP/HTTPS，JSON，UTF-8
- 公共前缀：`/api/v1`
- 内部（主后端 ↔ AI 服务）：`/internal/ai`
- 风格：RESTful 为主

## 2. 时间与字段命名

- **请求/响应 body 中的时间字段**：`yyyy-MM-dd HH:mm:ss`，北京时间（UTC+8），不带时区后缀
- **顶层 `timestamp` 字段**：ISO 8601 带时区，例 `2026-04-22T20:00:00+08:00`
- JSON 字段 `camelCase`，数据库字段 `snake_case`
- 枚举值必须取自 `docs/architecture/enums.md`

## 3. 请求头

| 请求头 | 说明 |
|---|---|
| `Authorization` | `Bearer <jwt>` |
| `Content-Type` | `application/json` 或 `multipart/form-data` |
| `X-Request-Id` | 可选，透传到日志 |

## 4. 统一响应

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "requestId": "uuid",
  "timestamp": "2026-04-22T20:00:00+08:00"
}
```

- `code = 0` 成功；非 0 见 §7
- 错误时 `data = null`，`message` 为简短中文原因

## 5. 分页

请求参数：`pageNo`（从 1 起） `pageSize`（默认 10，最大 50）

响应 `data`：
```json
{ "list": [], "pageNo": 1, "pageSize": 10, "total": 100, "totalPages": 10 }
```

## 6. ID 与幂等

- 所有业务主键类型 `CHAR(26)`，内容为 **ULID**，由 service 层在入库前生成（推荐库 `python-ulid`）。**禁止数据库自增**，**禁止雪花 ID**
- 路径参数中的 ID 均为 ULID 字符串，路由声明为 `str` 并在依赖层做 `ULID.from_str` 校验
- 以下接口幂等键（若触发重复提交返回 `40008`）：
  | 接口 | 幂等键 |
  |---|---|
  | 发布失物 | `user_id + itemName + lostTimeStart + lostLocation`，1 分钟内 |
  | 发布招领 | `user_id + itemName + foundTime + foundLocation`，1 分钟内 |
  | 发起认领 | `claimant_id + found_item_id` 且原有 review_status ∈ `{PENDING, ANSWER_PASSED, PROOF_PENDING, APPROVED}` 时禁止新建 |
  | 交接确认 | `claim_id + role` 仅生效一次 |
- 前端必须按钮防抖

## 7. 错误码

按模块分段，便于日志排错：

| 段 | 模块 |
|---|---|
| 0 | 成功 |
| 400xx | 通用客户端错误 |
| 41xxx | 用户与认证 |
| 42xxx | 物品（失物/招领/文件） |
| 43xxx | 匹配 |
| 44xxx | 认领与交接 |
| 45xxx | 积分 |
| 46xxx | 通知 |
| 47xxx | 举报 |
| 48xxx | 后台 |
| 50xxx | 服务端错误 |

### 通用
| 码 | 含义 |
|---|---|
| 40001 | 参数校验失败 |
| 40002 | 未登录或 token 失效 |
| 40003 | 无权限 |
| 40004 | 资源不存在 |
| 40005 | 当前状态不允许该操作 |
| 40006 | 文件上传失败 |
| 40008 | 重复提交 |
| 50001 | 服务内部错误 |
| 50002 | AI 服务调用失败 |
| 50003 | 对象存储不可用 |

### 用户与认证 41xxx
| 码 | 含义 |
|---|---|
| 41001 | 手机号已注册 |
| 41002 | 验证码错误或过期 |
| 41003 | 认证资料不完整 |
| 41004 | 已有待审批认证 |
| 41005 | 用户已禁用或注销 |
| 41006 | 短信服务当前不可用 |

### 物品 42xxx
| 码 | 含义 |
|---|---|
| 42001 | 物品不存在 |
| 42002 | 物品已关闭/已完成，不可修改 |
| 42003 | 图片数量超限（>5） |
| 42004 | 非发布者不可修改 |
| 42005 | 敏感物品原图越权访问 |

### 匹配 43xxx
| 码 | 含义 |
|---|---|
| 43001 | 匹配记录不存在 |
| 43002 | 该匹配已认领 |

### 认领 44xxx
| 码 | 含义 |
|---|---|
| 44001 | 已有进行中的认领请求 |
| 44002 | 认领请求不存在 |
| 44003 | 认领状态不允许该操作 |
| 44004 | 验证答案不匹配 |
| 44005 | 凭证未上传 |
| 44006 | 非当事人不可审核 |
| 44007 | 申诉已提交，不可重复 |

### 积分 45xxx
| 码 | 含义 |
|---|---|
| 45001 | 积分不足以执行该操作 |
| 45002 | 信誉低于阈值，认领权限已冻结 |

### 通知 46xxx
| 码 | 含义 |
|---|---|
| 46001 | 通知不存在 |

### 举报 47xxx
| 码 | 含义 |
|---|---|
| 47001 | 举报目标不存在 |
| 47002 | 已举报过该目标 |

### 后台 48xxx
| 码 | 含义 |
|---|---|
| 48001 | 审核对象状态已变更 |
| 48002 | 非管理员操作 |

治理审核、举报处理均通过行锁和源状态条件更新实现。认证/内容审核仅接受 `PENDING`，举报处理仅接受 `PENDING/PROCESSING`；重复或并发请求统一返回 `48001`。

## 8. 文件与图片

- 图片：`image/jpeg` / `image/png` / `image/webp`，单文件 ≤ 20MB
- 服务端按实际图片内容解码，限制总像素，拒绝 decompression bomb；不信任客户端 MIME、文件名或扩展名
- 上传后按真实格式重新编码为 JPEG/PNG/WebP 并剥离 EXIF/文本元数据
- 每条失物/招领 ≤ 5 张
- 证件凭证等文件走同一上传接口，由 `bizType` 区分
- 对象存储 key：`<bizType>/<uploaderUserId>/<yyyyMM>/<uuid>.<真实扩展名>`
- bucket 必须为私有；后端启动和上传都会删除已有 bucket policy，禁止匿名 `GetObject`
- 上传返回稳定 `assetRef`（`asset://<object-key>`）和短时 `previewUrl`；数据库只保存 `assetRef`，禁止保存 presigned URL
- 新业务提交只接受当前用户、对应 `bizType` 的 `assetRef`，并通过对象 `stat` 校验；外部 URL 和其他用户引用均拒绝
- API 读取时动态签发 GET URL：普通资源默认 7 天，CERT/CLAIM_PROOF/敏感 FOUND/类别为 CERT 的 LOST 默认 1 小时
- 敏感 FOUND 和类别为 CERT 的 LOST 对非发布者/非管理员返回空图片并保留敏感标志/类别；CERT 仅申请人/管理员，CLAIM_PROOF 仅认领双方/管理员。所有敏感 URL 字段在对象不可用时均允许为 null（数组场景则省略不可用项），不得回退为持久化原值
- AI 服务只接收使用 `MINIO_ENDPOINT` 独立动态签发的内部短时 URL，不接收浏览器 preview URL、`assetRef` 或永久公开 URL

### 8.1 现存数据兼容与迁移

- 读取层只兼容本项目当前 MinIO endpoint、bucket 下的历史 URL，并提取 object key 后重新签名；其他域名历史值按不可用处理，不原样返回
- 可在停写窗口审计 `item_images.image_url`、`item_images.masked_image_url`、`user_cert_requests.document_image_url` 和 `users.avatar_url`，将形如 `<MINIO_PUBLIC_BASE_URL>/<bucket>/<key>` 的值改为 `asset://<key>`
- 迁移前必须确认 host、bucket 和 object key，外部 URL 不得自动导入；建议先备份并用 MinIO `stat` 校验对象存在性
- 兼容读取仅用于受控迁移，新建和编辑接口不会接受历史 URL

## 9. 鉴权与权限标注

### 9.1 基础权限等级

| 标注 | 要求 |
|---|---|
| `公开` | 无需 token |
| `用户` | `Authorization` 有效且用户状态可用 |
| `STAFF` | role ∈ `{STAFF, ADMIN}` |
| `ADMIN` | role = `ADMIN` |

### 9.2 上下文限定写法

- `用户（本人）`：已登录，且当前用户必须是该资源发布者或所有者
- `用户（当事方）`：已登录，且当前用户必须是该业务记录直接参与方
- `用户（认领者）`：已登录，且当前用户必须是该 `claim` 的 `claimant`
- `用户（拾获者）`：已登录，且当前用户必须是对应招领物品的发布者或代管方
- `用户（认领者或拾获者）`：已登录，且当前用户满足两种上下文身份之一

### 9.3 组合写法

- 多种权限统一写成 `ADMIN / 用户（本人）`、`用户 / STAFF`
- 上下文限定总是建立在基础权限之上；例如 `用户（本人）` = 先登录，再校验资源归属
- 接口文档不要单独写裸标签 `本人`、`当事方`、`认领者`、`拾获者`
