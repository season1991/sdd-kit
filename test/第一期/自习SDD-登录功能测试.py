# -*- coding: utf-8 -*-
"""
自习SDD-登录功能测试
TDD 第一阶段：全红（All Red）—— 测试编写完成，实现尚未完成，所有测试应失败。

基于文档：data/tdd/第1期/自习SDD-登录功能-测试案例清单.md
"""

import pytest
from datetime import datetime, timedelta

from src.login import LoginService


@pytest.fixture
def svc():
    """登录服务实例"""
    return LoginService()


# ============================================================
# 一、前端校验（输入为空）
# ============================================================


class TestFrontendValidationEmpty:
    """TC-01 ~ TC-03"""

    def test_TC01_phone_empty(self, svc):
        """TC-01: 手机号为空，应提示"请输入手机号"，不发起请求"""
        errors = svc.validate_input("", "abc123")
        assert errors == ["请输入手机号"]

    def test_TC02_password_empty(self, svc):
        """TC-02: 密码为空，应提示"请输入密码"，不发起请求"""
        errors = svc.validate_input("13812345678", "")
        assert errors == ["请输入密码"]

    def test_TC03_both_empty(self, svc):
        """TC-03: 手机号和密码均为空，应提示"请输入手机号"，不发起请求"""
        errors = svc.validate_input("", "")
        assert errors == ["请输入手机号"]


# ============================================================
# 二、手机号格式校验
# ============================================================


class TestPhoneFormatValidation:
    """TC-04 ~ TC-08"""

    @pytest.mark.parametrize(
        "phone,expected_error",
        [
            ("1381234", "请输入正确的11位手机号"),   # TC-04: 少于11位
            ("1381234567890", "请输入正确的11位手机号"),  # TC-05: 多于11位
            ("138abc45678", "请输入正确的11位手机号"),   # TC-06: 含字母
            ("138-1234-5678", "请输入正确的11位手机号"),  # TC-07: 含特殊字符
        ],
    )
    def test_TC04_to_TC07_invalid_phone(self, svc, phone, expected_error):
        """TC-04~TC-07: 非法手机号应返回格式错误"""
        errors = svc.validate_input(phone, "abc123")
        assert errors == [expected_error]

    def test_TC08_valid_phone(self, svc):
        """TC-08: 11位纯数字手机号应通过格式校验"""
        errors = svc.validate_input("13812345678", "abc123")
        assert errors == []


# ============================================================
# 三、正常登录
# ============================================================


class TestNormalLogin:
    """TC-09 ~ TC-11"""

    def test_TC09_correct_login(self, svc):
        """TC-09: 正确手机号+正确密码，应登录成功，返回欢迎消息"""
        svc._users["13812345678"] = {"password": "abc123"}
        result = svc.login("13812345678", "abc123")
        assert result is not None
        assert result.get("success") is True
        assert result.get("welcome") == "欢迎回来，138****5678"

    def test_TC10_case_sensitive_lowercase(self, svc):
        """TC-10: 密码大小写敏感，密码为Abc123时输入abc123应提示密码错误"""
        svc._users["13812345678"] = {"password": "Abc123"}
        result = svc.login("13812345678", "abc123")
        assert result.get("success") is False
        assert result.get("error") == "密码错误"

    def test_TC11_case_sensitive_uppercase(self, svc):
        """TC-11: 密码大小写敏感，密码为abc123时输入ABC123应提示密码错误"""
        svc._users["13812345678"] = {"password": "abc123"}
        result = svc.login("13812345678", "ABC123")
        assert result.get("success") is False
        assert result.get("error") == "密码错误"


# ============================================================
# 四、异常登录
# ============================================================


class TestAbnormalLogin:
    """TC-12 ~ TC-14"""

    def test_TC12_unregistered_phone(self, svc):
        """TC-12: 手机号未注册，应提示该手机号尚未注册"""
        result = svc.login("13999999999", "any_password")
        assert result.get("success") is False
        assert result.get("error") == "该手机号尚未注册"

    def test_TC13_wrong_password(self, svc):
        """TC-13: 密码错误，应提示"密码错误"，错误计数+1"""
        svc._users["13812345678"] = {"password": "abc123"}
        result = svc.login("13812345678", "wrongpass")
        assert result.get("success") is False
        assert result.get("error") == "密码错误"
        assert svc._errors.get("13812345678", 0) == 1

    def test_TC14_nonexistent_phone_no_password_hint(self, svc):
        """TC-14: 手机号不存在时不应暴露密码错误，应统一说未注册"""
        result = svc.login("13999999999", "abc123")
        assert result.get("error") == "该手机号尚未注册"
        assert result.get("error") != "密码错误"


