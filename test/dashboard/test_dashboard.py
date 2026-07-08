# -*- coding: utf-8 -*-
"""
测试仪表盘：Flask 应用，提供测试运行和结果展示。
启动方式: python test/dashboard/test_dashboard.py
浏览器访问: http://localhost:5000
"""

import json
import os
import sys
import threading
import time

from flask import Flask, jsonify, render_template_string, request

# ── 加载 test_runner 模块 ──────────────────────────────────────────
_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
_runner_path = os.path.join(_DASHBOARD_DIR, "test_runner.py")

import importlib.util as _imp_util
_spec = _imp_util.spec_from_file_location("test_runner", _runner_path)
_runner = _imp_util.module_from_spec(_spec)
_spec.loader.exec_module(_runner)

app = Flask(__name__)

# ── 运行状态（内存中）─────────────────────────────────────────────
_last_results = None      # 最近一次运行结果
_is_running = False       # 是否正在运行
_run_lock = threading.Lock()


def _run_tests_async(test_dir=None, module_class=None):
    """在后台线程中运行测试。"""
    global _last_results, _is_running
    _is_running = True
    try:
        _last_results = _runner.run_tests(test_dir=test_dir, module_class=module_class)
    except Exception as e:
        _last_results = _runner._error_result(f"运行异常: {str(e)}")
    finally:
        _is_running = False


# ── API 路由 ───────────────────────────────────────────────────────

