# Agentic Business Automation Platform — Implementation Plan

## Background

The existing project has a solid skeleton:
- **FastAPI** entry point (`main.py`) with a `/chat` endpoint and a `/test` endpoint
- **LangChain + LangGraph + Groq** already in `requirements.txt`
- **SQLAlchemy models** for `User`, `ChatSession`, and `Message` (not yet wired to a DB)
- Empty `agents/` directory and a stub `tools/db_tool.py`
- Basic `ChatService` that simply calls Groq

We will **build on top of this foundation** and transform it into a full **Agentic Business Automation Platform** — no rework of what already exists, only additions and wiring.

---

## What We Are Building

```
User (HTTP Request)
        ↓
  FastAPI Routers  (/agent, /workflow, /chat, /analytics)
        ↓
  Agent Orchestrator  (LangGraph ReAct agent)
        ↓
  Planner  →  Tool Selection  →  Tool Execution  →  Observation
        ↓
  Final Response  +  Audit Log  +  Session Memory
```

---

## Open Questions

> [!IMPORTANT]
> **Do you want a real PostgreSQL database, or SQLite for local development?**
> The models already assume PostgreSQL-style FK relationships — we can wire either. We'll default to **SQLite** (easy, zero-config) and add a `DATABASE_URL` env var so you can swap to PostgreSQL/Docker later.

> [!IMPORTANT]
> **Email sending for invoice reminders** — do you have an SMTP account (Gmail, SendGrid, etc.)? We will implement a real `EmailTool` with SMTP and fall back to a "dry-run" mode if no credentials are set.

> [!IMPORTANT]
> **`services/chat.py` uses model `openai/gpt-oss-120b`** which is a non-standard Groq model name. We'll switch to `llama3-70b-8192` (a valid Groq model) unless you specify otherwise.

---

## Proposed Changes

### Layer 0 — Project Foundation

#### [MODIFY] [requirements.txt](file:///c:/Users/Nimap/Agentic_Bussiness_Automation/requirements.txt)
Add: `sqlalchemy`, `aiosqlite`, `passlib[bcrypt]`, `python-jose`, `httpx`, `alembic`

