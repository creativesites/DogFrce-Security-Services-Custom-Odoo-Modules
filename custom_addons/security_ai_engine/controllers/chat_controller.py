import json
import re
from datetime import date, timedelta

import requests

from odoo import fields, http
from odoo.http import request


# ── Model allowlist ───────────────────────────────────────────────────────────
# Only models in this set can be queried or written via the assistant.
_ALLOWED_MODELS = {
    "hr.employee",
    "security.attendance.record",
    "security.roster.slot",
    "security.roster.batch",
    "security.client.site",
    "security.post",
    "security.shift.requirement",
    "security.billing.invoice",
    "security.client.payment",
    "security.billing.plan",
    "security.leave.request",
    "security.leave.balance",
    "security.payslip",
    "security.payroll.period",
    "security.employee.loan",
    "security.incident",
    "security.employee.document",
    "security.guard.exclusion",
    "res.partner",
    "security.fleet.run",
    "security.equipment.allocation",
}

# Only action_* methods can be called via propose_method
_METHOD_PREFIX_ALLOWLIST = ("action_",)


# ── Tool definitions for Claude ───────────────────────────────────────────────

_TOOLS = [
    {
        "name": "search_records",
        "description": (
            "Search Odoo records. Use for any factual query about guards, sites, incidents, "
            "payslips, invoices, roster slots, leave requests, documents, etc. "
            "Always call this before stating facts about current data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Odoo model name, e.g. 'hr.employee'"},
                "domain": {"type": "array", "description": "Odoo domain filter (list of triples)", "default": []},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to return"},
                "limit": {"type": "integer", "default": 10, "description": "Max results (max 50)"},
                "order": {"type": "string", "description": "Sort, e.g. 'name asc'", "default": "id desc"},
            },
            "required": ["model", "fields"],
        },
    },
    {
        "name": "count_records",
        "description": "Count records matching a domain. Use before searching to understand scale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "domain": {"type": "array", "default": []},
            },
            "required": ["model"],
        },
    },
    {
        "name": "get_record",
        "description": "Fetch a single Odoo record by its numeric ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "id": {"type": "integer"},
                "fields": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["model", "id", "fields"],
        },
    },
    {
        "name": "get_dashboard_kpis",
        "description": (
            "Get current live operational KPIs: active guards, today's attendance, AWOL count, "
            "unassigned slots, pending leave, open incidents, overdue invoices, revenue MTD."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_pending_actions",
        "description": (
            "Get a summary of all items currently waiting for human action: "
            "pending leaves, open incidents, unassigned slots, draft invoices, expiring docs."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "navigate_to",
        "description": (
            "Produce a clickable navigation chip so the user can open a specific record or "
            "filtered list. Omit 'id' for a list view; include 'domain' to filter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "id": {"type": "integer", "description": "Record ID for form view"},
                "domain": {"type": "array", "description": "Filter for list view"},
                "label": {"type": "string", "description": "Link text shown to user"},
            },
            "required": ["model", "label"],
        },
    },
    {
        "name": "propose_update",
        "description": (
            "Propose writing field values to a record. This will show a confirmation "
            "dialog to the user — DO NOT use this without the user asking you to change something."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "id": {"type": "integer"},
                "vals": {"type": "object", "description": "Fields and values to write"},
                "description": {"type": "string", "description": "Human-readable summary of the change"},
            },
            "required": ["model", "id", "vals", "description"],
        },
    },
    {
        "name": "propose_method",
        "description": (
            "Propose calling an Odoo model method on a record (e.g. action_approve, action_confirm). "
            "Always shows a confirmation dialog before execution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "id": {"type": "integer"},
                "method": {"type": "string", "description": "Method name, must start with 'action_'"},
                "description": {"type": "string", "description": "Human-readable summary of what will happen"},
            },
            "required": ["model", "id", "method", "description"],
        },
    },
]


# ── System prompt builder ─────────────────────────────────────────────────────

