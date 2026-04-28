# 枚举字典

全项目唯一权威枚举定义。**其他文档必须引用此文件中的值，不得自造或翻译。**

## 用户

### UserRole
| 值 | 说明 |
|---|---|
| USER | 普通用户（学生/教职工） |
| STAFF | 后勤/安保 |
| ADMIN | 管理员 |

### CertStatus（`users.cert_status`）
| 值 | 说明 |
|---|---|
| UNVERIFIED | 未提交认证 |
| PENDING | 审批中 |
| APPROVED | 已通过 |
| REJECTED | 已驳回 |

### UserStatus（`users.status`）
`ACTIVE` / `DISABLED` / `CANCELLED`

### ReviewStatus（认证申请 / 内容审核通用）
`PENDING` / `APPROVED` / `REJECTED`

## 物品

### ItemCategory
| 值 | 对应场景 |
|---|---|
| CERT | 证件类（一卡通、身份证、学生证等，属敏感物品） |
| ELECTRONIC | 电子设备 |
| DAILY_USE | 生活用品 |
| BOOK | 书籍文具 |
| OTHER | 其他 |

### LostItemStatus（`lost_items.status`）
| 值 | 说明 |
|---|---|
| SEARCHING | 寻物中（初始） |
| FOUND | 已找回 |
| CLOSED | 用户主动关闭 |

### FoundItemStatus（`found_items.status`）
| 值 | 说明 |
|---|---|
| PENDING | 待认领（初始） |
| CLAIMING | 有认领中 |
| RETURNED | 已归还 |
| CLOSED | 关闭 |

### CustodyType（`found_items.custody_type`）
`SELF`（自行保管） / `SECURITY`（保卫处） / `OFFICE`（院系办公室）

### ContactPreference（`found_items.contact_preference`）
`IN_APP` / `PHONE`

### BizType（`item_images.biz_type` / 通用业务类型）
`LOST` / `FOUND` / `CLAIM_PROOF` / `CERT` / `USER` / `CLAIM` / `REPORT` / `ANNOUNCEMENT`

## 匹配与认领

### MatchStatus（`match_results.match_status`）
`NEW` / `READ` / `CLAIMED` / `EXPIRED`

### VerifyLevel（`claim_requests.verify_level`）
| 值 | 说明 |
|---|---|
| LEVEL_1 | 问答验证 |
| LEVEL_2 | 问答 + 凭证 |
| LEVEL_3 | 线下核对 |
| FAST_TRACK | 敏感证件快捷通道，系统自动比对实名信息 |

判定规则见 `matching-rules.md §3`。

### ClaimReviewStatus（`claim_requests.review_status`）
| 值 | 说明 |
|---|---|
| PENDING | 刚提交，待拾获者审核 |
| ANSWER_PASSED | 一级问答已通过，等待凭证或交接安排 |
| PROOF_PENDING | 等待认领者补交凭证（二级） |
| APPROVED | 审核通过，可进入交接 |
| REJECTED | 被拒绝 |
| APPEALING | 申诉中 |
| HANDED_OVER | 已交接完成 |

### HandoverMethod（`handover_records.method`）
`MEETUP`（当面交接） / `PICKUP_POINT`（指定代收点）

## 通知

### NoticeType（`notifications.notice_type`）
| 值 | 触发点 |
|---|---|
| MATCH_RECOMMEND | 匹配生成 |
| CLAIM_REQUEST | 收到认领 |
| CLAIM_REVIEW | 认领审核结果 |
| HANDOVER_REMINDER | 交接提醒 |
| CREDIT_CHANGED | 积分变动 |
| SYSTEM_ANNOUNCEMENT | 系统公告 |

### NotificationPriority（`notifications.priority`）
`NORMAL` / `HIGH`

## 积分

### CreditReasonCode（`credit_logs.reason_code`）
详见 `credit-rules.md`。

## 举报

### ReportTargetType（`reports.target_type`）
`LOST_ITEM` / `FOUND_ITEM` / `CLAIM_REQUEST` / `USER`

### ReportHandleStatus（`reports.handle_status`）
`PENDING` / `PROCESSING` / `CLOSED` / `REJECTED`

## 公告

### AnnouncementStatus（`announcements.status`）
`DRAFT` / `PUBLISHED` / `OFFLINE`

## 操作日志

### OperationAction（`operation_logs.action`）
常用值：`CREATE` / `UPDATE_STATUS` / `REVIEW_APPROVE` / `REVIEW_REJECT` / `HANDOVER_CONFIRM` / `CREDIT_CHANGE` / `REPORT_HANDLE` / `CERT_APPROVE` / `CERT_REJECT`

新增 action 必须在此登记。
