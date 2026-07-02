# -*- coding: utf-8 -*-
"""
测试仪表盘：Flask 应用，提供测试运行和结果展示。
启动方式: python test_dashboard.py
浏览器访问: http://localhost:5000
"""

import json
import os
import threading
import time
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".test_results.json")

# 存储最后一次的测试结果
_last_results = None
_last_run_time = None


def run_tests_sync():
    """同步运行测试并保存结果。"""
    import importlib.util as _imp_util
    _runner_path = os.path.join(os.path.dirname(__file__), "test_runner.py")
    _spec = _imp_util.spec_from_file_location("test_runner", _runner_path)
    _mod = _imp_util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    global _last_results, _last_run_time
    _last_results = _mod.run_tests()
    _last_run_time = time.strftime("%Y-%m-%d %H:%M:%S")
    return _last_results


def load_cached_results():
    """加载缓存的结果。"""
    global _last_results, _last_run_time
    if _last_results is not None:
        return _last_results
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            _last_results = json.load(f)
    return _last_results


@app.route("/")
def index():
    """返回仪表盘 HTML。"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/results")
def api_results():
    """返回缓存的测试结果。"""
    results = load_cached_results()
    if results is None:
        return jsonify({"error": "没有测试结果，请先运行测试"}), 404
    return jsonify(results)


@app.route("/api/run", methods=["POST"])
def api_run():
    """运行测试并返回实时进度。"""
    global _last_results, _last_run_time

    # 在新线程中运行测试
    def _run():
        run_tests_sync()

    thread = threading.Thread(target=_run)
    thread.start()

    # 轮询结果文件
    for _ in range(60):  # 最多等待 60 秒
        if _last_results is not None:
            return jsonify(_last_results)
        time.sleep(0.5)

    return jsonify({"error": "测试超时"}), 504


@app.route("/api/status")
def api_status():
    """返回当前状态。"""
    results = load_cached_results()
    if results is None:
        return jsonify({"ready": False, "message": "尚未运行测试"})
    s = results["summary"]
    pct = round(s["passed"] / s["total"] * 100, 1) if s["total"] > 0 else 0
    return jsonify({
        "ready": True,
        "total": s["total"],
        "passed": s["passed"],
        "failed": s["failed"],
        "error": s["error"],
        "skipped": s["skipped"],
        "pass_rate": pct,
        "run_time": _last_run_time,
    })


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>测试仪表盘 - 自习SDD 登录功能</title>
<style>
:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface2: #232733;
  --border: #2e3345;
  --text: #e4e6f0;
  --text-dim: #8b8fa3;
  --green: #34d399;
  --green-bg: rgba(52,211,153,.12);
  --red: #f87171;
  --red-bg: rgba(248,113,113,.12);
  --yellow: #fbbf24;
  --yellow-bg: rgba(251,191,36,.12);
  --blue: #60a5fa;
  --blue-bg: rgba(96,165,250,.12);
  --radius: 10px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }

/* Header */
.header { text-align:center; margin-bottom:32px; }
.header h1 { font-size:1.6rem; font-weight:700; margin-bottom:4px; }
.header p { color:var(--text-dim); font-size:.9rem; }

/* Buttons */
.btn-row { display:flex; gap:10px; justify-content:center; margin-bottom:28px; flex-wrap:wrap; }
.btn { padding:10px 24px; border:none; border-radius:var(--radius); font-size:.9rem; cursor:pointer; font-weight:600; transition:all .2s; }
.btn-primary { background:var(--blue); color:#fff; }
.btn-primary:hover { background:#3b82f6; transform:translateY(-1px); }
.btn-primary:disabled { opacity:.5; cursor:not-allowed; transform:none; }
.btn-secondary { background:var(--surface2); color:var(--text); border:1px solid var(--border); }
.btn-secondary:hover { background:var(--border); }

/* Summary Cards */
.summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:14px; margin-bottom:32px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:18px 16px; text-align:center; }
.card .num { font-size:2rem; font-weight:700; line-height:1.2; }
.card .label { font-size:.8rem; color:var(--text-dim); margin-top:4px; }
.card.green .num { color:var(--green); }
.card.red .num { color:var(--red); }
.card.yellow .num { color:var(--yellow); }
.card.blue .num { color:var(--blue); }

/* Progress Bar */
.progress-wrap { margin-bottom:28px; background:var(--surface); border-radius:var(--radius); padding:18px 20px; border:1px solid var(--border); }
.progress-bar-bg { height:10px; background:var(--surface2); border-radius:5px; overflow:hidden; margin-top:10px; }
.progress-bar-fill { height:100%; border-radius:5px; transition:width .5s ease; }
.progress-info { display:flex; justify-content:space-between; font-size:.85rem; color:var(--text-dim); }

/* Module Sections */
.module { margin-bottom:16px; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }
.module-header { padding:16px 20px; cursor:pointer; display:flex; align-items:center; justify-content:space-between; user-select:none; transition:background .15s; }
.module-header:hover { background:var(--surface2); }
.module-title { font-size:1rem; font-weight:600; display:flex; align-items:center; gap:10px; }
.module-badge { font-size:.75rem; padding:2px 10px; border-radius:20px; font-weight:600; }
.module-badge.pass { background:var(--green-bg); color:var(--green); }
.module-badge.fail { background:var(--red-bg); color:var(--red); }
.module-badge.partial { background:var(--yellow-bg); color:var(--yellow); }
.module-arrow { transition:transform .2s; color:var(--text-dim); font-size:.8rem; }
.module.open .module-arrow { transform:rotate(180deg); }
.module-body { display:none; }
.module.open .module-body { display:block; }

/* Test Rows */
.test-row { display:flex; align-items:center; padding:10px 20px 10px 40px; border-top:1px solid var(--border); font-size:.88rem; gap:12px; }
.test-row:hover { background:var(--surface2); }
.test-status { width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:.7rem; font-weight:700; flex-shrink:0; }
.test-status.pass { background:var(--green-bg); color:var(--green); }
.test-status.fail { background:var(--red-bg); color:var(--red); }
.test-status.skip { background:var(--yellow-bg); color:var(--yellow); }
.test-status.error { background:rgba(239,68,68,.12); color:#ef4444; }
.test-name { flex:1; color:var(--text); }
.test-name small { color:var(--text-dim); font-size:.78rem; margin-left:6px; }
.test-time { color:var(--text-dim); font-size:.78rem; white-space:nowrap; }

/* Failure Details */
.failure-detail { padding:8px 20px 8px 72px; font-size:.8rem; color:var(--red); background:rgba(248,113,113,.04); font-family:"Fira Code","Cascadia Code",monospace; white-space:pre-wrap; max-height:200px; overflow-y:auto; display:none; }
.test-row.show-fail + .failure-detail { display:block; }
.test-row.show-fail .test-name { cursor:pointer; text-decoration:underline; text-decoration-style:dotted; }

/* Loading spinner */
.spinner { display:inline-block; width:16px; height:16px; border:2px solid var(--border); border-top-color:var(--blue); border-radius:50%; animation:spin .6s linear infinite; margin-right:6px; vertical-align:middle; }
@keyframes spin { to { transform:rotate(360deg); } }

/* Empty state */
.empty-state { text-align:center; padding:60px 20px; color:var(--text-dim); }
.empty-state .icon { font-size:3rem; margin-bottom:12px; }

/* Responsive */
@media(max-width:600px) {
  .summary-grid { grid-template-columns:repeat(2,1fr); }
  .test-row { padding:8px 12px 8px 24px; }
  .failure-detail { padding:8px 12px 8px 36px; }
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🧪 测试仪表盘</h1>
    <p>自习SDD · 登录功能 · TDD 测试套件</p>
  </div>

  <div class="btn-row">
    <button class="btn btn-primary" id="btnRun" onclick="runTests()">▶ 运行测试</button>
    <button class="btn btn-secondary" id="btnExpandAll" onclick="toggleAll(true)">展开全部</button>
    <button class="btn btn-secondary" id="btnCollapseAll" onclick="toggleAll(false)">收起全部</button>
  </div>

  <!-- Summary -->
  <div id="summaryArea"></div>

  <!-- Modules -->
  <div id="modulesArea"></div>

  <!-- Empty state -->
  <div id="emptyState" class="empty-state" style="display:none;">
    <div class="icon">📋</div>
    <p>点击「运行测试」开始执行</p>
  </div>
</div>

<script>
const MODULE_NAMES = {
  "TestFrontendValidationEmpty": "一、前端校验（输入为空）",
  "TestPhoneFormatValidation": "二、手机号格式校验",
  "TestNormalLogin": "三、正常登录",
  "TestAbnormalLogin": "四、异常登录",
  "TestAccountLock": "五、账号锁定机制",
  "TestSystemException": "六、系统异常",
  "TestWelcomePage": "七、欢迎页",
};

const CLASS_SHORT = {
  "TestFrontendValidationEmpty": "前端校验",
  "TestPhoneFormatValidation": "格式校验",
  "TestNormalLogin": "正常登录",
  "TestAbnormalLogin": "异常登录",
  "TestAccountLock": "账号锁定",
  "TestSystemException": "系统异常",
  "TestWelcomePage": "欢迎页",
};

// Extract TC number from test name
function getTC(name) {
  const m = name.match(/TC-(\d+)/);
  return m ? m[1] : "";
}

function getStatusIcon(status) {
  const map = { passed: "✓", failed: "✗", error: "!", skipped: "⊘" };
  return map[status] || "?";
}

function renderSummary(summary, runTime) {
  const total = summary.total || 0;
  const passed = summary.passed || 0;
  const failed = summary.failed || 0;
  const error = summary.error || 0;
  const skipped = summary.skipped || 0;
  const rate = total > 0 ? (passed / total * 100).toFixed(1) : 0;

  return `
    <div class="summary-grid">
      <div class="card blue"><div class="num">${total}</div><div class="label">总测试数</div></div>
      <div class="card green"><div class="num">${passed}</div><div class="label">通过</div></div>
      <div class="card red"><div class="num">${failed}</div><div class="label">失败</div></div>
      <div class="card yellow"><div class="num">${error + skipped}</div><div class="label">错误/跳过</div></div>
    </div>
    <div class="progress-wrap">
      <div class="progress-info">
        <span>通过率 <strong style="color:${rate==100?'var(--green)':rate>0?'var(--yellow)':'var(--red)'}">${rate}%</strong></span>
        <span>${runTime || '尚未运行'}</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width:${rate}%;background:${rate==100?'var(--green)':rate>0?'var(--yellow)':'var(--red)'}"></div>
      </div>
    </div>`;
}

function renderModules(tests) {
  // Group by class
  const groups = {};
  for (const t of tests) {
    const cls = t.class;
    if (!groups[cls]) groups[cls] = [];
    groups[cls].push(t);
  }

  let html = "";
  for (const [cls, items] of Object.entries(groups)) {
    const displayName = MODULE_NAMES[cls] || cls;
    const shortName = CLASS_SHORT[cls] || cls;
    const passed = items.filter(i => i.status === "passed").length;
    const failed = items.filter(i => i.status === "failed" || i.status === "error").length;
    const total = items.length;
    const badgeClass = passed === total ? "pass" : failed === total ? "fail" : "partial";

    html += `<div class="module open" data-class="${cls}">`;
    html += `<div class="module-header" onclick="toggleModule(this.parentElement)">`;
    html += `<span class="module-title">${displayName} <span class="module-badge ${badgeClass}">${passed}/${total}</span></span>`;
    html += `<span class="module-arrow">▼</span>`;
    html += `</div>`;
    html += `<div class="module-body">`;

    for (const t of items) {
      const tc = getTC(t.name);
      const displayName = t.display_name || t.name;
      const icon = getStatusIcon(t.status);
      const dur = t.duration ? t.duration.toFixed(3) + "s" : "";

      html += `<div class="test-row" data-test="${t.full_name}">`;
      html += `<span class="test-status ${t.status}">${icon}</span>`;
      html += `<span class="test-name" onclick="toggleFailure(this.parentElement)">${displayName}<small>${tc ? 'TC-' + tc : ''}</small></span>`;
      html += `<span class="test-time">${dur}</span>`;
      html += `</div>`;

      if (t.failure) {
        html += `<div class="failure-detail">${escapeHtml(t.failure)}</div>`;
      }
    }

    html += `</div></div>`;
  }
  return html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function toggleModule(el) {
  el.classList.toggle("open");
}

function toggleAll(expand) {
  document.querySelectorAll(".module").forEach(m => {
    expand ? m.classList.add("open") : m.classList.remove("open");
  });
}

function toggleFailure(row) {
  const detail = row.nextElementSibling;
  if (detail && detail.classList.contains("failure-detail")) {
    row.classList.toggle("show-fail");
  }
}

async function runTests() {
  const btn = document.getElementById("btnRun");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>运行中...';

  try {
    const resp = await fetch("/api/run", { method: "POST" });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    renderResults(data);
  } catch (e) {
    alert("运行失败: " + e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ 运行测试';
  }
}

async function loadResults() {
  try {
    const resp = await fetch("/api/results");
    if (!resp.ok) return;
    const data = await resp.json();
    renderResults(data);
  } catch (e) { /* ignore */ }
}

function renderResults(data) {
  const area = document.getElementById("summaryArea");
  const modulesArea = document.getElementById("modulesArea");
  const emptyState = document.getElementById("emptyState");

  if (!data.tests || data.tests.length === 0) {
    area.innerHTML = "";
    modulesArea.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  area.innerHTML = renderSummary(data.summary, data.runTime || null);
  modulesArea.innerHTML = renderModules(data.tests);
}

// Initial load
loadResults();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print("=" * 50)
    print("  测试仪表盘已启动")
    print("  浏览器访问: http://localhost:5000")
    print("  按 Ctrl+C 停止")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