def _build_system_prompt(context: dict) -> str:
    ctx_lines = []
    if context.get("active_menu"):
        ctx_lines.append(f"Active menu section: {context['active_menu']}")
    if context.get("url_slug"):
        ctx_lines.append(f"Current page: /{context['url_slug']}")
        if context.get("url_id"):
            ctx_lines.append(f"Current record ID: {context['url_id']}")
    ctx_block = "\n".join(ctx_lines) if ctx_lines else "Home / unknown page"

    return f"""You are the DogForce Security AI Assistant — built into the DogForce Security Services management platform in Namibia.

CURRENT USER CONTEXT:
{ctx_block}

PURPOSE:
Help users find information, navigate to records, make decisions, and take actions within the platform.
You have real-time access to operational data through tools.

RULES:
1. ALWAYS call a tool before stating current facts — never guess counts, names, or figures.
2. NEVER execute writes without user confirmation — use propose_update or propose_method, never write directly.
3. Use navigate_to to provide clickable links rather than telling users to "go to" somewhere.
4. Keep responses concise — use components, not prose paragraphs.
5. If data is ambiguous, search to clarify before answering.

OUTPUT FORMAT — respond ONLY with a JSON object:
{{"summary":"<one sentence>","status":"info|findings|action_required|clean","components":[<component objects>]}}

COMPONENT TYPES:
Standard: alert, metric_row, finding, recommendation, table, section, bullet_list
Chat-specific:
  data_table — clickable table rows that open records:
    {{"type":"data_table","title":"...","headers":["Name","Grade"],"rows":[{{"values":["J. Nangolo","A"],"model":"hr.employee","id":42}}]}}
  record_card — summary card for one record:
    {{"type":"record_card","title":"J. Nangolo","subtitle":"Grade A Guard","fields":[{{"label":"Reliability","value":"87/100"}}],"model":"hr.employee","id":42}}
  navigate — clickable chip to open a record:
    {{"type":"navigate","label":"Open Guard Record →","model":"hr.employee","id":42}}
  navigate_list — clickable chip to open a filtered list:
    {{"type":"navigate_list","label":"View all AWOL →","model":"security.attendance.record","domain":[["absence_type","=","awol"]]}}
  action_confirm — proposed action awaiting confirmation (always use when you call propose_method/propose_update):
    {{"type":"action_confirm","title":"Approve Leave Request","description":"Approve 5-day annual leave for J. Nangolo (LR-041). 2 other guards on leave same week.","action_token":"<from tool result>","danger":false}}
  quick_replies — suggested follow-up questions (always end response with 2-3):
    {{"type":"quick_replies","suggestions":["Who can cover the gap?","Show leave calendar","What's the attendance rate?"]}}
  stat_comparison — side-by-side stats:
    {{"type":"stat_comparison","title":"Revenue Comparison","items":[{{"label":"This month","value":"N$45,200","severity":"success"}},{{"label":"Last month","value":"N$41,000","pct_change":10,"trend":"up"}}]}}"""


# ── Tool executor ─────────────────────────────────────────────────────────────

