class ErrorCode:
    """All error codes from docs/api/conventions.md section 7."""

    SUCCESS = 0

    # Generic 400xx
    PARAM_ERROR = 40001
    UNAUTHORIZED = 40002
    FORBIDDEN = 40003
    NOT_FOUND = 40004
    INVALID_STATE = 40005
    UPLOAD_FAILED = 40006
    DUPLICATE_SUBMIT = 40008

    # User 41xxx
    PHONE_REGISTERED = 41001
    SMS_CODE_INVALID = 41002
    CERT_INCOMPLETE = 41003
    CERT_PENDING = 41004
    USER_DISABLED = 41005
    SMS_SERVICE_UNAVAILABLE = 41006

    # Item 42xxx
    ITEM_NOT_FOUND = 42001
    ITEM_CLOSED = 42002
    IMAGE_EXCEED = 42003
    NOT_PUBLISHER = 42004
    SENSITIVE_UNAUTHORIZED = 42005

    # Match 43xxx
    MATCH_NOT_FOUND = 43001
    MATCH_CLAIMED = 43002

    # Claim 44xxx
    CLAIM_DUPLICATE = 44001
    CLAIM_NOT_FOUND = 44002
    CLAIM_INVALID_STATE = 44003
    CLAIM_ANSWER_MISMATCH = 44004
    CLAIM_PROOF_MISSING = 44005
    CLAIM_NOT_PARTY = 44006
    APPEAL_DUPLICATE = 44007

    # Credit 45xxx
    CREDIT_INSUFFICIENT = 45001
    CREDIT_FROZEN = 45002

    # Notification 46xxx
    NOTIFICATION_NOT_FOUND = 46001

    # Report 47xxx
    REPORT_TARGET_NOT_FOUND = 47001
    REPORT_DUPLICATE = 47002

    # Admin 48xxx
    REVIEW_STATE_CHANGED = 48001
    ADMIN_FORBIDDEN = 48002

    # Server 50xxx
    INTERNAL_ERROR = 50001
    AI_SERVICE_ERROR = 50002
    STORAGE_ERROR = 50003


_CODE_MESSAGES: dict[int, str] = {
    ErrorCode.SUCCESS: "success",
    ErrorCode.PARAM_ERROR: "参数校验失败",
    ErrorCode.UNAUTHORIZED: "未登录或 token 失效",
    ErrorCode.FORBIDDEN: "无权限",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.INVALID_STATE: "当前状态不允许该操作",
    ErrorCode.UPLOAD_FAILED: "文件上传失败",
    ErrorCode.DUPLICATE_SUBMIT: "重复提交",
    ErrorCode.PHONE_REGISTERED: "手机号已注册",
    ErrorCode.SMS_CODE_INVALID: "验证码错误或过期",
    ErrorCode.CERT_INCOMPLETE: "认证资料不完整",
    ErrorCode.CERT_PENDING: "已有待审批认证",
    ErrorCode.USER_DISABLED: "用户已禁用或注销",
    ErrorCode.SMS_SERVICE_UNAVAILABLE: "短信服务当前不可用",
    ErrorCode.ITEM_NOT_FOUND: "物品不存在",
    ErrorCode.ITEM_CLOSED: "物品已关闭/已完成,不可修改",
    ErrorCode.IMAGE_EXCEED: "图片数量超限(>5)",
    ErrorCode.NOT_PUBLISHER: "非发布者不可修改",
    ErrorCode.SENSITIVE_UNAUTHORIZED: "敏感物品原图越权访问",
    ErrorCode.MATCH_NOT_FOUND: "匹配结果不存在",
    ErrorCode.MATCH_CLAIMED: "匹配结果已被认领",
    ErrorCode.CLAIM_DUPLICATE: "该物品已有进行中的认领",
    ErrorCode.CLAIM_NOT_FOUND: "认领不存在",
    ErrorCode.CLAIM_INVALID_STATE: "认领状态不允许该操作",
    ErrorCode.CLAIM_ANSWER_MISMATCH: "验证答案不匹配",
    ErrorCode.CLAIM_PROOF_MISSING: "凭证未上传",
    ErrorCode.CLAIM_NOT_PARTY: "非认领当事人不可操作",
    ErrorCode.APPEAL_DUPLICATE: "申诉已提交,不可重复",
    ErrorCode.CREDIT_INSUFFICIENT: "信誉积分不足",
    ErrorCode.CREDIT_FROZEN: "信誉积分过低,暂不可认领",
    ErrorCode.NOTIFICATION_NOT_FOUND: "通知不存在",
    ErrorCode.REPORT_TARGET_NOT_FOUND: "举报目标不存在",
    ErrorCode.REPORT_DUPLICATE: "重复举报",
    ErrorCode.REVIEW_STATE_CHANGED: "审核状态已变化",
    ErrorCode.ADMIN_FORBIDDEN: "需要管理员权限",
    ErrorCode.INTERNAL_ERROR: "服务内部错误",
    ErrorCode.AI_SERVICE_ERROR: "AI 服务调用失败",
    ErrorCode.STORAGE_ERROR: "对象存储不可用",
}


class BizError(Exception):
    """Business logic exception carrying an error code and message."""

    def __init__(self, code: int, message: str | None = None) -> None:
        self.code = code
        self.message = message or _CODE_MESSAGES.get(code, "未知错误")
        super().__init__(self.message)
