/* Axiom — Frontend Application */

const API = "";

const state = {
  chatSessionId: null,
  pendingRunId: null,
  agentSessionId: crypto.randomUUID(),
};

// ── Utilities ────────────────────────────────────────────────────────────────

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function fmtMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n || 0);
}

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function fmtMs(ms) {
  if (!ms) return "—";
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function truncate(s, len = 60) {
  if (!s) return "";
  return s.length > len ? s.slice(0, len) + "…" : s;
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function showLoader(text = "Processing…") {
  $("#loader-text").textContent = text;
  $("#loader").hidden = false;
}

function hideLoader() {
  $("#loader").hidden = true;
}

function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Navigation ───────────────────────────────────────────────────────────────

$$(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".nav-item").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const view = btn.dataset.view;
    $$(".view").forEach((v) => v.classList.remove("active"));
    $(`#view-${view}`).classList.add("active");
    if (view === "dashboard") loadDashboard();
    if (view === "invoices") loadInvoices();
    if (view === "logs") loadLogs();
    if (view === "agent") loadAgentHistory();
  });
});

// ── Dashboard ───────────────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const data = await api("/analytics/summary");
    const inv = data.invoices || {};
    const byStatus = inv.by_status || {};

    $("#dashboard-stats").innerHTML = `
      <div class="stat-card" style="--accent: var(--mint)">
        <div class="label">Revenue Collected</div>
        <div class="value">${fmtMoney(inv.total_revenue_collected)}</div>
        <div class="sub">Paid invoices</div>
      </div>
      <div class="stat-card" style="--accent: var(--amber)">
        <div class="label">Outstanding</div>
        <div class="value">${fmtMoney(inv.total_outstanding)}</div>
        <div class="sub">Unpaid + overdue</div>
      </div>
      <div class="stat-card" style="--accent: var(--violet)">
        <div class="label">Workflow Runs</div>
        <div class="value">${Object.values(data.workflow_runs || {}).reduce((a, b) => a + b, 0)}</div>
        <div class="sub">Total executions</div>
      </div>
      <div class="stat-card" style="--accent: var(--coral)">
        <div class="label">Tool Calls</div>
        <div class="value">${Object.values(data.tool_usage || {}).reduce((a, b) => a + b, 0)}</div>
        <div class="sub">Across all agents</div>
      </div>
    `;

    const maxAmt = Math.max(...Object.values(byStatus).map((s) => s.total_amount || 0), 1);
    $("#invoice-chart").innerHTML = Object.entries(byStatus).map(([status, s]) => `
      <div class="bar-row">
        <span>${status}</span>
        <div class="bar-track">
          <div class="bar-fill ${status}" style="width:${((s.total_amount || 0) / maxAmt) * 100}%"></div>
        </div>
        <span class="mono">${fmtMoney(s.total_amount)}</span>
      </div>
    `).join("") || "<p style='color:var(--muted)'>No invoice data. Seed demo data from Invoices tab.</p>";

    $("#top-customers").innerHTML = (data.top_customers || []).map((c) => `
      <div class="list-item">
        <span>${c.customer}</span>
        <span class="amount">${fmtMoney(c.total_amount)}</span>
      </div>
    `).join("") || "<p style='color:var(--muted)'>No customers yet.</p>";

    $("#tool-usage").innerHTML = Object.entries(data.tool_usage || {}).map(([tool, count]) => `
      <span class="chip-stat"><strong>${count}</strong> × ${tool}</span>
    `).join("") || "<span style='color:var(--muted)'>No tool usage yet.</span>";
  } catch (e) {
    toast(`Dashboard error: ${e.message}`, "error");
  }
}

$("#btn-refresh-dashboard").addEventListener("click", loadDashboard);

// ── Agent Studio ────────────────────────────────────────────────────────────

function renderPlan(plan, status = "awaiting_approval") {
  $("#plan-panel").hidden = false;
  $("#plan-status").textContent = status.replace(/_/g, " ");
  $("#plan-status").className = `badge ${status}`;
  $("#plan-steps").innerHTML = plan.map((step, i) =>
    `<li style="animation-delay:${i * 0.08}s">${step}</li>`
  ).join("");
  $(".approval-bar").style.display = status === "awaiting_approval" ? "flex" : "none";
}

