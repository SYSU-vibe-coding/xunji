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
| relatedType | string | `LOST` / `FOUND` / `CLAIM` / `CERT` / `REPORT` / null |
| relatedId | string(ulid) | 可空 |
| priority | enum | `NORMAL` / `HIGH` |
| createdAt | datetime | |

## GET /api/v1/notifications/unread-count  · 用户

返回 `{total, byType: {MATCH_RECOMMEND: n, ...}}`

## POST /api/v1/notifications/{id}/read  · 用户

仅本人通知可标记，否则 `40003`。

## POST /api/v1/notifications/read-all  · 用户

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| noticeType | NoticeType | 否 | 不传则全部已读 |