def _execute_tool(name: str, args: dict, session, env) -> dict:
    uid = env.uid
    today_str = str(date.today())

    if name == "search_records":
        model = args.get("model", "")
        if model not in _ALLOWED_MODELS:
            return {"error": f"Model '{model}' is not accessible via the assistant."}
        try:
            recs = env[model].with_user(uid).search(
                args.get("domain", []),
                limit=min(int(args.get("limit", 10)), 50),
                order=args.get("order", "id desc"),
            )
            return {"records": recs.read(args.get("fields", ["name"])), "total": len(recs)}
        except Exception as e:
            return {"error": str(e)[:300]}

    if name == "count_records":
        model = args.get("model", "")
        if model not in _ALLOWED_MODELS:
            return {"error": f"Model '{model}' is not accessible."}
        try:
            return {"count": env[model].with_user(uid).search_count(args.get("domain", []))}
        except Exception as e:
            return {"error": str(e)[:300]}

    if name == "get_record":
        model = args.get("model", "")
        if model not in _ALLOWED_MODELS:
            return {"error": f"Model '{model}' is not accessible."}
        try:
            rec = env[model].with_user(uid).browse(int(args["id"]))
            if not rec.exists():
                return {"error": "Record not found."}
            return rec.read(args.get("fields", ["name"]))[0]
        except Exception as e:
            return {"error": str(e)[:300]}

    if name == "get_dashboard_kpis":
        try:
            return {
                "active_guards": env["hr.employee"].search_count([["security_guard", "=", True], ["active", "=", True]]),
                "today_present": env["security.attendance.record"].search_count([["shift_date", "=", today_str], ["status", "in", ["present", "late"]]]),
                "today_awol": env["security.attendance.record"].search_count([["shift_date", "=", today_str], ["absence_type", "=", "awol"]]),
                "unassigned_slots": env["security.roster.slot"].search_count([["state", "=", "confirmed"], ["employee_id", "=", False]]),
                "pending_leave": env["security.leave.request"].search_count([["state", "=", "draft"]]),
                "open_incidents": env["security.incident"].search_count([["state", "=", "draft"]]),
                "draft_invoices": env["security.billing.invoice"].search_count([["state", "=", "draft"]]),
                "overdue_invoices": env["security.billing.invoice"].search_count([["state", "not in", ["paid", "cancelled"]], ["due_date", "<", today_str]]),
                "today": today_str,
            }
        except Exception as e:
            return {"error": str(e)[:300]}

    if name == "get_pending_actions":
        try:
            return {
                "pending_leave_requests": env["security.leave.request"].search_count([["state", "=", "draft"]]),
                "open_incidents": env["security.incident"].search_count([["state", "=", "draft"]]),
                "unassigned_slots": env["security.roster.slot"].search_count([["state", "=", "confirmed"], ["employee_id", "=", False]]),
                "draft_invoices": env["security.billing.invoice"].search_count([["state", "=", "draft"]]),
                "overdue_invoices": env["security.billing.invoice"].search_count([["state", "not in", ["paid", "cancelled"]], ["due_date", "<", today_str]]),
                "expiring_documents": env["security.employee.document"].search_count([["expiry_status", "=", "expiring"]]),
                "expired_documents": env["security.employee.document"].search_count([["expiry_status", "=", "expired"]]),
            }
        except Exception as e:
            return {"error": str(e)[:300]}

    if name == "navigate_to":
        return {
            "_navigate": True,
            "label": args.get("label", "Open Record"),
            "model": args.get("model"),
            "id": args.get("id"),
            "domain": args.get("domain"),
        }

    if name in ("propose_update", "propose_method"):
        model = args.get("model", "")
        if model not in _ALLOWED_MODELS:
            return {"error": f"Model '{model}' is not permitted for writes."}
        if name == "propose_method":
            method = args.get("method", "")
            if not any(method.startswith(p) for p in _METHOD_PREFIX_ALLOWLIST):
                return {"error": f"Method '{method}' is not permitted. Only action_* methods are allowed."}
        pending = env["security.ai.chat.message"].sudo().create({
            "session_id": session.id,
            "role": "pending_action",
            "content": name,
            "tool_calls_json": json.dumps({
                "type": "update" if name == "propose_update" else "method",
                "model": args["model"],
                "id": args["id"],
                "vals": args.get("vals"),
                "method": args.get("method"),
                "description": args.get("description", ""),
            }),
        })
        return {
            "action_token": pending.id,
            "description": args.get("description", ""),
            "model": args.get("model"),
            "id": args.get("id"),
        }

    return {"error": f"Unknown tool: {name}"}


# ── Claude multi-turn call ────────────────────────────────────────────────────

def _claude_chat(messages: list, system: str, config) -> dict:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.claude_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.claude_model or "claude-sonnet-4-6",
            "max_tokens": 4096,
            "system": system,
            "messages": messages,
            "tools": _TOOLS,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


# ── Parse AI text → component array ──────────────────────────────────────────

