# 34 — Feedback & Support

> Status: Draft · Owner: Product
>
> This is the "ASSIST" stage of the loop. Its job: make it trivially easy to say "this didn't work", capture enough context that nobody has to ask "what were you doing?", and close the loop back into training, configuration and product fixes.

---

## 1. Feedback capture

### 1.1 Post-task micro-feedback

After completing a checklist or a first-time task:

> How was that? · **Easy** · **Okay** · **Difficult** · **Couldn't complete**

- One tap, dismissible, asked at most once per template per user per week.
- "Difficult" optionally asks "what made it difficult?" with the taxonomy below.
- "Couldn't complete" is *also* a work outcome ([08](08-work-management.md) §2), so the item is never silently missing.

### 1.2 "Something's wrong" (available everywhere)

| Category | Typical routing |
|---|---|
| `dont_understand` | Knowledge article + micro-lesson suggestion; supervisor informed for context |
| `not_working` | Support request with diagnostics; adoption deductions suppressed pending outcome |
| `no_permission` | Tenant admin task (access review); often reveals a provisioning gap |
| `cant_find` | Article + navigation help; repeated hits become a UX issue |
| `my_info_wrong` | HR/admin (ERP data correction, e.g. site assignment, employee record) |
| `slow` | Performance issue with client timings attached |
| `other` | Triage queue |

### 1.3 Context captured automatically

User, roles and scopes, tenant, screen route, current task/checklist and template version, linked ERP record, device and app version, connectivity state, last 5 client errors with codes, correlation id, timestamp — and nothing else. No screenshots by default (the user may attach one), no keystrokes, no free-text scraping ([16](16-security-architecture.md) §9).

## 2. Support workflow

```
feedback/problem → support_request (new)
  → triage (auto-classify V1, human confirm)
  → assigned (HR/admin, tenant admin, or platform support)
  → in_progress → resolved(resolution_code) → [optional] knowledge article created/updated
```

| Field | Notes |
|---|---|
| Categories | Access · Data correction · How-to · Defect · ERP issue · Training · Other |
| Priority | Derived from blocking status (is work overdue because of it?), number of affected users, and severity of the blocked workflow |
| SLA | Tenant-configurable: e.g. blocking issues 4 working hours to first response, 2 working days to resolve |
| Resolution codes | `fixed`, `explained`, `training_assigned`, `config_changed`, `access_granted`, `erp_fault`, `platform_fault`, `not_reproducible`, `duplicate` |
| Visibility | Requester sees status and replies; supervisors see that their team member has an open blocking issue (not its content, unless the requester shares it) |

**`platform_fault` and `erp_fault` resolutions retroactively excuse affected expected work** ([09](09-adoption-engine.md) §2) — the single most important fairness link in the product.

## 3. Knowledge base

- Articles are targeted by role, screen route and workflow key, so "Help" is contextual rather than a search box in the dark.
- Seeded from `security_help` content at onboarding (C-6), then maintained in the Platform.
- Each article: purpose, steps with screenshots from the tenant's own configuration, "common mistakes", and links to the real screen.
- Article usefulness is rated; low-rated and stale articles surface to the content owner.
- V1: AI support assistant answers **only** from approved articles, with citations, and escalates otherwise ([11](11-ai-intelligence.md) §4.5).

## 4. Closing the loop

| Signal | Automatic follow-through |
|---|---|
| Repeated `dont_understand` on one workflow | Training gap recommendation ([07](07-training-platform.md) §8) |
| Repeated `no_permission` | Access review task for tenant admin; provisioning checklist update |
| Repeated `not_working` on one screen | `support.recurring_issue` exception → product defect or configuration fix |
| Feedback "Difficult" clustering on a template | Template review task (wording, item order, evidence burden) |
| Resolution `config_changed` | Prompts a check: should the expectation definition or template change too? |
| Any resolution | Offer to create/update a knowledge article from the answer given |

## 5. Tone and trust

- Every response, automatic or human, starts from the assumption that the person tried.
- Never "user error" in any user-visible text or category name.
- Response templates are reviewed for tone as part of content approval (R-8).
- Employees can see everything recorded about their own reports; nothing about their reports flows into HR or discipline systems.

## 6. Support metrics

| Metric | Use |
|---|---|
| First-response and resolution time vs SLA | Service quality |
| Share of requests resolved by self-service (article opened, no request created) | Deflection |
| Blocking issues open > 1 working day | Direct adoption risk; appears in the manager inbox |
| Requests per 100 expected work items, by workflow | Where the product or configuration fails people |
| Reopen rate | Quality of resolutions |
| Fault-attributed excusals | Honest accounting of how often *we* were the problem |