@app.route("/")
def index():
    """返回仪表盘主页。"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/results")
def api_results():
    """返回最近一次测试结果。"""
    if _last_results is None:
        return jsonify({"status": "no_results", "message": "尚未运行测试"})
    return jsonify(_last_results)


@app.route("/api/status")
def api_status():
    """返回运行状态。"""
    return jsonify({"running": _is_running})


@app.route("/api/run", methods=["POST"])
def api_run():
    """
    触发测试运行。
    可选参数: {"module_class": "TestNormalLogin"}
    """
    global _is_running
    with _run_lock:
        if _is_running:
            return jsonify({"error": "测试正在运行中，请稍候"}), 409

        body = request.get_json(silent=True) or {}
        module_class = body.get("module_class")

        thread = threading.Thread(
            target=_run_tests_async,
            kwargs={"module_class": module_class},
            daemon=True,
        )
        thread.start()

    # 等待运行完成（最多 70 秒）
    for _ in range(140):
        if not _is_running:
            break
        time.sleep(0.5)

    if _is_running:
        return jsonify({"error": "测试运行超时"}), 504

    if _last_results and "error" in _last_results:
        return jsonify(_last_results), 500

    return jsonify(_last_results or {})


# ── HTML 模板 ──────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>测试仪表盘 — 自习SDD 登录功能</title>
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
  --orange: #fb923c;
  --orange-bg: rgba(251,146,60,.12);
  --radius: 10px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }

/* ── Header ─────────────────────────────────────── */
.header { text-align:center; margin-bottom:32px; }
.header h1 { font-size:1.6rem; font-weight:700; margin-bottom:4px; }
.header p { color:var(--text-dim); font-size:.9rem; }

/* ── Buttons ────────────────────────────────────── */
.btn-row { display:flex; gap:10px; justify-content:center; margin-bottom:28px; flex-wrap:wrap; }
.btn { padding:10px 24px; border:none; border-radius:var(--radius); font-size:.9rem; cursor:pointer; font-weight:600; transition:all .2s; }
.btn-primary { background:var(--blue); color:#fff; }
.btn-primary:hover { background:#3b82f6; transform:translateY(-1px); }
.btn-primary:disabled { opacity:.5; cursor:not-allowed; transform:none; }
.btn-secondary { background:var(--surface2); color:var(--text); border:1px solid var(--border); }
.btn-secondary:hover { background:var(--border); }
.btn-sm { padding:5px 14px; font-size:.78rem; border-radius:8px; }

/* ── Summary Cards ──────────────────────────────── */
.summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:14px; margin-bottom:28px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:18px 16px; text-align:center; }
.card .num { font-size:2rem; font-weight:700; line-height:1.2; }
.card .label { font-size:.8rem; color:var(--text-dim); margin-top:4px; }
.card.green .num { color:var(--green); }
.card.red .num { color:var(--red); }
.card.yellow .num { color:var(--yellow); }
.card.blue .num { color:var(--blue); }
.card.orange .num { color:var(--orange); }

/* ── Progress Bar ───────────────────────────────── */
.progress-wrap { margin-bottom:28px; background:var(--surface); border-radius:var(--radius); padding:18px 20px; border:1px solid var(--border); }
.progress-bar-bg { height:10px; background:var(--surface2); border-radius:5px; overflow:hidden; margin-top:10px; }
.progress-bar-fill { height:100%; border-radius:5px; transition:width .5s ease; }
.progress-info { display:flex; justify-content:space-between; font-size:.85rem; color:var(--text-dim); }

/* ── Module Sections ────────────────────────────── */
.module { margin-bottom:16px; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }
.module-header { padding:16px 20px; cursor:pointer; display:flex; align-items:center; justify-content:space-between; user-select:none; transition:background .15s; }
.module-header:hover { background:var(--surface2); }
.module-title { font-size:1rem; font-weight:600; display:flex; align-items:center; gap:10px; }
.module-badge { font-size:.75rem; padding:2px 10px; border-radius:20px; font-weight:600; }
.module-badge.pass { background:var(--green-bg); color:var(--green); }
.module-badge.fail { background:var(--red-bg); color:var(--red); }
.module-badge.partial { background:var(--yellow-bg); color:var(--yellow); }
.module-badge.none { background:rgba(139,143,163,.12); color:var(--text-dim); }
.module-actions { display:flex; align-items:center; gap:10px; }
.module-arrow { transition:transform .2s; color:var(--text-dim); font-size:.8rem; }
.module.open .module-arrow { transform:rotate(180deg); }
.module-body { display:none; }
.module.open .module-body { display:block; }

/* ── Test Table ─────────────────────────────────── */
.test-table { width:100%; border-collapse:collapse; }
.test-table th { text-align:left; padding:8px 20px 8px 36px; font-size:.78rem; color:var(--text-dim); font-weight:500; border-bottom:1px solid var(--border); text-transform:uppercase; letter-spacing:.5px; }
.test-table td { padding:10px 20px 10px 36px; border-top:1px solid var(--border); font-size:.88rem; }
.test-table tr:hover td { background:var(--surface2); }
.test-table .col-tc { width:70px; white-space:nowrap; color:var(--text-dim); }
.test-table .col-status { width:60px; text-align:center; }

/* ── Status Icon ────────────────────────────────── */
.status-icon { display:inline-flex; align-items:center; justify-content:center; width:24px; height:24px; border-radius:50%; font-size:.75rem; font-weight:700; }
.status-icon.passed { background:var(--green-bg); color:var(--green); }
.status-icon.failed { background:var(--red-bg); color:var(--red); }
.status-icon.error { background:var(--orange-bg); color:var(--orange); }
.status-icon.skipped { background:var(--yellow-bg); color:var(--yellow); }
.status-icon.not-run { background:rgba(139,143,163,.1); color:var(--text-dim); }

/* ── Failure Detail ─────────────────────────────── */
.failure-detail { display:none; padding:0 20px 12px 110px; }
.failure-detail.open { display:block; }
.failure-detail pre { background:rgba(248,113,113,.06); border:1px solid rgba(248,113,113,.15); border-radius:8px; padding:12px 16px; font-family:"Fira Code","Cascadia Code","Consolas",monospace; font-size:.8rem; color:var(--red); white-space:pre-wrap; word-break:break-all; max-height:250px; overflow-y:auto; line-height:1.5; }
.test-row.clickable { cursor:pointer; }
.test-row.clickable td { text-decoration:none; }
.test-row.clickable:hover td { text-decoration:underline dotted; text-underline-offset:3px; }

/* ── Loading Spinner ────────────────────────────── */
.spinner { display:inline-block; width:16px; height:16px; border:2px solid var(--border); border-top-color:var(--blue); border-radius:50%; animation:spin .6s linear infinite; margin-right:6px; vertical-align:middle; }
@keyframes spin { to { transform:rotate(360deg); } }

/* ── Empty / Error State ────────────────────────── */
.empty-state { text-align:center; padding:80px 20px; color:var(--text-dim); }
.empty-state .icon { font-size:3rem; margin-bottom:12px; }
.error-banner { background:var(--red-bg); border:1px solid rgba(248,113,113,.3); border-radius:var(--radius); padding:16px 20px; margin-bottom:20px; color:var(--red); font-size:.9rem; white-space:pre-wrap; }

/* ── Run-time Info ──────────────────────────────── */
.runtime-info { text-align:center; color:var(--text-dim); font-size:.8rem; margin-bottom:20px; }

/* ── Responsive ─────────────────────────────────── */
@media(max-width:600px) {
  .summary-grid { grid-template-columns:repeat(2,1fr); }
  .test-table th, .test-table td { padding:8px 12px 8px 20px; }
  .failure-detail { padding:0 12px 12px 20px; }
  .module-header { padding:12px 14px; }
  .module-title { font-size:.9rem; }
}
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>🧪 测试仪表盘</h1>
    <p>自习SDD · 登录功能 · 测试监控</p>
  </div>

  <!-- Buttons -->
  <div class="btn-row">
    <button class="btn btn-primary" id="btnRunAll" onclick="runTests()">▶ 运行全部测试</button>
    <button class="btn btn-secondary" onclick="toggleAll(true)">展开全部</button>
    <button class="btn btn-secondary" onclick="toggleAll(false)">收起全部</button>
  </div>

  <!-- Runtime Info -->
  <div id="runtimeInfo" class="runtime-info" style="display:none;"></div>

  <!-- Error Banner -->
  <div id="errorBanner" class="error-banner" style="display:none;"></div>

  <!-- Summary -->
  <div id="summaryArea"></div>

  <!-- Modules -->
  <div id="modulesArea"></div>

  <!-- Empty State -->
  <div id="emptyState" class="empty-state">
    <div class="icon">📋</div>
    <p>点击「运行全部测试」开始执行</p>
  </div>
</div>

<script>
// ── 大模块配置 ───────────────────────────────────────────────────
const MODULE_ORDER = [
  "TestFrontendValidationEmpty",
  "TestPhoneFormatValidation",
  "TestNormalLogin",
  "TestAbnormalLogin",
  "TestAccountLock",
  "TestSystemException",
  "TestWelcomePage",
];

const MODULE_NAMES = {
  "TestFrontendValidationEmpty": "一、前端校验（输入为空）",
  "TestPhoneFormatValidation":   "二、手机号格式校验",
  "TestNormalLogin":             "三、正常登录",
  "TestAbnormalLogin":           "四、异常登录",
  "TestAccountLock":             "五、账号锁定机制",
  "TestSystemException":         "六、系统异常",
  "TestWelcomePage":             "七、欢迎页",
};

const STATUS_MAP = {
  passed:  {icon:"✓", label:"通过"},
  failed:  {icon:"✗", label:"失败"},
  error:   {icon:"!", label:"错误"},
  skipped: {icon:"⊘", label:"跳过"},
};

function getStatusInfo(status) {
  return STATUS_MAP[status] || {icon:"—", label:"未运行"};
}

// ── 页面加载时获取结果 ────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => { loadResults(); });

async function loadResults() {
  try {
    const resp = await fetch("/api/results");
    const data = await resp.json();
    if (data.status === "no_results") {
      renderInitial();
      return;
    }
    renderResults(data);
  } catch(e) {
    renderInitial();
  }
}

function renderInitial() {
  document.getElementById("emptyState").style.display = "block";
  document.getElementById("summaryArea").innerHTML = "";
  document.getElementById("modulesArea").innerHTML = renderModules([]);
  document.getElementById("runtimeInfo").style.display = "none";
  document.getElementById("errorBanner").style.display = "none";
}

// ── 运行全部测试 ─────────────────────────────────────────────────
async function runTests() {
  const btn = document.getElementById("btnRunAll");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>运行中…';

  try {
    const resp = await fetch("/api/run", {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"});
    const data = await resp.json();
    if (data.error && !data.tests) {
      document.getElementById("errorBanner").style.display = "block";
      document.getElementById("errorBanner").textContent = data.error;
      return;
    }
    document.getElementById("errorBanner").style.display = "none";
    renderResults(data);
  } catch(e) {
    document.getElementById("errorBanner").style.display = "block";
    document.getElementById("errorBanner").textContent = "请求失败: " + e.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = "▶ 运行全部测试";
  }
}

// ── 运行单个模块 ─────────────────────────────────────────────────
async function runModule(cls) {
  const btn = document.querySelector(`[data-run-btn="${cls}"]`);
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>'; }

  try {
    const resp = await fetch("/api/run", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({module_class: cls}),
    });
    const data = await resp.json();
    if (data.error && !data.tests) {
      alert(data.error);
      return;
    }
    renderResults(data);
  } catch(e) {
    alert("运行失败: " + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = "▶"; }
  }
}

// ── 渲染结果 ─────────────────────────────────────────────────────
function renderResults(data) {
  document.getElementById("emptyState").style.display = "none";

  // 错误信息
  const eb = document.getElementById("errorBanner");
  if (data.error) {
    eb.style.display = "block";
    eb.textContent = data.error;
  } else {
    eb.style.display = "none";
  }

  // 运行时间信息
  const ri = document.getElementById("runtimeInfo");
  if (data.runTime) {
    const dur = data.duration ? ` · 耗时 ${data.duration}s` : "";
    ri.textContent = `上次运行: ${data.runTime}${dur}`;
    ri.style.display = "block";
  }

  // 汇总面板
  document.getElementById("summaryArea").innerHTML = renderSummary(data.summary);

  // 模块列表
  document.getElementById("modulesArea").innerHTML = renderModules(data.tests || []);
}

// ── 汇总面板 ─────────────────────────────────────────────────────
function renderSummary(s) {
  if (!s || s.total === 0) return "";
  const rate = (s.passed / s.total * 100).toFixed(1);
  const rateColor = rate == 100 ? "var(--green)" : rate > 0 ? "var(--yellow)" : "var(--red)";
  const barColor = rate == 100 ? "var(--green)" : rate > 0 ? "var(--yellow)" : "var(--red)";

  return `
    <div class="summary-grid">
      <div class="card blue"><div class="num">${s.total}</div><div class="label">总测试数</div></div>
      <div class="card green"><div class="num">${s.passed}</div><div class="label">通过</div></div>
      <div class="card red"><div class="num">${s.failed}</div><div class="label">失败</div></div>
      <div class="card orange"><div class="num">${s.error + s.skipped}</div><div class="label">错误/跳过</div></div>
    </div>
    <div class="progress-wrap">
      <div class="progress-info">
        <span>通过率 <strong style="color:${rateColor}">${rate}%</strong></span>
        <span>${s.passed} / ${s.total}</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width:${rate}%;background:${barColor}"></div>
      </div>
    </div>`;
}

// ── 模块列表 ─────────────────────────────────────────────────────
function renderModules(tests) {
  // 按 class 分组
  const groups = {};
  for (const t of tests) {
    if (!groups[t.class]) groups[t.class] = [];
    groups[t.class].push(t);
  }

  let html = "";
  for (const cls of MODULE_ORDER) {
    const items = groups[cls] || [];
    const displayName = MODULE_NAMES[cls] || cls;
    const total = items.length;
    const passed = items.filter(i => i.status === "passed").length;
    const failed = items.filter(i => i.status === "failed" || i.status === "error").length;

    let badgeClass, badgeText;
    if (total === 0) {
      badgeClass = "none";
      badgeText = "未运行";
    } else if (passed === total) {
      badgeClass = "pass";
      badgeText = `全部通过 ${passed}/${total}`;
    } else if (failed === total) {
      badgeClass = "fail";
      badgeText = `全部失败 ${passed}/${total}`;
    } else {
      badgeClass = "partial";
      badgeText = `部分通过 ${passed}/${total}`;
    }

    html += `<div class="module open" data-class="${cls}">`;
    html += `<div class="module-header" onclick="toggleModule(this.parentElement)">`;
    html += `<span class="module-title">${displayName} <span class="module-badge ${badgeClass}">${badgeText}</span></span>`;
    html += `<span class="module-actions">`;
    html += `<button class="btn btn-secondary btn-sm" data-run-btn="${cls}" onclick="event.stopPropagation();runModule('${cls}')" title="运行此模块">▶</button>`;
    html += `<span class="module-arrow">▼</span>`;
    html += `</span></div>`;

    html += `<div class="module-body">`;
    if (items.length > 0) {
      html += `<table class="test-table">`;
      html += `<thead><tr><th class="col-tc">编号</th><th>功能描述</th><th class="col-status">状态</th></tr></thead>`;
      html += `<tbody>`;
      for (const t of items) {
        const info = getStatusInfo(t.status);
        const clickable = (t.status === "failed" || t.status === "error") && t.failure;
        html += `<tr class="test-row${clickable ? " clickable" : ""}" onclick="${clickable ? "toggleFailure(this,'" + escapeId(t.full_name) + "')" : ""}">`;
        html += `<td class="col-tc">${t.tc || "—"}</td>`;
        html += `<td>${escapeHtml(t.display_name || t.name)}</td>`;
        html += `<td class="col-status"><span class="status-icon ${t.status}" title="${info.label}">${info.icon}</span></td>`;
        html += `</tr>`;
        if (clickable) {
          html += `<tr class="failure-detail" id="fail-${escapeId(t.full_name)}"><td colspan="3"><pre>${escapeHtml(t.failure)}</pre></td></tr>`;
        }
      }
      html += `</tbody></table>`;
    } else {
      html += `<div style="padding:20px 36px;color:var(--text-dim);font-size:.85rem;">此模块尚未运行</div>`;
    }
    html += `</div></div>`;
  }
  return html;
}

// ── 交互 ─────────────────────────────────────────────────────────
function toggleModule(el) {
  el.classList.toggle("open");
}

function toggleAll(expand) {
  document.querySelectorAll(".module").forEach(m => {
    expand ? m.classList.add("open") : m.classList.remove("open");
  });
}

function toggleFailure(row, id) {
  const detail = document.getElementById("fail-" + id);
  if (detail) detail.classList.toggle("open");
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text || "";
  return d.innerHTML;
}

function escapeId(s) {
  return (s || "").replace(/[^a-zA-Z0-9_-]/g, "_");
}
</script>
</body>
</html>
"""

# ── 启动入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    port = 5000
    print("=" * 50)
    print("  测试仪表盘已启动")
    print(f"  浏览器访问: http://localhost:{port}")
    print("  按 Ctrl+C 停止")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)
