import json
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

EVENT_KINDS = [
    ("started", "Started"),
    ("step_shown", "Step shown"),
    ("step_done", "Step done"),
    ("deviation", "Went off track"),
    ("show_me", "Asked to be shown"),
    ("help_requested", "Asked for help"),
    ("ai_asked", "Asked the AI"),
    ("completed", "Completed"),
    ("abandoned", "Stopped"),
]

# The UI state the runner reports. Anything else is dropped.
UI_KEYS = ("action_xmlid", "action_id", "client_tag", "model", "view_type", "res_id", "path")


def _matches(expected, ui_state):
    """Every key in `expected` must match the reported UI state. A list value
    means any one of them. A list of dicts means any one of those screens."""
    if not expected:
        return True
    if isinstance(expected, list):
        return any(_matches(e, ui_state) for e in expected)
    for key, want in expected.items():
        have = ui_state.get(key)
        wanted = want if isinstance(want, list) else [want]
        if have not in wanted:
            return False
    return True


class SecurityGuidanceSession(models.Model):
    """One employee working through one guided task.

    The server owns the state machine. The runner (inside the ERP) and the
    desktop side panel only report and render. `report_ui_state` is the one
    place the current step is decided."""

    _name = "security.guidance.session"
    _description = "Guided Task Session"
    _order = "started_at desc, id desc"

    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True, readonly=True)
    flow_id = fields.Many2one("security.guidance.flow", required=True, ondelete="cascade", readonly=True)
    task_id = fields.Many2one("security.work.task", ondelete="set null", readonly=True,
                              help="The real task this guidance is for. Empty in practice mode.")
    practice = fields.Boolean(readonly=True, help="No real task: steps DeployGuard can't verify are confirmed by the employee.")
    context_site_id = fields.Many2one("security.client.site", readonly=True)
    context_date = fields.Date(readonly=True)
    state = fields.Selection(
        [("active", "In progress"), ("completed", "Completed"), ("abandoned", "Stopped")],
        default="active", required=True, index=True,
    )
    current_step_id = fields.Many2one("security.guidance.step", readonly=True)
    reached_step_ids = fields.Many2many(
        "security.guidance.step", string="Steps reached",
        help="Screen-based steps stay done once reached; check-based steps are re-verified every time.",
    )
    ui_state = fields.Text(readonly=True)
    off_track = fields.Boolean(readonly=True)
    highlight_nonce = fields.Integer(readonly=True, help="Bumped by 'Show me' so the runner pulses the target.")
    started_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    completed_at = fields.Datetime(readonly=True)
    event_ids = fields.One2many("security.guidance.event", "session_id", readonly=True)

    # ------------------------------------------------------------------
    # Public API (desktop side panel + ERP runner)
    # ------------------------------------------------------------------

    @api.model
    def start(self, flow_code, task_id=None):
        """Start guidance. With a task, DeployGuard verifies each step against
        that task's real records. Without one it looks for the employee's own
        open task for this flow today, and only falls back to practice mode
        when there is none."""
        flow = self.env["security.guidance.flow"].search([("code", "=", flow_code)], limit=1)
        if not flow:
            raise UserError(self.env._("That guided task isn't available."))
        Task = self.env["security.work.task"]
        task = Task.browse()
        if task_id:
            task = Task.search([("id", "=", int(task_id))], limit=1)  # respects the caller's access
            if not task:
                raise UserError(self.env._("That task isn't one of yours."))
        else:
            task = Task.search([
                ("employee_id.user_id", "=", self.env.uid),
                ("responsibility_id.guidance_flow_code", "=", flow_code),
                ("state", "in", ("open", "in_progress")),
            ], order="due_at", limit=1)

        self.search([("user_id", "=", self.env.uid), ("state", "=", "active")])._finish("abandoned")
        session = self.create({
            "flow_id": flow.id,
            "task_id": task.id or False,
            "practice": not task,
            "context_site_id": task.site_id.id if task else False,
            "context_date": (task.roster_date or (task.due_at and task.due_at.date())) if task else fields.Date.context_today(self),
        })
        if task and task.state == "open":
            task.action_start()
        session._log("started")
        session._advance({})
        return session._payload()

    @api.model
    def get_active(self):
        session = self._mine()
        return session._payload() if session else False

    @api.model
    def report_ui_state(self, ui_state):
        """The runner reports where the employee is; the server answers with
        what to show. Also re-checks the real records."""
        session = self._mine()
        if not session:
            return False
        clean = {k: ui_state.get(k) for k in UI_KEYS if isinstance(ui_state, dict) and ui_state.get(k) not in (None, "")}
        session._advance(clean)
        return session._payload()

    @api.model
    def show_me(self):
        session = self._mine()
        if session:
            session.highlight_nonce += 1
            session._log("show_me")
            return session._payload()
        return False

    @api.model
    def request_help(self):
        session = self._mine()
        if not session:
            return False
        session._log("help_requested")
        step = session.current_step_id
        return {"help_html": step.help_html or False, "deviation_hint": session._fill(step.deviation_hint) or False}

    @api.model
    def confirm_step(self):
        """Practice mode only: the employee confirms a step DeployGuard has no
        real record to check. Never available on a real task."""
        session = self._mine()
        if not session or not session.practice or not session.current_step_id:
            raise UserError(self.env._("DeployGuard checks this step for you. Carry on in the ERP."))
        session.reached_step_ids = [(4, session.current_step_id.id)]
        session._advance(json.loads(session.ui_state or "{}"))
        return session._payload()

    @api.model
    def abandon(self):
        session = self._mine()
        if session:
            session._finish("abandoned")
        return True

    @api.model
    def ask_ai(self, question):
        """Explain the current step in other words. Grounded only in the
        approved flow content; labelled as AI; never advances anything."""
        session = self._mine()
        question = (question or "").strip()[:500]
        if not session or not question:
            raise UserError(self.env._("Ask a question about the step you're on."))
        step = session.current_step_id
        session._log("ai_asked", detail=question)
        sources = [f"Step: {step.name}"] if step else []
        fallback = {
            "ai": False,
            "answer": html2plaintext(step.help_html or "") or step.why or self.env._("Ask your supervisor, or report the problem."),
            "sources": sources,
        }
        if "security.ai.engine" not in self.env:
            return fallback

        flow = session.flow_id
        content = "\n".join(filter(None, [
            f"Task: {flow.name}",
            f"Goal: {flow.objective or ''}",
            f"Why the task exists: {flow.why or ''}",
            f"Current step: {step.name}" if step else "",
            f"Instruction: {session._fill(step.instruction)}" if step else "",
            f"Why this step matters: {step.why or ''}" if step else "",
            f"Help text: {html2plaintext(step.help_html or '')}" if step else "",
        ]))
        system_prompt = (
            "You help an employee of DogForce Security Services while they do a task in the company ERP. "
            "Answer ONLY from the approved task content provided. Never invent steps, buttons, field names, "
            "rules or procedures. If the answer isn't in the content, say you don't know and suggest asking "
            "their supervisor. Use short, plain sentences a new employee understands. Under 90 words."
        )
        try:
            text = self.env["security.ai.engine"].sudo().complete(
                "guidance_explain", system_prompt, f"{content}\n\nEmployee's question: {question}",
                max_tokens=250, temperature=0.2,
            )
        except Exception:  # noqa: BLE001 - AI is optional; the employee still gets the approved help
            _logger.warning("guidance ask_ai failed", exc_info=True)
            text = None
        if not text:
            return fallback
        return {"ai": True, "answer": text.strip(), "sources": sources}

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    @api.model
    def _mine(self):
        return self.search([("user_id", "=", self.env.uid), ("state", "=", "active")], limit=1)

    def _step_done(self, step, ui_state):
        self.ensure_one()
        if step.done_check:
            if self.practice:
                return step in self.reached_step_ids
            return bool(self._run_check(step.done_check))
        done_ui = step._json("done_ui_json", None)
        if done_ui is None:
            return step in self.reached_step_ids
        return step in self.reached_step_ids or _matches(done_ui, ui_state)

    def _run_check(self, name):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name or ""):
            return False
        method = getattr(self, f"_guidance_check_{name}", None)
        if not method:
            _logger.warning("guidance check %s is not implemented", name)
            return False
        return method()

    def _advance(self, ui_state):
        """Pick the first step that isn't done. Screen-reached steps stick;
        record checks are the truth every time."""
        self.ensure_one()
        if self.state != "active":
            return
        steps = self.flow_id.step_ids.sorted(lambda s: (s.sequence, s.id))
        newly_reached = steps.filtered(
            lambda s: not s.done_check and s._json("done_ui_json", None) is not None
            and _matches(s._json("done_ui_json", {}), ui_state)
        )
        if newly_reached:
            self.reached_step_ids = [(4, s.id) for s in newly_reached]

        current = next((s for s in steps if not self._step_done(s, ui_state)), None)
        previous = self.current_step_id
        if previous and previous != current and self._step_done(previous, ui_state):
            self._log("step_done", step=previous)

        vals = {"ui_state": json.dumps(ui_state) if ui_state else self.ui_state}
        if current is None:
            vals.update(current_step_id=False, off_track=False)
            self.write(vals)
            self._finish("completed")
            return

        where = current._json("where_json", {})
        off_track = bool(ui_state) and not _matches(where, ui_state)
        vals.update(current_step_id=current.id, off_track=off_track)
        if current != previous:
            self._log("step_shown", step=current)
        if off_track and not self.off_track:
            self._log("deviation", step=current, detail=json.dumps(ui_state))
        self.write(vals)

    def _finish(self, state):
        for session in self:
            session.write({"state": state, "completed_at": fields.Datetime.now()})
            session._log(state)

    def _log(self, kind, step=None, detail=None):
        self.ensure_one()
        self.env["security.guidance.event"].sudo().create({
            "session_id": self.id,
            "step_id": (step or self.current_step_id).id or False,
            "kind": kind,
            "detail": (detail or "")[:1000] or False,
        })

    def _fill(self, text):
        self.ensure_one()
        if not text:
            return ""
        date = fields.Date.to_string(self.context_date) if self.context_date else ""
        return text.replace("{site}", self.context_site_id.name or "your site").replace("{date}", date)

    def _payload(self):
        self.ensure_one()
        steps = self.flow_id.step_ids.sorted(lambda s: (s.sequence, s.id))
        ui = json.loads(self.ui_state or "{}")
        step = self.current_step_id
        return {
            "id": self.id,
            "state": self.state,
            "practice": self.practice,
            "flow": {"code": self.flow_id.code, "name": self.flow_id.name, "objective": self.flow_id.objective or False,
                     "why": self.flow_id.why or False},
            "task": {"id": self.task_id.id, "name": self.task_id.name, "state": self.task_id.state} if self.task_id else False,
            "site": self.context_site_id.name or False,
            "date": fields.Date.to_string(self.context_date) if self.context_date else False,
            "step": {
                "id": step.id,
                "index": list(steps).index(step) + 1,
                "title": self._fill(step.name),
                "instruction": self._fill(step.instruction),
                "why": step.why or False,
                "has_help": bool(step.help_html),
                "success_message": step.success_message or False,
                "deviation_hint": self._fill(step.deviation_hint) or False,
                "target": step._json("target_json", []),
                "where": step._json("where_json", {}),
                "confirmable": bool(self.practice and step.done_check),
            } if step else False,
            "total": len(steps),
            "steps": [{"title": self._fill(s.name), "done": self.state == "completed" or self._step_done(s, ui)} for s in steps],
            "off_track": self.off_track,
            "highlight_nonce": self.highlight_nonce,
        }


class SecurityGuidanceEvent(models.Model):
    """Operational evidence of guided work: which steps people reach, where
    they go off track, and where they ask for help. It is used to improve
    training and procedures. It holds no mouse, keyboard or screen-time
    data."""

    _name = "security.guidance.event"
    _description = "Guided Task Event"
    _order = "create_date desc, id desc"

    session_id = fields.Many2one("security.guidance.session", required=True, ondelete="cascade", index=True)
    user_id = fields.Many2one(related="session_id.user_id", store=True)
    flow_id = fields.Many2one(related="session_id.flow_id", store=True)
    step_id = fields.Many2one("security.guidance.step", ondelete="set null")
    kind = fields.Selection(EVENT_KINDS, required=True, index=True)
    detail = fields.Char()
