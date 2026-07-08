# -*- coding: utf-8 -*-
"""
pytest 测试运行器：调用 pytest 执行测试，解析输出为结构化 JSON。
"""

import json
import os
import re
import subprocess
import sys
import time


# ── 项目根目录（test/dashboard/ 的上两级）──────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_TEST_DIR = os.path.join(_PROJECT_ROOT, "test", "第一期")

# ── 大模块名称映射（Python 类名 → 中文）─────────────────────────────
CLASS_DISPLAY_NAMES = {
    "TestFrontendValidationEmpty": "一、前端校验（输入为空）",
    "TestPhoneFormatValidation":   "二、手机号格式校验",
    "TestNormalLogin":             "三、正常登录",
    "TestAbnormalLogin":           "四、异常登录",
    "TestAccountLock":             "五、账号锁定机制",
    "TestSystemException":         "六、系统异常",
    "TestWelcomePage":             "七、欢迎页",
}

# ── 测试用例功能描述（TC 编号 → 中文描述）───────────────────────────
TC_DESCRIPTIONS = {
    "TC-01": '手机号为空，应提示"请输入手机号"，不发起请求',
    "TC-02": '密码为空，应提示"请输入密码"，不发起请求',
    "TC-03": '手机号和密码均为空，应提示"请输入手机号"，不发起请求',
    "TC-04": '手机号少于11位，应提示"请输入正确的11位手机号"',
    "TC-05": '手机号多于11位，应提示"请输入正确的11位手机号"',
    "TC-06": '手机号含字母，应提示"请输入正确的11位手机号"',
    "TC-07": '手机号含特殊字符，应提示"请输入正确的11位手机号"',
    "TC-08": '11位纯数字手机号应通过格式校验',
    "TC-09": '正确手机号+正确密码，应登录成功，显示欢迎消息',
    "TC-10": '密码大小写敏感（小写），输入错误应提示"密码错误"',
    "TC-11": '密码大小写敏感（大写），输入错误应提示"密码错误"',
    "TC-12": '手机号未注册，应提示"该手机号尚未注册"',
    "TC-13": '密码错误，应提示"密码错误"，错误计数+1',
    "TC-14": '手机号不存在时不暴露密码错误，应统一提示未注册',
    "TC-15": '错误1次，提示"密码错误"，错误计数=1',
    "TC-16": '错误3次后再次错误，错误计数=4',
    "TC-17": '错误5次触发锁定，应提示账号锁定30分钟',
    "TC-18": '锁定期间输入正确密码，应提示账号已锁定',
    "TC-19": '锁定期间输入错误密码，应提示账号已锁定',
    "TC-20": '锁定到期后自动解锁，输入正确密码应登录成功',
    "TC-21": '锁定到期后错误计数清零，再次错误应从1开始',
    "TC-22": '数据库连接失败，应提示系统异常请稍后重试',
    "TC-23": '服务端查询超时，应提示系统异常请稍后重试',
    "TC-24": '欢迎页应显示脱敏手机号 138****5678',
}


def extract_tc_number(test_name: str) -> str:
    """从测试名称中提取 TC 编号，如 'TC-01'。"""
    m = re.search(r"TC[-_]?(\d+)", test_name)
    return f"TC-{m.group(1)}" if m else ""


def get_display_name(test_name: str) -> str:
    """获取用例的中文显示名称：优先用描述映射，回退到方法名。"""
    tc = extract_tc_number(test_name)
    if tc and tc in TC_DESCRIPTIONS:
        return f"{tc} {TC_DESCRIPTIONS[tc]}"
    return test_name


def run_tests(test_dir: str = None, module_class: str = None) -> dict:
    """
    运行 pytest 测试并返回结构化结果。

    参数:
        test_dir:    测试目录路径，默认为 test/第一期/
        module_class: 指定类名时仅运行该模块，如 "TestNormalLogin"

    返回:
        {
            "summary": {"total": N, "passed": N, "failed": N, "error": N, "skipped": N},
            "tests": [
                {
                    "class": "TestXxx",
                    "class_display": "一、...",
                    "name": "test_TC01_xxx",
                    "full_name": "file::Class::method",
                    "display_name": "TC-01 手机号为空...",
                    "tc": "TC-01",
                    "status": "passed|failed|error|skipped",
                    "duration": 0.001,
                    "failure": "错误信息..."
                },
                ...
            ],
            "runTime": "2025-07-02 14:30:00",
            "duration": 1.23
        }
    """
    if test_dir is None:
        test_dir = _DEFAULT_TEST_DIR

    cmd = [sys.executable, "-m", "pytest", test_dir,
           "-v", "--tb=short", "--no-header", "-p", "no:cacheprovider"]

    if module_class:
        cmd.extend(["-k", module_class])

    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=_PROJECT_ROOT,
        )
    except FileNotFoundError:
        return _error_result("测试环境异常：pytest 未安装，请先执行 pip install pytest")
    except subprocess.TimeoutExpired:
        return _error_result("测试运行超时，请检查测试代码")

    elapsed = round(time.time() - start, 2)
    output = proc.stdout + "\n" + proc.stderr

    # 检查 pytest 自身是否报错（import error 等）
    if proc.returncode not in (0, 1, 2, 5):
        # returncode 5 = no tests collected，其他非 0/1/2 视为异常
        if proc.returncode != 5:
            return _error_result(f"测试运行异常:\n{proc.stderr[:2000]}")

    tests = _parse_pytest_output(output)
    summary = _compute_summary(tests)

    return {
        "summary": summary,
        "tests": tests,
        "runTime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration": elapsed,
    }


