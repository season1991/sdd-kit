# -*- coding: utf-8 -*-
"""
测试运行器：运行 pytest 并将结果写入 JSON 文件。
供 test_dashboard.py 读取。
"""

import json
import os
import subprocess
import sys
import re


def run_tests(test_dir=None):
    """运行测试，返回结构化的测试结果。"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if test_dir is None:
        test_dir = os.path.join(project_root, "test", "第一期", "自习SDD-登录功能测试.py")

    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".test_results.json")

    env = os.environ.copy()
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True,
        cwd=project_root,
        env=env,
    )

    stdout_text = _decode_bytes(proc.stdout)
    stderr_text = _decode_bytes(proc.stderr)

    results = _parse_pytest_output(stdout_text, stderr_text)

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def _decode_bytes(data):
    """尝试多种编码解码字节数据。"""
    for enc in ("gbk", "utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("latin-1", errors="replace")


def _parse_pytest_output(stdout, stderr):
    """从 pytest 文本输出中解析测试结果。"""
    stdout = stdout.replace("\r\n", "\n").replace("\r", "\n")
    stderr = stderr.replace("\r\n", "\n").replace("\r", "\n")

    lines = stdout.strip().split("\n") if stdout.strip() else []

    tests = []
    summary = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "total": 0}

    for line in lines:
        # 匹配参数化测试: ...::TestClass::test_name[params] STATUS [XX%]
        m = re.search(r"::(\w+)::(\w+)\[([^\]]+)\]\s+(PASSED|FAILED|ERROR|SKIPPED)\s+\[\s*\d+%\]$", line)
        if m:
            cls_name = m.group(1)
            test_name = m.group(2)
            params = m.group(3)
            outcome = m.group(4)
            status_map = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error", "SKIPPED": "skipped"}
            status = status_map[outcome]
            summary[status] += 1
            summary["total"] += 1
            tests.append({
                "class": cls_name,
                "name": test_name,
                "params": params,
                "display_name": f"{test_name}[{params}]",
                "status": status,
                "full_name": f"{cls_name}.{test_name}[{params}]",
            })
            continue

        # 匹配普通测试: ...::TestClass::test_name STATUS [XX%]
        m = re.search(r"::(\w+)::(\w+)\s+(PASSED|FAILED|ERROR|SKIPPED)\s+\[\s*\d+%\]$", line)
        if m:
            cls_name = m.group(1)
            test_name = m.group(2)
            outcome = m.group(3)
            status_map = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error", "SKIPPED": "skipped"}
            status = status_map[outcome]
            summary[status] += 1
            summary["total"] += 1
            tests.append({
                "class": cls_name,
                "name": test_name,
                "status": status,
                "full_name": f"{cls_name}.{test_name}",
            })
            continue

    # 提取失败详情
    for test in tests:
        if test["status"] in ("failed", "error"):
            test["failure"] = _extract_failure(stderr, test["full_name"])

    return {
        "summary": summary,
        "tests": tests,
    }


def _extract_failure(text, test_name):
    """从 pytest 输出中提取单个测试的失败信息。"""
    if not text:
        return ""
    idx = text.find(test_name)
    if idx == -1:
        return ""
    chunk = text[idx:idx + 3000]
    return chunk[:1500].strip()


if __name__ == "__main__":
    results = run_tests()
    print(json.dumps(results, ensure_ascii=False, indent=2))
