"""
登录功能模块 - 存根实现（全部未实现，用于 TDD 全红阶段）
"""


class LoginService:
    """登录服务 - 占位实现，所有方法返回 None 或未就绪状态"""

    def __init__(self):
        self._users = {}
        self._locks = {}
        self._errors = {}

    def validate_input(self, phone, password):
        """前端校验：返回错误信息列表，未实现"""
        return None

    def check_phone_format(self, phone):
        """手机号格式校验，未实现"""
        return False

    def login(self, phone, password):
        """登录主逻辑，未实现"""
        return None

    def _is_locked(self, phone):
        """检查账号是否锁定，未实现"""
        return None

    def _record_error(self, phone):
        """记录错误次数，未实现"""
        return None

    def _lock_account(self, phone):
        """锁定账号，未实现"""
        return None

    def _unlock_account(self, phone):
        """解锁账号，未实现"""
        return None

    def get_welcome_message(self, phone):
        """生成欢迎消息，未实现"""
        return None