# ============================================================
# 五、账号锁定机制
# ============================================================


class TestAccountLock:
    """TC-15 ~ TC-21"""

    def test_TC15_error_once(self, svc):
        """TC-15: 错误1次，提示"密码错误"，错误计数=1"""
        svc._users["13812345678"] = {"password": "abc123"}
        result = svc.login("13812345678", "wrong")
        assert result.get("error") == "密码错误"
        assert svc._errors.get("13812345678") == 1

    def test_TC16_error_three_times(self, svc):
        """TC-16: 错误3次后再次错误，错误计数=4"""
        svc._users["13812345678"] = {"password": "abc123"}
        svc._errors["13812345678"] = 3
        result = svc.login("13812345678", "wrong")
        assert result.get("error") == "密码错误"
        assert svc._errors.get("13812345678") == 4

    def test_TC17_error_five_times_lock(self, svc):
        """TC-17: 错误5次触发锁定，应提示账号锁定30分钟"""
        svc._users["13812345678"] = {"password": "abc123"}
        svc._errors["13812345678"] = 4
        result = svc.login("13812345678", "wrong")
        assert result.get("success") is False
        assert "锁定" in result.get("error", "") or "锁定" in str(result)

    def test_TC18_locked_correct_password(self, svc):
        """TC-18: 锁定期间输入正确密码，应提示账号已锁定"""
        svc._users["13812345678"] = {"password": "abc123"}
        svc._locks["13812345678"] = datetime.now() + timedelta(minutes=30)
        result = svc.login("13812345678", "abc123")
        assert result.get("success") is False
        assert "锁定" in result.get("error", "")

    def test_TC19_locked_wrong_password(self, svc):
        """TC-19: 锁定期间输入错误密码，应提示账号已锁定"""
        svc._users["13812345678"] = {"password": "abc123"}
        svc._locks["13812345678"] = datetime.now() + timedelta(minutes=30)
        result = svc.login("13812345678", "wrong")
        assert result.get("success") is False
        assert "锁定" in result.get("error", "")

    def test_TC20_locked_expired_unlock(self, svc):
        """TC-20: 锁定到期后自动解锁，输入正确密码应登录成功"""
        svc._users["13812345678"] = {"password": "abc123"}
        svc._locks["13812345678"] = datetime.now() - timedelta(minutes=31)
        result = svc.login("13812345678", "abc123")
        assert result.get("success") is True

    def test_TC21_locked_expired_error_reset(self, svc):
        """TC-21: 锁定到期后错误计数清零，再次错误应从1开始"""
        svc._users["13812345678"] = {"password": "abc123"}
        svc._errors["13812345678"] = 4
        svc._locks["13812345678"] = datetime.now() - timedelta(minutes=31)
        svc.login("13812345678", "abc123")  # 先解锁
        result = svc.login("13812345678", "wrong")
        assert result.get("error") == "密码错误"
        assert svc._errors.get("13812345678") == 1


# ============================================================
# 六、系统异常
# ============================================================


class TestSystemException:
    """TC-22 ~ TC-23"""

    def test_TC22_database_connection_failure(self, svc):
        """TC-22: 数据库连接失败，应提示系统异常请稍后重试"""
        svc._simulate_db_failure = True
        result = svc.login("13812345678", "abc123")
        assert result.get("success") is False
        assert "系统异常" in result.get("error", "")

    def test_TC23_query_timeout(self, svc):
        """TC-23: 服务端查询超时，应提示系统异常请稍后重试"""
        svc._simulate_timeout = True
        result = svc.login("13812345678", "abc123")
        assert result.get("success") is False
        assert "系统异常" in result.get("error", "")


# ============================================================
# 七、欢迎页
# ============================================================


class TestWelcomePage:
    """TC-24"""

    def test_TC24_welcomessage_masked_phone(self, svc):
        """TC-24: 欢迎页应显示脱敏手机号"""
        svc._users["13812345678"] = {"password": "abc123"}
        result = svc.login("13812345678", "abc123")
        assert "138****5678" in result.get("welcome", "")
