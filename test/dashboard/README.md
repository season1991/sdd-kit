# 测试仪表盘使用说明

## 快速启动

```bash
python test/dashboard/test_dashboard.py
```

浏览器打开 **http://localhost:5000**

按 `Ctrl+C` 停止服务。

## 功能

- **一键运行测试** — 点击页面顶部的「运行测试」按钮，自动执行 pytest 并刷新结果
- **模块分组** — 按测试大类折叠/展开（前端校验、格式校验、正常登录、异常登录、账号锁定、系统异常、欢迎页）
- **状态概览** — 顶部卡片显示总测试数、通过数、失败数、通过率进度条
- **失败详情** — 点击失败的测试名可查看错误堆栈

## 架构

```
test/
├── 第一期/
│   └── 自习SDD-登录功能测试.py   ← pytest 测试文件
└── dashboard/
    ├── test_runner.py            ← 运行 pytest，解析输出为 JSON
    └── test_dashboard.py         ← Flask 服务 + HTML 仪表盘
```

- `test_runner.py` 通过 `subprocess` 调用 pytest，解析文本输出为结构化数据
- `test_dashboard.py` 提供 Flask Web 服务，前端用原生 HTML/CSS/JS（无框架依赖）
- 测试结果缓存到 `.test_results.json`，刷新页面无需重新运行

## 依赖

- Python 3.8+
- Flask
- pytest

安装依赖：

```bash
pip install flask pytest
```

## 命令行直接运行测试

```bash
# 在项目根目录
python -m pytest test/第一期/ -v

# 单条测试
python -m pytest test/第一期/ -v -k "TC-01"

# 失败后停止
python -m pytest test/第一期/ -v -x
```