def _parse_components(text: str) -> list:
    """Extract the JSON component array from the AI's final response text."""
    if not text:
        return [{"type": "alert", "variant": "info", "message": "No response from AI."}]
    s = text.strip()
    m = re.search(r"```json\s*([\s\S]*?)\s*```", s)
    if m:
        s = m.group(1).strip()
    start = s.find("{")
    if start >= 0:
        try:
            parsed = json.loads(s[start:])
            return parsed.get("components", [parsed])
        except Exception:
            pass
    return [{"type": "section", "title": "Response", "body": text}]


# ── Agentic loop ──────────────────────────────────────────────────────────────

def _run_agent(session, user_message: str, context: dict, env) -> tuple:
    """
    Multi-turn tool-calling loop.
    Returns (components_list, all_tool_calls_list).
    """
    try:
        config = env["security.ai.config"].get_active_config()
    except Exception:
        return [{"type": "alert", "variant": "danger", "title": "Not Configured",
                 "message": "AI Engine is not configured. Go to Configuration → AI Engine to add your API key."}], []

    system = _build_system_prompt(context)

    # Build message history from session (last 30 exchanges)
    history_msgs = env["security.ai.chat.message"].search(
        [("session_id", "=", session.id), ("role", "in", ("user", "assistant"))],
        order="id asc",
        limit=60,
    )
    messages = []
    for hm in history_msgs:
        if hm.role == "user":
            messages.append({"role": "user", "content": hm.content or ""})
        elif hm.role == "assistant":
            # Include compressed summary of previous AI turns
            prev = hm.components_json
            if prev:
                try:
                    comps = json.loads(prev)
                    summary = next((c.get("message") or c.get("body") or c.get("summary", "")
                                    for c in comps if c.get("type") in ("alert", "section")), "")
                    messages.append({"role": "assistant", "content": summary[:500] or "[previous response]"})
                except Exception:
                    pass

    # Append the new user message (not yet in history)
    messages.append({"role": "user", "content": user_message})

    all_tool_calls = []

    for _round in range(8):
        try:
            response = _claude_chat(messages, system, config)
        except requests.HTTPError as exc:
            return [{"type": "alert", "variant": "danger", "title": "API Error",
                     "message": f"Claude returned an error: {exc.response.status_code}"}], all_tool_calls
        except Exception as exc:
            return [{"type": "alert", "variant": "danger", "title": "Connection Error",
                     "message": str(exc)[:200]}], all_tool_calls

        stop_reason = response.get("stop_reason")
        content_blocks = response.get("content", [])

        if stop_reason == "end_turn":
            text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            return _parse_components(text), all_tool_calls

        if stop_reason == "tool_use":
            tool_results = []
            for block in content_blocks:
                if block.get("type") != "tool_use":
                    continue
                tool_name = block["name"]
                tool_input = block.get("input", {})
                tool_id = block["id"]

                result = _execute_tool(tool_name, tool_input, session, env)
                all_tool_calls.append({"tool": tool_name, "input": tool_input, "result": result})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(result, default=str),
                })

            messages.append({"role": "assistant", "content": content_blocks})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return [{"type": "alert", "variant": "warning", "title": "Limit Reached",
             "message": "The assistant reached the maximum reasoning steps for this query."}], all_tool_calls


# ── HTTP Controller ───────────────────────────────────────────────────────────

