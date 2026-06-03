# DogForce AI Engine — Technical Documentation

**Module:** `security_ai_engine`  
**Version:** 19.0.4.0.0  
**Last Updated:** June 2026  
**Author:** Winston Zulu

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Module Structure](#3-module-structure)
4. [AI Features Reference](#4-ai-features-reference)
5. [Global AI Assistant (Chat Panel)](#5-global-ai-assistant-chat-panel)
6. [Component Library](#6-component-library)
7. [Configuration Guide](#7-configuration-guide)
8. [Security Model](#8-security-model)
9. [Response Caching](#9-response-caching)
10. [Multi-Provider Fallback](#10-multi-provider-fallback)
11. [Token Tracking & Cost Management](#11-token-tracking--cost-management)
12. [User Feedback System](#12-user-feedback-system)
13. [Extending the AI Engine](#13-extending-the-ai-engine)
14. [Monitoring & Logs](#14-monitoring--logs)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. System Overview

The DogForce AI Engine is a multi-provider, multi-feature AI orchestration layer built natively into the DogForce Security Services Odoo platform. It provides:

- **10 domain-specific AI features** that plug into existing form views (payslip, employee, invoice, roster batch, attendance record, incident, leave request, employee document)
- **A global AI assistant** — a floating chat panel available on every page, capable of querying live data, navigating the system, and executing actions after confirmation
- **A shared component library** — a structured JSON-based output format that the AI uses to render rich, interactive results consistently across all features
- **Infrastructure** — response caching, multi-provider fallback, prompt versioning, token tracking, and cost estimation

All AI calls are logged for audit and compliance. Every write action requires explicit user confirmation.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Odoo Web Client (OWL)                            │
│                                                                         │
│  Form Views                    Global Chat Panel                        │
│  ┌──────────────────┐          ┌──────────────────────────┐            │
│  │ widget="ai_output"│          │ SecurityAIChatPanel       │            │
│  │ AiOutputWidget    │          │ (main_components registry)│            │
│  └────────┬─────────┘          └────────────┬─────────────┘            │
│           │                                  │                          │
│           └──────────────┬───────────────────┘                         │
│                          │                                              │
│                   AiComponentRenderer                                   │
│            (shared component tree renderer)                             │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │ JSON components
┌──────────────────────────┼──────────────────────────────────────────────┐
│                     Odoo Server (Python)                                │
│                                                                         │
│  One-shot Features              Chat Controller                         │
│  ┌────────────────────┐         ┌──────────────────────────────────┐   │
│  │ security_ai_features│         │ /web/ai-chat/message             │   │
│  │ .py                 │         │ /web/ai-chat/confirm             │   │
│  │ (10 model mixins)   │         │ /web/ai-chat/history             │   │
│  └────────┬────────────┘         │ /web/ai-chat/new-session        │   │
│           │                      └──────────────┬───────────────────┘   │
│           └──────────────┬───────────────────────┘                      │
│                          │                                              │
│                  SecurityAIEngine (Abstract Model)                      │
│                  ┌─────────────────────────────┐                       │
│                  │ complete(feature, prompt, msg)│                       │
│                  │ • Cache lookup               │                       │
│                  │ • Feature flag check         │                       │
│                  │ • Provider call              │                       │
│                  │ • Fallback handling          │                       │
│                  │ • Token logging              │                       │
│                  │ • Cache write                │                       │
│                  └─────────────┬───────────────┘                       │
│                                │                                        │
│              ┌─────────────────┼────────────────┐                      │
│              │                 │                 │                      │
│         Claude Provider   OpenAI Provider   Gemini Provider            │
│         (AIResult namedtuple: text, tokens_in, tokens_out)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Abstract model for the engine | Features call `self.env["security.ai.engine"].complete(...)` from any model without knowing which provider is active |
| `AIResult` namedtuple | Providers return structured data (text + tokens) rather than plain strings, enabling token tracking without changing callers |
| JSON component output | AI is instructed to output structured JSON rather than prose, enabling rich interactive rendering without post-processing |
| Form reload on feature completion | `action_ai_*` methods return `ir.actions.act_window` back to the same record, causing Odoo to re-render the form with fresh data |
| Pending action tokens | Proposed writes are stored in the DB as `pending_action` messages; client receives an opaque token; execution is server-side with full ACL |

---

## 3. Module Structure

```
security_ai_engine/
├── __manifest__.py
├── __init__.py
│
├── models/
│   ├── __init__.py
│   ├── security_ai_cache.py       # Response cache model
│   ├── security_ai_chat.py        # Chat session + message models
│   ├── security_ai_config.py      # Config singleton + AI log model
│   ├── security_ai_engine.py      # Abstract engine facade (caching, fallback, versioning)
│   └── security_ai_features.py    # 10 feature model mixins
│
├── providers/
│   ├── __init__.py
│   ├── base.py                    # AIProviderBase + AIResult namedtuple
│   ├── claude.py                  # Anthropic Claude provider
│   ├── openai_provider.py         # OpenAI provider
│   └── gemini.py                  # Google Gemini provider
│
├── controllers/
│   ├── __init__.py
│   └── chat_controller.py         # HTTP endpoints + agentic loop + tool executor
│
├── views/
│   ├── security_ai_config_views.xml   # Config, log, all 10 inherited form views
│   ├── security_ai_client_actions.xml # AI dashboard client action + menuitem
│   └── security_ai_chat_views.xml     # Chat session admin views
│
├── static/src/
│   ├── css/
│   │   └── ai_chat.css            # Chat panel styles
│   ├── js/
│   │   ├── ai_output_widget.js    # Component library + AiOutputWidget + AiComponentRenderer
│   │   ├── ai_chat_panel.js       # Chat panel OWL component (main_components registry)
│   │   └── ai_admin_config.js     # AI admin dashboard
│   └── xml/
│       ├── ai_output_widget.xml   # Templates for all 13 component types
│       ├── ai_chat_panel.xml      # Chat panel templates
│       └── ai_admin_config.xml    # Admin dashboard templates
│
└── security/
    └── ir.model.access.csv
```

---

## 4. AI Features Reference

All features follow the same pattern:
1. **Fields** added to the target model via `_inherit`
2. **Action method** (`action_ai_*`) collects context data, calls the engine, writes results, returns a form reload
3. **Feedback methods** (`action_ai_*_accept/reject/flag`) write to the feedback selection field
4. **Inherited form view** in `security_ai_config_views.xml` adds button + result section

### Feature Map

| # | Feature | Trigger Model | Button | Feature Flag |
|---|---------|--------------|--------|-------------|
| 1 | Attendance Anomaly Detection | `security.payslip` | AI Anomaly Scan | `feature_attendance_anomaly` |
| 2 | Guard Risk Profiling | `hr.employee` | Run AI Risk Analysis | `feature_risk_profiling` |
| 3 | Billing Auditor | `security.billing.invoice` | AI Billing Audit | `feature_billing_auditor` |
| 4 | Roster Optimizer | `security.roster.batch` | AI Optimize Roster | `feature_roster_optimizer` |
| 5 | Smart Shift Fill | `security.attendance.record` | AI Find Replacement | `feature_shift_fill` |
| 6 | Incident Consequence Advisor | `security.incident` | AI Consequence Advisor | `feature_incident_advisor` |
| 7 | Leave Coverage Check | `security.leave.request` | AI Coverage Check | `feature_leave_coverage` |
| 8 | Document Renewal Letter | `security.employee.document` | Generate Renewal Letter | `feature_doc_renewal_letter` |
| 9 | Guard Performance Review | `hr.employee` | Generate Performance Review | `feature_performance_review` |
| 10 | Payslip Plain-English Explanation | `security.payslip` | Explain My Payslip | `feature_payslip_explain` |

### Fields Added Per Feature

Each feature adds these fields to its target model:

```python
ai_<feature>_<result>   = fields.Text(readonly=True)       # JSON or text result
ai_<feature>_date       = fields.Datetime(readonly=True)   # When analysis was run
ai_<feature>_feedback   = fields.Selection([               # User feedback
    ('pending', 'Pending Review'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
    ('flagged', 'Flagged for Review'),
], default='pending')
```

### Adding a New Feature

1. Add a system prompt constant in `security_ai_features.py`
2. Create a new model class inheriting the target model
3. Add AI result fields and the `action_ai_*` method
4. Add `action_ai_*_accept/reject/flag` feedback methods
5. Register the feature key in `_FEATURE_FLAG_MAP` in `security_ai_engine.py`
6. Add a feature toggle field in `security_ai_config.py`
7. Add the inherited form view in `security_ai_config_views.xml`
8. Add the toggle to the Feature Toggles page in the config form

---

## 5. Global AI Assistant (Chat Panel)

### How It Works

The chat panel is registered as a `main_components` entry, meaning it renders on every page of the Odoo backend. It consists of:

- A **floating toggle button** (bottom-right) that opens/closes the panel
- A **side panel** (400px, slides from the right) with conversation history
- An **input bar** with Enter-to-send and Shift+Enter for newlines

### Agentic Loop

Every message goes through a multi-round tool-calling loop:

```
User message + page context
        ↓
Build conversation history from DB (last 60 messages)
        ↓
POST to Claude with 7 tools defined
        ↓
Claude returns tool_use blocks
        ↓
Controller executes each tool against ORM (with user ACL)
        ↓
Tool results sent back to Claude as tool_result blocks
        ↓
(Repeat up to 8 rounds)
        ↓
Claude returns end_turn with final JSON response
        ↓
Parse JSON → component array → save to DB → return to OWL
```

### Available Tools

| Tool | Returns | Confirmation Required |
|------|---------|----------------------|
| `search_records` | Array of record dicts | No |
| `count_records` | `{count: N}` | No |
| `get_record` | Single record dict | No |
| `get_dashboard_kpis` | Live KPI summary | No |
| `get_pending_actions` | Pending counts per category | No |
| `navigate_to` | Navigate component (user clicks) | No — user initiates |
| `propose_update` | Stores pending action, returns token | Yes — `action_confirm` component |
| `propose_method` | Stores pending action, returns token | Yes — `action_confirm` component |

### Allowed Model Allowlist

The controller only allows queries/writes against these 20 models:

```
hr.employee, security.attendance.record, security.roster.slot,
security.roster.batch, security.client.site, security.post,
security.shift.requirement, security.billing.invoice,
security.client.payment, security.billing.plan,
security.leave.request, security.leave.balance,
security.payslip, security.payroll.period,
security.employee.loan, security.incident,
security.employee.document, security.guard.exclusion,
res.partner, security.fleet.run, security.equipment.allocation
```

### Session Persistence

- Sessions are stored in `security.ai.chat.session` (one per user)
- Messages stored in `security.ai.chat.message`
- The OWL panel stores `session_id` in `localStorage` (`dogforce_ai_session`)
- On panel open, history is loaded from `/web/ai-chat/history`
- "New Chat" creates a fresh session and clears localStorage

### Context Injection

The OWL panel reads the current URL and active menu on every message:

```javascript
get currentContext() {
    const path = window.location.pathname;
    const m = path.match(/\/odoo\/([^/]+)(?:\/(\d+))?/);
    return {
        current_url: path,
        url_slug: m ? m[1] : null,
        url_id: m && m[2] ? parseInt(m[2]) : null,
        active_menu: document.querySelector(".o_menu_brand")?.textContent?.trim(),
    };
}
```

This context is injected into the system prompt so the AI understands where the user is.

---

## 6. Component Library

All AI output — both from the 10 features and the chat panel — uses a shared JSON schema. The AI is instructed to return this format in every system prompt.

### Schema

```json
{
  "summary": "<one sentence — the single most important takeaway>",
  "status": "clean | findings | info | action_required",
  "confidence": 4,
  "components": [ <component objects> ]
}
```

### Component Types

#### Standard (available in all contexts)

| Type | JSON Schema |
|------|-------------|
| `alert` | `{"type":"alert","variant":"success\|info\|warning\|danger","title":"...","message":"..."}` |
| `metric_row` | `{"type":"metric_row","metrics":[{"label":"...","value":"...","trend":"up\|down\|stable","severity":"success\|warning\|danger\|info"}]}` |
| `finding` | `{"type":"finding","severity":"CRITICAL\|WARNING\|INFO","title":"...","detail":"...","recommendation":"..."}` |
| `recommendation` | `{"type":"recommendation","action":"...","reason":"...","guard":"...","post":"...","date":"..."}` |
| `table` | `{"type":"table","title":"...","headers":["Col1"],"rows":[["val"]]}` |
| `section` | `{"type":"section","title":"...","body":"..."}` |
| `bullet_list` | `{"type":"bullet_list","title":"...","items":["item 1","item 2"]}` |

#### Navigation & Data (available in all contexts, interactive)

| Type | JSON Schema |
|------|-------------|
| `data_table` | `{"type":"data_table","title":"...","headers":["Name"],"rows":[{"values":["val"],"model":"hr.employee","id":42}]}` |
| `record_card` | `{"type":"record_card","title":"...","subtitle":"...","fields":[{"label":"...","value":"..."}],"model":"hr.employee","id":42}` |
| `navigate` | `{"type":"navigate","label":"Open record →","model":"hr.employee","id":42}` |
| `navigate_list` | `{"type":"navigate_list","label":"View all →","model":"security.attendance.record","domain":[...]}` |
| `stat_comparison` | `{"type":"stat_comparison","title":"...","items":[{"label":"...","value":"...","severity":"...","pct_change":10,"trend":"up"}]}` |

#### Chat-Only (require callbacks — only rendered by `AiComponentRenderer`)

| Type | JSON Schema |
|------|-------------|
| `action_confirm` | `{"type":"action_confirm","title":"...","description":"...","action_token":"<token>","danger":false}` |
| `quick_replies` | `{"type":"quick_replies","suggestions":["Question 1?","Question 2?"]}` |

### OWL Components

| OWL Component | Purpose |
|---------------|---------|
| `AiOutputWidget` | Field widget (`widget="ai_output"`) — reads from record field, renders standard + navigation types |
| `AiComponentRenderer` | Standalone renderer — takes `components` prop directly, renders all 13 types including chat-only |

#### Using `AiOutputWidget` in a form view

```xml
<field name="ai_anomaly_narrative" widget="ai_output" readonly="1" nolabel="1"/>
```

#### Using `AiComponentRenderer` in OWL

```javascript
import { AiComponentRenderer } from "@security_ai_engine/js/ai_output_widget";

// In template:
// <AiComponentRenderer
//     components="myComponents"
//     onQuickReply="(q) => this.handleReply(q)"
//     onConfirmAction="(t) => this.handleConfirm(t)"
// />
```

---

## 7. Configuration Guide

### Initial Setup

1. Go to **Configuration → AI Engine → Configuration**
2. Click **New** to create a configuration record
3. Set **Active Provider** (Claude recommended for best results)
4. Enter the corresponding API key
5. Click **Test Connection** to verify

### Configuration Fields

| Field | Description | Default |
|-------|-------------|---------|
| `active_provider` | Primary AI provider | `claude` |
| `claude_model` | Claude model version | `claude-sonnet-4-6` |
| `openai_model` | OpenAI model version | `gpt-4o` |
| `gemini_model` | Gemini model version | `gemini-2.5-flash` |
| `max_tokens` | Max response length | `2500` |
| `temperature` | Response creativity (0–1) | `0.2` |
| `fallback_provider` | Secondary provider on failure | `none` |
| `enable_response_cache` | Cache identical queries | `True` |
| `cache_ttl_hours` | Cache freshness window | `24` |

### Feature Toggles

Each of the 10 features can be independently enabled or disabled from the **Feature Toggles** page of the config form. Disabled features silently return `None` without making an API call.

### Recommended Models by Task

| Task type | Recommended model |
|-----------|------------------|
| Analytical (anomaly, audit, risk) | `claude-sonnet-4-6` or `gpt-4o` |
| Creative (letters, reviews, explanations) | `claude-opus-4-8` |
| High-volume / cost-sensitive | `claude-haiku-4-5` or `gpt-4o-mini` |
| Chat assistant | `claude-sonnet-4-6` (best tool-calling) |

---

## 8. Security Model

### Access Control

| Model | Admin (group_system) | User (group_user) |
|-------|---------------------|-------------------|
| `security.ai.config` | Full CRUD | Read only |
| `security.ai.log` | Full CRUD | Read only |
| `security.ai.cache` | Full CRUD | Read only |
| `security.ai.chat.session` | Full CRUD | Full CRUD (own sessions only) |
| `security.ai.chat.message` | Full CRUD | Full CRUD (own sessions only) |

### Chat Panel Security

- Session ownership is checked on every request — users can only read/write their own sessions
- The model allowlist prevents the AI from querying models outside the permitted set (e.g., `res.users`, `ir.rule`, `mail.message`)
- Only `action_*` methods can be called via `propose_method` — no arbitrary Python execution
- All writes use `env[model].with_user(uid)` — Odoo's standard ACL is fully enforced
- Pending actions are stored server-side and referenced by integer ID — clients cannot forge action payloads

### API Key Storage

API keys are stored in `security.ai.config` with `password=True` on the field definition, which:
- Masks the value in the UI (shows `*****`)
- Prevents the value from being included in `read()` responses
- Prevents export via standard Odoo export tools

---

## 9. Response Caching

When `enable_response_cache = True`, the engine computes a SHA-256 hash of:

```
feature + "\x00" + system_prompt + "\x00" + user_message
```

Before making any API call, it checks `security.ai.cache` for a matching entry within the TTL window. On cache hit:
- Zero API cost
- Near-instant response
- Logged with `cache_hit = True` and `estimated_cost_usd = 0`

Cache entries are stored indefinitely but only served within the TTL. Admins can view and clear the cache from **Configuration → AI Engine → Response Cache**.

**When to clear the cache:**
- After updating system prompts (prompt_version will differ, so old cache entries won't match)
- After a data migration where historical context should be re-evaluated
- When AI responses seem stale

---

## 10. Multi-Provider Fallback

Set `fallback_provider` to a provider other than `active_provider`. If the primary provider raises any exception (network error, rate limit, model unavailable):

1. The engine logs the primary error
2. Resolves the fallback provider's API key from the same config record
3. Retries the identical call with the fallback provider
4. If the fallback also fails, logs both errors and returns `None`
5. The log entry's `provider` field reflects whichever provider ultimately served the response

The fallback uses the already-configured API keys — no separate key fields are needed.

---

## 11. Token Tracking & Cost Management

Every successful API call logs:

| Field | Description |
|-------|-------------|
| `tokens_in` | Input tokens sent to the provider |
| `tokens_out` | Output tokens returned by the provider |
| `estimated_cost_usd` | Calculated from per-model rate table |
| `prompt_version` | First 12 characters of SHA-256 of the system prompt |

### Cost Rate Table (approximate 2025 pricing)

| Model | Input ($/1K tokens) | Output ($/1K tokens) |
|-------|--------------------|--------------------|
| `claude-opus-4-8` | $0.015 | $0.075 |
| `claude-sonnet-4-6` | $0.003 | $0.015 |
| `claude-haiku-4-5` | $0.0008 | $0.004 |
| `gpt-4o` | $0.005 | $0.015 |
| `gpt-4o-mini` | $0.00015 | $0.0006 |
| `gemini-2.5-flash` | $0.00075 | $0.003 |

Month-to-date aggregates (tokens + cost) are computed on the config record and visible in the **Usage & Cost** tab.

---

## 12. User Feedback System

Every AI result panel includes three feedback buttons:

- **Accept** — marks the result as validated and acted upon
- **Reject** — marks the result as incorrect or unhelpful
- **Flag for Review** — marks the result as needing human review before acting

Feedback is stored as a selection field on the record (e.g., `ai_anomaly_feedback`). Once a feedback state is set, the corresponding button is hidden to prevent double-clicking.

Feedback data can be used to:
- Audit AI quality over time
- Identify features with high rejection rates (prompt tuning needed)
- Provide evidence for disciplinary actions supported by AI recommendations

---

## 13. Extending the AI Engine

### Adding a new one-shot feature

```python
# security_ai_features.py

_MY_FEATURE_SYSTEM = (
    "You are a [role] for DogForce Security. [task description]."
    + _COMPONENT_LIBRARY  # always append this
)

class MyTargetModel(models.Model):
    _inherit = "my.target.model"

    ai_my_result = fields.Text(string="AI Result", readonly=True)
    ai_my_date = fields.Datetime(string="Analysis Date", readonly=True)
    ai_my_feedback = fields.Selection(_FEEDBACK_STATES, default="pending")

    def action_ai_my_feature(self):
        engine = self.env["security.ai.engine"]
        self.ensure_one()
        
        data = {
            # ... collect context data ...
        }
        
        response = engine.complete(
            feature="my_feature",         # must match key in _FEATURE_FLAG_MAP
            system_prompt=_MY_FEATURE_SYSTEM,
            user_message=json.dumps(data, default=str),
        )
        if response:
            self.write({
                "ai_my_result": response,
                "ai_my_date": fields.Datetime.now(),
                "ai_my_feedback": "pending",
            })
        
        return _reload_form(self)  # always reload to show results

    def action_ai_my_accept(self):
        self.ai_my_feedback = "accepted"
        return _reload_form(self)
    
    # ... reject, flag methods ...
```

Then register in `security_ai_engine.py`:

```python
_FEATURE_FLAG_MAP = {
    ...
    "my_feature": "feature_my_feature",
}
```

And add a toggle field to `security_ai_config.py`:

```python
feature_my_feature = fields.Boolean(default=True, string="My Feature Name")
```

### Adding a new chat tool

In `controllers/chat_controller.py`:

1. Add to `_TOOLS` list with name, description, and input_schema
2. Add a handler branch in `_execute_tool()`
3. Optionally add to `_ALLOWED_MODELS` if the tool queries a new model

---

## 14. Monitoring & Logs

### AI Call Logs

Every API call (including cache hits) is recorded in `security.ai.log`. Access via:
**Configuration → AI Engine → Call Logs**

Key fields to monitor:

| Field | What to watch for |
|-------|------------------|
| `state` | `error` — increase = API or auth problem |
| `duration_ms` | Very high values (>10s) = slow provider |
| `estimated_cost_usd` | Unexpected spikes = runaway features |
| `cache_hit` | Low ratio = cache not effective, consider raising TTL |
| `prompt_version` | Changed unexpectedly = system prompt modified |

### Chat Session Log

Chat sessions with full message history are at:
**Configuration → AI Engine → Chat Sessions**

Useful for:
- Auditing what actions the AI proposed and what users confirmed
- Debugging unexpected tool call behaviour
- Reviewing conversation quality for prompt tuning

---

## 15. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "No active AI Engine configuration found" | No config record exists or `active = False` | Create and activate a config record |
| "AI provider authentication failed" | Wrong API key | Update API key; use **Test Connection** |
| AI button visible but nothing happens | Feature toggle disabled | Enable in Config → Feature Toggles |
| Form doesn't show AI result after clicking button | Odoo cache | Hard refresh (Ctrl+Shift+R); check that action returns `_reload_form` |
| AI returns plain text instead of components | Old response in cache; or AI didn't follow format | Clear cache; check system prompt includes `_COMPONENT_LIBRARY` |
| Chat panel shows "Claude returned an error: 400" | Message too long for context window | Start a new chat; reduce conversation length |
| Cost is higher than expected | Cache not hit; model is expensive | Enable cache; switch to `claude-haiku-4-5` for high-volume features |
| `propose_method` fails with "Method not permitted" | Method doesn't start with `action_` | Only action_ methods can be called via AI |