def _parse_pytest_output(output: str) -> list:
    """解析 pytest -v 输出，提取每条用例的状态。"""
    tests = []

    # 只匹配实时输出行（带百分比进度的行），跳过末尾 summary 段
    # 例如: test/第一期/file.py::ClassName::method[param] PASSED [  4%]
    pattern = re.compile(
        r"^(.+?)::([\w]+)::([\w]+(?:\[.+?\])?)\s+"
        r"(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+\[",
        re.MULTILINE,
    )

    # 失败详情：匹配 short tb 输出
    failure_blocks = _extract_failure_blocks(output)

    for m in pattern.finditer(output):
        filepath, cls_name, method_raw = m.group(1), m.group(2), m.group(3)
        status_raw = m.group(4)

        # 参数化显示名
        param_match = re.search(r"\[(.+?)\]", method_raw)
        param = param_match.group(1) if param_match else ""
        method_clean = re.sub(r"\[.+?\]", "", method_raw)

        tc = extract_tc_number(method_clean)

        # 状态映射
        status_map = {
            "PASSED": "passed", "FAILED": "failed", "ERROR": "error",
            "SKIPPED": "skipped", "XFAIL": "skipped", "XPASS": "passed",
        }
        status = status_map.get(status_raw, "failed")

        # 查找失败详情（failure_blocks 的 key 是 "ClassName.method_name"）
        full_name = f"{filepath}::{cls_name}::{method_raw}"
        lookup_key = f"{cls_name}.{method_clean}"
        failure = failure_blocks.get(lookup_key, "")
        # 对于参数化测试，尝试带参数的 key
        if not failure and param:
            lookup_key_param = f"{cls_name}.{method_raw}"
            failure = failure_blocks.get(lookup_key_param, "")

        # 显示名
        display = get_display_name(method_clean)
        if param:
            display += f"（{param}）"

        tests.append({
            "class": cls_name,
            "class_display": CLASS_DISPLAY_NAMES.get(cls_name, cls_name),
            "name": method_clean,
            "full_name": full_name,
            "display_name": display,
            "tc": tc,
            "status": status,
            "duration": 0.0,
            "failure": failure,
        })

    # 从时间行提取耗时: "test.py::Class::method PASSED [0.01s]"
    time_pattern = re.compile(
        r"^(.+?)::([\w]+)::([\w]+(?:\[.+?\])?)\s+PASSED\s+\[([\d.]+)s\]",
        re.MULTILINE,
    )
    for m in time_pattern.finditer(output):
        full = f"{m.group(1)}::{m.group(2)}::{m.group(3)}"
        dur = float(m.group(4))
        for t in tests:
            if t["full_name"] == full:
                t["duration"] = dur
                break

    return tests


def _extract_failure_blocks(output: str) -> dict:
    """
    从 pytest --tb=short 输出中提取失败测试的错误信息。
    返回 {类名.方法名: 错误详情} 的字典。
    """
    blocks = {}
    # 分隔 FAILURES 段（用等号包围）
    parts = re.split(r"={3,}\s+FAILURES\s+={3,}", output)
    if len(parts) < 2:
        return blocks

    failure_section = parts[1]

    # 用正则查找每个测试块的起始位置
    # 分隔符格式: ______________ ClassName.method_name ______________
    # 也支持参数化和短分隔符: _ ClassName.method_name[param] ____
    separator_pattern = re.compile(
        r"_+\s+([\w]+\.[\w]+(?:\[.+?\])?)\s+[_\s]"
    )
    matches = list(separator_pattern.finditer(failure_section))

    for i, m in enumerate(matches):
        test_key = m.group(1)  # e.g. "TestFrontendValidationEmpty.test_TC01_phone_empty"
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(failure_section)
        body = failure_section[start:end].strip()
        if body:
            blocks[test_key] = body[:2000]

    return blocks


def _compute_summary(tests: list) -> dict:
    """汇总各状态计数。"""
    s = {"total": len(tests), "passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for t in tests:
        key = t["status"]
        if key in s:
            s[key] += 1
    return s


def _error_result(message: str) -> dict:
    """返回错误结果结构。"""
    return {
        "summary": {"total": 0, "passed": 0, "failed": 0, "error": 0, "skipped": 0},
        "tests": [],
        "runTime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration": 0,
        "error": message,
    }


# ── CLI 入口 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    target_class = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_tests(module_class=target_class)
    print(json.dumps(result, ensure_ascii=False, indent=2))