class AIChatController(http.Controller):

    # ── Send a message and get a response ──────────────────────────────────

    @http.route("/web/ai-chat/message", type="json", auth="user", methods=["POST"])
    def chat_message(self, session_id=None, message="", context=None):
        env = request.env
        context = context or {}

        # Resolve or create session
        session = None
        if session_id:
            candidate = env["security.ai.chat.session"].sudo().browse(int(session_id))
            if candidate.exists() and candidate.user_id.id == env.uid:
                session = candidate
        if not session:
            session = env["security.ai.chat.session"].sudo().create({
                "user_id": env.uid,
                "context_model": context.get("url_slug") or "",
                "context_id": int(context.get("url_id") or 0),
            })

        # Persist user message BEFORE running agent (so history includes it)
        env["security.ai.chat.message"].sudo().create({
            "session_id": session.id,
            "role": "user",
            "content": message,
        })

        # Run the agentic loop
        components, tool_calls = _run_agent(session, message, context, env)

        # Persist assistant response
        ai_msg = env["security.ai.chat.message"].sudo().create({
            "session_id": session.id,
            "role": "assistant",
            "components_json": json.dumps(components),
            "tool_calls_json": json.dumps(tool_calls, default=str),
        })

        session.sudo().write({"last_activity": fields.Datetime.now()})

        return {
            "session_id": session.id,
            "message_id": ai_msg.id,
            "components": components,
        }

    # ── Confirm a proposed action ──────────────────────────────────────────

    @http.route("/web/ai-chat/confirm", type="json", auth="user", methods=["POST"])
    def chat_confirm(self, action_token=None):
        env = request.env
        if not action_token:
            return {"error": "No action token provided."}

        pending = env["security.ai.chat.message"].sudo().browse(int(action_token))
        if not pending.exists() or pending.role != "pending_action":
            return {"error": "Invalid or expired action token."}
        if pending.session_id.user_id.id != env.uid:
            return {"error": "Permission denied."}

        try:
            action_data = json.loads(pending.tool_calls_json or "{}")
            model = action_data.get("model", "")
            record_id = int(action_data.get("id", 0))

            if model not in _ALLOWED_MODELS:
                return {"error": f"Model '{model}' is not permitted."}

            record = env[model].with_user(env.uid).browse(record_id)
            if not record.exists():
                return {"error": f"Record {model}#{record_id} not found."}

            action_type = action_data.get("type")
            if action_type == "update":
                record.write(action_data.get("vals", {}))
                msg = f"Updated {model} record #{record_id}."
            elif action_type == "method":
                method = action_data.get("method", "")
                if not any(method.startswith(p) for p in _METHOD_PREFIX_ALLOWLIST):
                    return {"error": f"Method '{method}' is not allowed."}
                getattr(record, method)()
                msg = f"Executed {method} on {model} #{record_id}."
            else:
                return {"error": "Unknown action type."}

            pending.sudo().write({"content": "executed"})

            return {
                "success": True,
                "components": [
                    {"type": "alert", "variant": "success",
                     "title": "Done", "message": action_data.get("description") or msg},
                    {"type": "navigate", "label": "Open updated record →",
                     "model": model, "id": record_id},
                    {"type": "quick_replies",
                     "suggestions": ["What changed?", "Show me the record", "Any other actions?"]},
                ],
            }
        except Exception as exc:
            return {"error": str(exc)[:300]}

    # ── Load conversation history ───────────────────────────────────────────

    @http.route("/web/ai-chat/history", type="json", auth="user", methods=["POST"])
    def chat_history(self, session_id=None):
        env = request.env

        if session_id:
            session = env["security.ai.chat.session"].sudo().browse(int(session_id))
            if not session.exists() or session.user_id.id != env.uid:
                return {"session_id": None, "messages": []}
        else:
            session = env["security.ai.chat.session"].sudo().search(
                [("user_id", "=", env.uid)],
                order="last_activity desc",
                limit=1,
            )

        if not session:
            return {"session_id": None, "messages": []}

        msgs = env["security.ai.chat.message"].sudo().search(
            [("session_id", "=", session.id), ("role", "in", ("user", "assistant"))],
            order="id asc",
            limit=60,
        )
        return {
            "session_id": session.id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "components": json.loads(m.components_json) if m.components_json else None,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                }
                for m in msgs
            ],
        }

    # ── New chat session ───────────────────────────────────────────────────

    @http.route("/web/ai-chat/new-session", type="json", auth="user", methods=["POST"])
    def chat_new_session(self):
        env = request.env
        session = env["security.ai.chat.session"].sudo().create({"user_id": env.uid})
        return {"session_id": session.id}
