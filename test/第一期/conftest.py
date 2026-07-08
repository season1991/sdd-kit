# -*- coding: utf-8 -*-
"""pytest 配置：使 pytest 能发现中文命名的测试文件。"""

collect_ignore_glob = []

# 自定义测试文件发现规则：匹配目录下所有 .py 文件（排除 __init__.py 和 conftest.py）
def pytest_collect_file(parent, file_path):
    """收集所有 .py 文件作为测试候选。"""
    if file_path.suffix == ".py" and file_path.name not in ("conftest.py", "__init__.py"):
        import pytest
        return pytest.Module.from_parent(parent, path=file_path)