#### [NEW] `.env` additions
Add `DATABASE_URL`, `SECRET_KEY`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`

---

### Layer 1 — Core Infrastructure

#### [NEW] `src/database/base.py`
SQLAlchemy `Base`, `engine`, `SessionLocal`, `get_db` dependency

#### [NEW] `src/database/init_db.py`
`create_all_tables()` called at app startup — creates DB tables from existing models

#### [MODIFY] [config.py](file:///c:/Users/Nimap/Agentic_Bussiness_Automation/src/core/config.py)
Add `DATABASE_URL`, `SECRET_KEY`, `SMTP_*` settings, fix model name

#### [MODIFY] [main.py](file:///c:/Users/Nimap/Agentic_Bussiness_Automation/main.py)
Add startup event (`create_all_tables`), include new routers (`/agent`, `/workflow`, `/analytics`, `/invoices`)

---

### Layer 2 — Business Domain Models

#### [NEW] `src/models/invoice.py`
`Invoice` table: `id`, `customer_name`, `customer_email`, `amount`, `due_date`, `status` (`paid`/`unpaid`/`overdue`), `created_at`

#### [NEW] `src/models/workflow_run.py`
`WorkflowRun` table: `id`, `workflow_type`, `input_payload`, `status`, `steps_log` (JSON), `result`, `started_at`, `finished_at`

#### [NEW] `src/models/tool_call_log.py`
`ToolCallLog` table: `id`, `run_id`, `tool_name`, `input`, `output`, `latency_ms`, `success`, `timestamp`

---

### Layer 3 — Business Tools (LangChain Tools)

#### [MODIFY] [db_tool.py](file:///c:/Users/Nimap/Agentic_Bussiness_Automation/src/tools/db_tool.py)
`DatabaseTool` — LangChain `@tool` for `get_invoices(status)`, `get_invoice_by_id(id)`, `update_invoice_status(id, status)`

#### [NEW] `src/tools/email_tool.py`
`EmailTool` — `send_email(to, subject, body)` via SMTP (with dry-run fallback)

#### [NEW] `src/tools/search_tool.py`
`SearchTool` — `search_documents(query)` — searches invoices/sessions by keyword

#### [NEW] `src/tools/analytics_tool.py`
`AnalyticsTool` — `generate_report(report_type)` — revenue summary, overdue stats, top customers

#### [NEW] `src/tools/tool_registry.py`
Central registry that exports `ALL_TOOLS` list used by the agent

---

### Layer 4 — Agent Orchestrator (LangGraph ReAct)

#### [NEW] `src/agents/orchestrator.py`
- **ReAct Agent** built with `langgraph` + `create_react_agent`
- Uses `ALL_TOOLS` from tool registry
- Groq LLM as the brain (`llama3-70b-8192`)
- Enforces **step limits** (max 10 steps), **retry logic**, **timeout handling**
- Returns structured `AgentResult` with `steps[]`, `final_answer`, `tool_calls_made`

#### [NEW] `src/agents/planner.py`
- **Planner** that decomposes complex requests into sub-tasks
- Produces a `Plan` (list of steps) before handing off to executor

#### [NEW] `src/agents/memory.py`
- **Conversation memory** using `langgraph` checkpointer
- Stores intermediate agent state per `session_id`
- Session-scoped memory (not global)

#### [NEW] `src/agents/state.py`
- LangGraph `AgentState` TypedDict: `messages`, `plan`, `current_step`, `observations`, `tool_results`

---

### Layer 5 — Services (Business Logic)

#### [NEW] `src/services/agent_service.py`
- `AgentService.run(task: str, session_id: str) → AgentResult`
- Wires orchestrator + memory + DB logging
- Writes `WorkflowRun` and `ToolCallLog` records

#### [NEW] `src/services/invoice_service.py`
- `InvoiceService`: CRUD for invoices, seed demo data

#### [MODIFY] `src/services/chat.py`
- Fix model name to `llama3-70b-8192`
- Add `invoke()` method (currently only `send_message()` exists but `chat.py` calls `invoke()`)

---

### Layer 6 — API Endpoints

#### [NEW] `src/api/v1/agent.py`
```
POST /agent/run          → run a free-form task ("Find unpaid invoices and send reminders")
GET  /agent/history      → list past workflow runs
GET  /agent/run/{run_id} → get specific run details + step log
```

#### [NEW] `src/api/v1/invoices.py`
```
GET  /invoices           → list all invoices (filter by status)
POST /invoices           → create invoice
PUT  /invoices/{id}      → update invoice
POST /invoices/seed      → seed 10 demo invoices
```

#### [NEW] `src/api/v1/analytics.py`
```
GET /analytics/summary   → revenue totals, paid/unpaid counts
GET /analytics/overdue   → overdue invoice list
```

#### [MODIFY] `src/api/v1/chat.py`
Wire to updated `ChatService.invoke()`

---

### Layer 7 — Monitoring & Reliability

#### [NEW] `src/core/middleware.py`
- Request logging middleware (logs method, path, latency)
- Tool usage tracking

#### [NEW] `src/core/exceptions.py`
- Custom `AgentTimeoutError`, `ToolExecutionError`, `PlannerError`
- Global FastAPI exception handlers

---

## Directory Structure After Implementation

```
Agentic_Bussiness_Automation/
├── main.py
├── requirements.txt
├── src/
│   ├── .env
│   ├── agents/
│   │   ├── orchestrator.py     ← ReAct Agent (LangGraph)
│   │   ├── planner.py          ← Task decomposition
│   │   ├── memory.py           ← Conversation/session memory
│   │   └── state.py            ← LangGraph AgentState
│   ├── api/v1/
│   │   ├── agent.py            ← /agent/* endpoints
│   │   ├── invoices.py         ← /invoices/* endpoints
│   │   ├── analytics.py        ← /analytics/* endpoints
│   │   ├── chat.py             ← (existing, fixed)
│   │   └── test_api.py         ← (existing)
│   ├── core/
│   │   ├── config.py           ← (extended)
│   │   ├── middleware.py       ← Request + tool logging
│   │   └── exceptions.py      ← Custom errors
│   ├── database/
│   │   ├── base.py             ← SQLAlchemy engine + SessionLocal
│   │   └── init_db.py          ← create_all_tables()
│   ├── models/
│   │   ├── users.py            ← (existing)
│   │   ├── messege.py          ← (existing)
│   │   ├── session.py          ← (existing)
│   │   ├── invoice.py          ← NEW
│   │   ├── workflow_run.py     ← NEW
│   │   └── tool_call_log.py    ← NEW
│   ├── services/
│   │   ├── chat.py             ← (fixed)
│   │   ├── agent_service.py    ← NEW
│   │   └── invoice_service.py  ← NEW
│   └── tools/
│       ├── db_tool.py          ← (implemented)
│       ├── email_tool.py       ← NEW
│       ├── search_tool.py      ← NEW
│       ├── analytics_tool.py   ← NEW
│       └── tool_registry.py    ← NEW
```

---

## Demo Workflow (End-to-End)

After implementation, this single API call will:
1. Parse the natural-language task
2. Plan sub-steps (Planner)
3. Call `DatabaseTool.get_invoices(status="unpaid")`
4. Call `EmailTool.send_email(...)` for each
5. Log every step with latency
6. Return a final structured response

```http
POST /agent/run
{
  "task": "Find all unpaid invoices and send reminder emails to customers",
  "session_id": "session-abc123"
}
```

---

## Verification Plan

### Automated
- `GET /test/test` — existing sanity check
- `POST /invoices/seed` — seed demo data
- `POST /agent/run` — run the invoice reminder workflow
- `GET /analytics/summary` — verify analytics

### Manual
- Check Groq API calls succeed
- Verify `workflow_runs` and `tool_call_logs` tables are populated
- Inspect step-by-step logs in `GET /agent/run/{run_id}`