function renderAgentResult(data) {
  $("#agent-result").hidden = false;
  $("#result-meta").innerHTML = `
    <span>Run <strong>#${data.run_id}</strong></span>
    <span>Status <strong>${data.status || (data.success ? "completed" : "failed")}</strong></span>
    <span>Duration <strong>${fmtMs(data.duration_ms)}</strong></span>
    <span>Tools <strong>${(data.tool_calls_made || []).join(", ") || "none"}</strong></span>
  `;

  const steps = data.steps || [];
  $("#execution-timeline").innerHTML = steps.length
    ? steps.map((s) => `
        <div class="timeline-item ${s.type}">
          <span class="mono">${s.type}</span>
          <span>${s.tool ? `<strong>${s.tool}</strong>: ` : ""}${truncate(s.input || s.output || "", 120)}</span>
        </div>
      `).join("")
    : "<p style='color:var(--muted)'>No step details.</p>";

  $("#final-answer").textContent = data.final_answer || data.message || "No output.";
}

async function generatePlan() {
  const task = $("#agent-task").value.trim();
  if (!task) { toast("Enter a task first.", "error"); return; }

  showLoader("Generating plan…");
  $("#agent-result").hidden = true;
  try {
    const data = await api("/agent/plan", {
      method: "POST",
      body: JSON.stringify({ task, session_id: state.agentSessionId }),
    });
    state.pendingRunId = data.run_id;
    renderPlan(data.plan, data.status);
    toast("Plan ready — review and approve.", "success");
  } catch (e) {
    toast(`Plan failed: ${e.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function approvePlan(approved) {
  if (!state.pendingRunId) { toast("No pending plan.", "error"); return; }

  showLoader(approved ? "Executing approved plan…" : "Rejecting…");
  try {
    const data = await api("/agent/approve", {
      method: "POST",
      body: JSON.stringify({ run_id: state.pendingRunId, approved }),
    });

    if (!approved) {
      renderPlan(data.plan || [], "rejected");
      toast("Plan rejected. No actions executed.", "info");
    } else {
      renderPlan(data.plan || [], data.status || "completed");
      renderAgentResult(data);
      toast("Execution complete!", "success");
      loadAgentHistory();
    }
    state.pendingRunId = null;
  } catch (e) {
    toast(`Approval failed: ${e.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function quickRun() {
  const task = $("#agent-task").value.trim();
  if (!task) { toast("Enter a task first.", "error"); return; }

  showLoader("Running agent (no approval)…");
  $("#plan-panel").hidden = true;
  try {
    const data = await api("/agent/run", {
      method: "POST",
      body: JSON.stringify({ task, session_id: state.agentSessionId }),
    });
    renderPlan(data.plan || [], data.success ? "completed" : "failed");
    renderAgentResult(data);
    toast("Quick run complete.", "success");
    loadAgentHistory();
  } catch (e) {
    toast(`Run failed: ${e.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function loadAgentHistory() {
  try {
    const runs = await api("/agent/history?limit=15");
    $("#agent-history").innerHTML = `
      <table>
        <thead><tr>
          <th>ID</th><th>Task</th><th>Status</th><th>Duration</th><th>Started</th>
        </tr></thead>
        <tbody>${runs.map((r) => `
          <tr>
            <td class="mono">#${r.run_id}</td>
            <td>${truncate(r.input_payload, 50)}</td>
            <td><span class="status-tag ${r.status}">${r.status}</span></td>
            <td class="mono">${fmtMs(r.duration_ms)}</td>
            <td class="mono">${fmtDate(r.started_at)}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    `;
  } catch (e) {
    $("#agent-history").innerHTML = `<p style="color:var(--muted)">${e.message}</p>`;
  }
}

$("#btn-generate-plan").addEventListener("click", generatePlan);
$("#btn-approve").addEventListener("click", () => approvePlan(true));
$("#btn-reject").addEventListener("click", () => approvePlan(false));
$("#btn-quick-run").addEventListener("click", quickRun);

$$(".quick-tasks .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    $("#agent-task").value = chip.dataset.task;
  });
});

// ── Chat ────────────────────────────────────────────────────────────────────

function appendBubble(role, text) {
  const welcome = $(".chat-welcome");
  if (welcome) welcome.remove();
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  $("#chat-messages").appendChild(div);
  $("#chat-messages").scrollTop = $("#chat-messages").scrollHeight;
  return div;
}

function createStreamingBubble() {
  const welcome = $(".chat-welcome");
  if (welcome) welcome.remove();
  const div = document.createElement("div");
  div.className = "bubble assistant streaming";
  $("#chat-messages").appendChild(div);
  return div;
}

function scrollChat() {
  const el = $("#chat-messages");
  el.scrollTop = el.scrollHeight;
}

async function consumeChatStream(url) {
  const bubble = createStreamingBubble();
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      const data = JSON.parse(line.slice(6));

      if (data.token) {
        bubble.textContent += data.token;
        scrollChat();
      }
      if (data.error) {
        bubble.textContent = `Error: ${data.error}`;
        bubble.classList.remove("streaming");
        throw new Error(data.error);
      }
      if (data.done && data.session_id) {
        state.chatSessionId = data.session_id;
        $("#chat-session-display").textContent = data.session_id;
      }
    }
  }

  bubble.classList.remove("streaming");
  scrollChat();
}

async function sendChat() {
  const input = $("#chat-input");
  const message = input.value.trim();
  if (!message) return;

  appendBubble("user", message);
  input.value = "";
  $("#btn-send-chat").disabled = true;

  try {
    const encoded = encodeURIComponent(message);
    const url = state.chatSessionId
      ? `/chat/stream/${state.chatSessionId}?message=${encoded}`
      : `/chat/stream?message=${encoded}`;
    await consumeChatStream(url);
  } catch (e) {
    appendBubble("assistant", `Error: ${e.message}`);
    toast(`Chat error: ${e.message}`, "error");
  } finally {
    $("#btn-send-chat").disabled = false;
    $("#chat-input").focus();
  }
}

$("#btn-send-chat").addEventListener("click", sendChat);
$("#chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});

// ── Invoices ────────────────────────────────────────────────────────────────

async function loadInvoices() {
  const status = $("#invoice-filter").value;
  const qs = status ? `?status=${status}` : "";
  try {
    const invoices = await api(`/invoices/${qs || ""}`);
    $("#invoices-table").innerHTML = invoices.length ? `
      <table>
        <thead><tr>
          <th>ID</th><th>Customer</th><th>Email</th><th>Amount</th><th>Status</th><th>Due</th>
        </tr></thead>
        <tbody>${invoices.map((inv) => `
          <tr>
            <td class="mono">#${inv.id}</td>
            <td>${inv.customer_name}</td>
            <td class="mono">${inv.customer_email}</td>
            <td class="mono">${fmtMoney(inv.amount)}</td>
            <td><span class="status-tag ${inv.status}">${inv.status}</span></td>
            <td class="mono">${fmtDate(inv.due_date)}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    ` : "<p style='color:var(--muted);padding:1rem'>No invoices. Click Seed Demo Data.</p>";
  } catch (e) {
    toast(`Invoices error: ${e.message}`, "error");
  }
}

$("#invoice-filter").addEventListener("change", loadInvoices);

$("#btn-seed-invoices").addEventListener("click", async () => {
  showLoader("Seeding invoices…");
  try {
    const data = await api("/invoices/seed", { method: "POST" });
    toast(data.message, "success");
    loadInvoices();
  } catch (e) {
    toast(`Seed failed: ${e.message}`, "error");
  } finally {
    hideLoader();
  }
});

// ── Activity Logs ───────────────────────────────────────────────────────────

async function loadLogs() {
  const type = $("#log-filter").value;
  const qs = type ? `?log_type=${type}` : "";
  try {
    const logs = await api(`/logs/${qs}`);
    $("#logs-table").innerHTML = logs.length ? `
      <table>
        <thead><tr>
          <th>ID</th><th>Type</th><th>Model</th><th>Tokens</th><th>Latency</th><th>Task / Message</th><th>Time</th>
        </tr></thead>
        <tbody>${logs.map((l) => `
          <tr>
            <td class="mono">#${l.id}</td>
            <td><span class="status-tag ${l.log_type}">${l.log_type}</span></td>
            <td class="mono">${truncate(l.model_name, 20)}</td>
            <td class="mono">${l.total_tokens}</td>
            <td class="mono">${fmtMs(l.latency_ms)}</td>
            <td>${truncate(l.task || l.message, 45)}</td>
            <td class="mono">${fmtDate(l.created_at)}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    ` : "<p style='color:var(--muted);padding:1rem'>No activity logs yet.</p>";
  } catch (e) {
    toast(`Logs error: ${e.message}`, "error");
  }
}

$("#log-filter").addEventListener("change", loadLogs);

// ── Init ────────────────────────────────────────────────────────────────────

loadDashboard();
