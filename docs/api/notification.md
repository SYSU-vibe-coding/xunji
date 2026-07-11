# 通知接口

类型枚举 `NoticeType` 见 `../architecture/enums.md`。

## GET /api/v1/notifications  · 用户

查询参数：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| pageNo, pageSize | int | 否 | |
| isRead | bool | 否 | |
| noticeType | NoticeType | 否 | |

返回 list 元素：
| 字段 | 类型 | 说明 |
|---|---|---|
| id | string(ulid) | |
| noticeType | NoticeType | |
| title | string | ≤ 100 |
| content | string | ≤ 500 |
| isRead | bool | |
| relatedType | string | `LOST` / `FOUND` / `CLAIM` / `CERT` / `REPORT` / `ANNOUNCEMENT` / null |
| relatedId | string(ulid) | 可空 |
| priority | enum | `NORMAL` / `HIGH` |
| createdAt | datetime | |

## GET /api/v1/notifications/unread-count  · 用户

返回 `{total, byType: {MATCH_RECOMMEND: n, ...}}`

## POST /api/v1/notifications/{id}/read  · 用户

仅本人通知可标记，否则 `40003`。
返回 `{id, isRead: true}`，与用户端类型声明一致；重复标记保持幂等。

## POST /api/v1/notifications/read-all  · 用户

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| noticeType | NoticeType | 否 | 不传则全部已读 |

返回 `{updated}`，值为本次实际更新的通知数量。

## GET /api/v1/announcements  · 公开

分页返回 `PUBLISHED` 公告，元素为 `{id, title, publishedAt}`，按发布时间倒序。`DRAFT/OFFLINE` 不可见。

## GET /api/v1/announcements/{id}  · 公开

返回 `{id, title, content, publishedAt}`。目标不是 `PUBLISHED`（包括草稿 ID）时按不存在返回 `40004`。

`SYSTEM_ANNOUNCEMENT` 通知使用 `relatedType = ANNOUNCEMENT` 和公告 ID。用户端应直接打开 `/announcements/{id}`；详情接口会再次校验公告仍为 `PUBLISHED`，因此下线后的旧通知不会暴露公告内容。
