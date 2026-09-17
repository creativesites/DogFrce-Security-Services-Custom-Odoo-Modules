import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ChecklistItemDef,
  ChecklistResponse,
  WorkTask,
  RosterSignoff,
  fetchChecklistItems,
  fetchChecklistResponses,
  fetchCncReasonOptions,
  fetchMyTasks,
  fetchPendingRosterSignoffs,
  signRosterBatch,
  fetchTask,
  resolveEmployeeId,
  runWorkAction,
  saveChecklistResponse,
} from "../../api/work";
import { extractErrorMessage } from "../../lib/extractErrorMessage";
import { invoke } from "../../lib/tauri";
import { useSession } from "../../session/SessionContext";
import {
  STATE_LABELS,
  WorkAction,
  availableActions,
  byDueDateAscending,
  dueBadgeTone,
  isOverdue,
  parseOdooDatetime,
  formatRosterRole,
} from "./myWork.logic";
import { AlertTriangleIcon, CheckCircleIcon, ClipboardListIcon } from "../icons";

type LoadState = "loading" | "ready" | "error";

function formatDue(dueAt: string | false): string {
  if (!dueAt) return "No due date";
  const parsed = parseOdooDatetime(dueAt);
  if (!parsed) return "No due date";
  return parsed.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function DueBadge({ task }: { task: WorkTask }) {
  const tone = dueBadgeTone(task.due_at, task.state);
  const overdue = isOverdue(task.due_at, task.state);
  const style: Record<string, string> =
    tone === "danger"
      ? { background: "var(--ds-danger-bg)", color: "var(--ds-danger)" }
      : tone === "warning"
        ? { background: "var(--ds-warning-bg)", color: "var(--ds-warning)" }
        : { background: "var(--ds-slate)", color: "var(--ds-text-muted)" };
  return (
    <span className="dg-chip" style={style}>
      {overdue ? "Overdue · " : ""}
      {formatDue(task.due_at)}
    </span>
  );
}

/**
 * The employee's own work queue: `security.work.task` rows assigned to
 * them, a detail view with the workflow actions valid from that task's
 * current state, and (when the task has one) a checklist form that writes
 * `security.work.checklist.response` rows. See the build brief for the
 * `security_work` model contract this talks to via plain `call_kw` — there
 * is no bespoke backend endpoint.
 *
 * The backing Odoo module may not be installed in every environment this
 * runs in yet, so every RPC here is wrapped and surfaced as an error state
 * rather than allowed to crash the page.
 *
 * Visual notes: list tiles rise in on mount (one orchestrated stagger,
 * see --i + .dg-tile in shell_depth.css) rather than animating on every
 * hover; drilling into a task uses .dg-detail-enter for a single settling
 * transition. Both respect prefers-reduced-motion via the shared tokens.
 */
interface MyWorkProps {
  /** Bumped by the toolbar's Reload button when this page is the one on
   * screen (see Toolbar.tsx — Reload otherwise targets the Odoo webview,
   * which is invisible while the app view covers the window, so it would
   * silently do nothing here without this). Any change refetches; the
   * initial mount already fetches on its own, so that first value is
   * ignored. */
  reloadSignal?: number;
}

export function MyWork({ reloadSignal }: MyWorkProps) {
  const { session } = useSession();
  const [employeeState, setEmployeeState] = useState<LoadState>("loading");
  const [employeeId, setEmployeeId] = useState<number | null>(null);
  const [employeeError, setEmployeeError] = useState<string | null>(null);

  const [tasksState, setTasksState] = useState<LoadState>("loading");
  const [tasks, setTasks] = useState<WorkTask[]>([]);
  const [tasksError, setTasksError] = useState<string | null>(null);

  const [signoffs, setSignoffs] = useState<RosterSignoff[]>([]);
  const [signoffBusyId, setSignoffBusyId] = useState<number | null>(null);
  const [signoffFeedback, setSignoffFeedback] = useState<{ id: number; message: string } | null>(null);

  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);

  const loadSignoffs = useCallback(async () => {
    if (!session) return;
    try {
      const items = await fetchPendingRosterSignoffs();
      setSignoffs(items);
    } catch {
      setSignoffs([]);
    }
  }, [session]);

  useEffect(() => {
    void loadSignoffs();
  }, [loadSignoffs]);

  const handleSignRoster = async (signoffId: number) => {
    setSignoffBusyId(signoffId);
    try {
      await signRosterBatch(signoffId);
      setSignoffFeedback({ id: signoffId, message: "Signed off!" });
      setTimeout(() => {
        setSignoffs((prev) => prev.filter((s) => s.id !== signoffId));
        setSignoffFeedback(null);
      }, 1200);
    } catch (err) {
      alert(extractErrorMessage(err, "Failed to sign off roster batch."));
    } finally {
      setSignoffBusyId(null);
    }
  };

  const handleReviewRoster = async (signoff: RosterSignoff) => {
    const batchId = signoff.batch_id[0];
    await invoke("navigate_odoo", { path: `/odoo/action-security_operations.action_security_roster_batch/${batchId}` });
    await invoke("app_view_close");
  };

  const loadEmployee = useCallback(async () => {
    if (!session) return;
    setEmployeeState("loading");
    setEmployeeError(null);
    try {
      const id = await resolveEmployeeId(session.uid);
      setEmployeeId(id);
      setEmployeeState("ready");
    } catch (err) {
      setEmployeeError(extractErrorMessage(err, "Couldn't look up your employee record."));
      setEmployeeState("error");
    }
  }, [session]);

  useEffect(() => {
    void loadEmployee();
  }, [loadEmployee]);

  const loadTasks = useCallback(async () => {
    if (employeeId == null) return;
    setTasksState("loading");
    setTasksError(null);
    try {
      const rows = await fetchMyTasks(employeeId);
      setTasks([...rows].sort(byDueDateAscending));
      setTasksState("ready");
    } catch (err) {
      setTasksError(extractErrorMessage(err, "Couldn't load your tasks."));
      setTasksState("error");
    }
  }, [employeeId]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  const refresh = useCallback(() => {
    void loadTasks();
    void loadSignoffs();
  }, [loadTasks, loadSignoffs]);

  const isFirstReloadSignal = useRef(true);
  useEffect(() => {
    if (isFirstReloadSignal.current) { isFirstReloadSignal.current = false; return; }
    if (selectedTaskId == null) refresh();
    // else: TaskDetail below gets the same reloadSignal and refetches itself.
  }, [reloadSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  const taskCount = tasks.length;

  if (employeeState === "loading") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div className="dg-skeleton" style={{ height: 56 }} />
        <div className="dg-skeleton" style={{ height: 56 }} />
        <div className="dg-skeleton" style={{ height: 56 }} />
      </div>
    );
  }

  if (employeeState === "error") {
    return (
      <div className="dg-card dg-page-enter" style={{ maxWidth: 480 }}>
        <p style={{ fontSize: 13, color: "var(--ds-danger)", margin: "0 0 10px" }}>{employeeError}</p>
        <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void loadEmployee()}>
          Try again
        </button>
      </div>
    );
  }

  if (employeeId == null) {
    return (
      <div className="dg-page-enter" style={{ maxWidth: 640 }}>
        <RosterSignoffSection
          signoffs={signoffs}
          busyId={signoffBusyId}
          feedback={signoffFeedback}
          onSign={(id) => void handleSignRoster(id)}
          onReview={(s) => void handleReviewRoster(s)}
        />
        <div className="dg-card" style={{ maxWidth: 480, marginTop: signoffs.length > 0 ? 16 : 0 }}>
          <p style={{ fontSize: 13, color: "var(--ds-text-2)", margin: 0 }}>
            {signoffs.length > 0
              ? "Your account does not have a linked guard profile for field sweeps, but roster sign-offs assigned to your role appear above."
              : "Your account isn't linked to an employee record yet, so there's no work queue to show. Ask your operations manager to link one."}
          </p>
        </div>
      </div>
    );
  }

  if (selectedTaskId != null) {
    return (
      <TaskDetail
        taskId={selectedTaskId}
        onBack={() => setSelectedTaskId(null)}
        onChanged={refresh}
        reloadSignal={reloadSignal}
      />
    );
  }

  return (
    <>
      <RosterSignoffSection
        signoffs={signoffs}
        busyId={signoffBusyId}
        feedback={signoffFeedback}
        onSign={(id) => void handleSignRoster(id)}
        onReview={(s) => void handleReviewRoster(s)}
      />

      <div
        className="dg-page-enter"
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "4px 0 20px" }}
      >
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "var(--ds-text)" }}>My Work</h1>
        {tasksState === "ready" && (
          <span className="dg-chip">
            {taskCount} {taskCount === 1 ? "task" : "tasks"}
          </span>
        )}
      </div>

      {tasksState === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="dg-skeleton" style={{ height: 62 }} />
          <div className="dg-skeleton" style={{ height: 62 }} />
          <div className="dg-skeleton" style={{ height: 62 }} />
        </div>
      )}

      {tasksState === "error" && (
        <div className="dg-card dg-page-enter" style={{ maxWidth: 480 }}>
          <p style={{ fontSize: 13, color: "var(--ds-danger)", margin: "0 0 10px" }}>{tasksError}</p>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={refresh}>
            Try again
          </button>
        </div>
      )}

      {tasksState === "ready" && taskCount === 0 && (
        <div className="dg-card dg-page-enter" style={{ maxWidth: 480 }}>
          <p className="dg-empty" style={{ padding: "8px 0" }}>
            Nothing assigned to you right now. New tasks and sweeps will show up here.
          </p>
        </div>
      )}

      {tasksState === "ready" && taskCount > 0 && (
        <div className="dg-tasklist">
          {tasks.map((task, index) => (
            <button
              key={task.id}
              type="button"
              className="dg-tile"
              style={{ alignItems: "flex-start", "--i": index } as React.CSSProperties}
              onClick={() => setSelectedTaskId(task.id)}
            >
              <span className="dg-tile__icon">
                <ClipboardListIcon size={18} />
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span className="dg-tile__title">{task.name}</span>
                  <span className="dg-chip">{STATE_LABELS[task.state]}</span>
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
                  <DueBadge task={task} />
                  {task.site_id && (
                    <span style={{ fontSize: 11.5, color: "var(--ds-text-subtle)" }}>{task.site_id[1]}</span>
                  )}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function TaskDetail({
  taskId, onBack, onChanged, reloadSignal,
}: { taskId: number; onBack: () => void; onChanged: () => void; reloadSignal?: number }) {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [task, setTask] = useState<WorkTask | null>(null);
  const [items, setItems] = useState<ChecklistItemDef[]>([]);
  const [responses, setResponses] = useState<ChecklistResponse[]>([]);
  const [cncOptions, setCncOptions] = useState<Array<{ value: string; label: string }>>([]);

  const [actionBusy, setActionBusy] = useState<WorkAction | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showCncPicker, setShowCncPicker] = useState(false);
  const [cncReason, setCncReason] = useState("");

  const [draft, setDraft] = useState<Record<number, { value_bool?: boolean; value_text?: string; value_number?: number }>>({});
  const [savingChecklist, setSavingChecklist] = useState(false);
  const [checklistSaved, setChecklistSaved] = useState(false);

  const load = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const t = await fetchTask(taskId);
      setTask(t);
      if (t.checklist_template_id) {
        const [itemDefs, existingResponses] = await Promise.all([
          fetchChecklistItems(t.checklist_template_id[0]),
          fetchChecklistResponses(taskId),
        ]);
        setItems(itemDefs);
        setResponses(existingResponses);
      } else {
        setItems([]);
        setResponses([]);
      }
      setState("ready");
    } catch (err) {
      setError(extractErrorMessage(err, "Couldn't load this task."));
      setState("error");
    }
  }, [taskId]);

  useEffect(() => {
    void load();
  }, [load]);

  const isFirstReloadSignal = useRef(true);
  useEffect(() => {
    if (isFirstReloadSignal.current) { isFirstReloadSignal.current = false; return; }
    void load();
  }, [reloadSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (showCncPicker && cncOptions.length === 0) {
      void fetchCncReasonOptions().then(setCncOptions);
    }
  }, [showCncPicker, cncOptions.length]);

  const responseByItem = useMemo(() => {
    const map = new Map<number, ChecklistResponse>();
    for (const r of responses) map.set(r.item_def_id[0], r);
    return map;
  }, [responses]);

  const actions = task ? availableActions(task.state) : [];
  const editableChecklist = task ? task.state === "open" || task.state === "in_progress" || task.state === "rejected" : false;

  const runAction = useCallback(
    async (action: WorkAction, reason?: string) => {
      setActionBusy(action);
      setActionError(null);
      try {
        await runWorkAction(taskId, action, reason);
        setShowCncPicker(false);
        setCncReason("");
        await load();
        onChanged();
      } catch (err) {
        setActionError(extractErrorMessage(err, "That action didn't go through."));
      } finally {
        setActionBusy(null);
      }
    },
    [taskId, load, onChanged],
  );

  const saveChecklist = useCallback(async () => {
    if (!task) return;
    setSavingChecklist(true);
    setActionError(null);
    setChecklistSaved(false);
    try {
      for (const item of items) {
        const pending = draft[item.id];
        if (!pending) continue;
        const existing = responseByItem.get(item.id);
        await saveChecklistResponse(taskId, item.id, existing?.id ?? null, pending);
      }
      setDraft({});
      await load();
      setChecklistSaved(true);
    } catch (err) {
      setActionError(extractErrorMessage(err, "Couldn't save the checklist."));
    } finally {
      setSavingChecklist(false);
    }
  }, [task, items, draft, responseByItem, taskId, load]);

  if (state === "loading") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 640 }}>
        <div className="dg-skeleton" style={{ height: 28, width: 220 }} />
        <div className="dg-skeleton" style={{ height: 120 }} />
        <div className="dg-skeleton" style={{ height: 44, width: 200 }} />
      </div>
    );
  }

  if (state === "error" || !task) {
    return (
      <div className="dg-card dg-detail-enter" style={{ maxWidth: 480 }}>
        <p style={{ fontSize: 13, color: "var(--ds-danger)", margin: "0 0 10px" }}>{error}</p>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void load()}>
            Try again
          </button>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={onBack}>
            Back to My Work
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dg-detail-enter">
      <button
        type="button"
        className="dg-btn dg-btn--secondary"
        style={{ marginBottom: 16, fontSize: 12.5, padding: "6px 12px" }}
        onClick={onBack}
      >
        ← Back to My Work
      </button>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
        <h1 style={{ fontSize: 19, fontWeight: 700, margin: 0, color: "var(--ds-text)" }}>{task.name}</h1>
        <span className="dg-chip">{STATE_LABELS[task.state]}</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
        <DueBadge task={task} />
        {task.site_id && <span style={{ fontSize: 12, color: "var(--ds-text-subtle)" }}>{task.site_id[1]}</span>}
      </div>

      {task.description && (
        <p style={{ fontSize: 13, color: "var(--ds-text-2)", lineHeight: 1.5, marginBottom: 18 }}>{task.description}</p>
      )}

      {task.state === "could_not_complete" && task.cnc_reason && (
        <div className="dg-card" style={{ marginBottom: 18, display: "flex", gap: 8, alignItems: "flex-start" }}>
          <AlertTriangleIcon size={16} />
          <span style={{ fontSize: 12.5, color: "var(--ds-text-2)" }}>Marked could not complete: {task.cnc_reason}</span>
        </div>
      )}

      {task.state === "verified" && (
        <div className="dg-card dg-pop-in" style={{ marginBottom: 18, display: "flex", gap: 8, alignItems: "center" }}>
          <CheckCircleIcon size={16} />
          <span style={{ fontSize: 12.5, color: "var(--ds-text-2)" }}>Verified — no further action needed.</span>
        </div>
      )}

      {items.length > 0 && (
        <div className="dg-card" style={{ marginBottom: 18 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-text)", margin: "0 0 12px" }}>Checklist</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {items.map((item) => {
              const existing = responseByItem.get(item.id);
              const pending = draft[item.id];
              return (
                <ChecklistItemRow
                  key={item.id}
                  item={item}
                  existing={existing}
                  pending={pending}
                  disabled={!editableChecklist}
                  onChange={(value) => setDraft((d) => ({ ...d, [item.id]: { ...d[item.id], ...value } }))}
                />
              );
            })}
          </div>
          {editableChecklist && (
            <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 10 }}>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                disabled={savingChecklist || Object.keys(draft).length === 0}
                onClick={() => void saveChecklist()}
              >
                {savingChecklist ? "Saving…" : "Save checklist"}
              </button>
              {checklistSaved && Object.keys(draft).length === 0 && (
                <span className="dg-pop-in" style={{ fontSize: 12, color: "var(--ds-success)" }}>Saved</span>
              )}
            </div>
          )}
        </div>
      )}

      {actionError && <p style={{ fontSize: 12.5, color: "var(--ds-danger)", margin: "0 0 12px" }}>{actionError}</p>}

      {showCncPicker && (
        <div className="dg-card dg-detail-enter" style={{ marginBottom: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-text)", margin: "0 0 10px" }}>
            Why couldn't this be completed?
          </p>
          {cncOptions.length > 0 ? (
            <select
              value={cncReason}
              onChange={(e) => setCncReason(e.target.value)}
              className="dg-input"
              style={{
                width: "100%",
                padding: "8px 10px",
                borderRadius: "var(--dgs-r-control)",
                border: "1px solid var(--ds-border)",
                fontSize: 13,
                marginBottom: 10,
                fontFamily: "var(--dgs-font)",
              }}
            >
              <option value="">Select a reason…</option>
              {cncOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ) : (
            <textarea
              value={cncReason}
              onChange={(e) => setCncReason(e.target.value)}
              placeholder="Describe why this couldn't be completed"
              rows={3}
              className="dg-input"
              style={{
                width: "100%",
                padding: "8px 10px",
                borderRadius: "var(--dgs-r-control)",
                border: "1px solid var(--ds-border)",
                fontSize: 13,
                marginBottom: 10,
                fontFamily: "var(--dgs-font)",
                resize: "vertical",
              }}
            />
          )}
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              className="dg-btn dg-btn--primary"
              disabled={!cncReason || actionBusy === "could_not_complete"}
              onClick={() => void runAction("could_not_complete", cncReason)}
            >
              {actionBusy === "could_not_complete" ? "Submitting…" : "Confirm"}
            </button>
            <button type="button" className="dg-btn dg-btn--secondary" onClick={() => setShowCncPicker(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {actions.length > 0 && !showCncPicker && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {actions.includes("start") && (
            <button
              type="button"
              className="dg-btn dg-btn--primary"
              disabled={actionBusy !== null}
              onClick={() => void runAction("start")}
            >
              {actionBusy === "start" ? "Starting…" : "Start"}
            </button>
          )}
          {actions.includes("submit") && (
            <button
              type="button"
              className="dg-btn dg-btn--primary"
              disabled={actionBusy !== null}
              onClick={() => void runAction("submit")}
            >
              {actionBusy === "submit" ? "Submitting…" : "Submit"}
            </button>
          )}
          {actions.includes("could_not_complete") && (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              disabled={actionBusy !== null}
              onClick={() => setShowCncPicker(true)}
            >
              Could not complete
            </button>
          )}
          {actions.includes("cancel") && (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              disabled={actionBusy !== null}
              onClick={() => void runAction("cancel")}
            >
              {actionBusy === "cancel" ? "Cancelling…" : "Cancel"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ChecklistItemRow({
  item,
  existing,
  pending,
  disabled,
  onChange,
}: {
  item: ChecklistItemDef;
  existing: ChecklistResponse | undefined;
  pending: { value_bool?: boolean; value_text?: string; value_number?: number } | undefined;
  disabled: boolean;
  onChange: (value: { value_bool?: boolean; value_text?: string; value_number?: number }) => void;
}) {
  const label = (
    <span style={{ fontSize: 13, color: "var(--ds-text-2)" }}>
      {item.label}
      {item.required && <span style={{ color: "var(--ds-danger)" }}> *</span>}
    </span>
  );

  if (item.item_type === "boolean") {
    const checked = pending?.value_bool ?? existing?.value_bool ?? false;
    return (
      <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          type="checkbox"
          className="dg-check-input"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange({ value_bool: e.target.checked })}
        />
        {label}
      </label>
    );
  }

  if (item.item_type === "number") {
    const value = pending?.value_number ?? existing?.value_number ?? "";
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {label}
        <input
          type="number"
          className="dg-input"
          value={value === false ? "" : value}
          disabled={disabled}
          onChange={(e) => onChange({ value_number: e.target.value === "" ? undefined : Number(e.target.value) })}
          style={{
            padding: "6px 10px",
            borderRadius: "var(--dgs-r-control)",
            border: "1px solid var(--ds-border)",
            fontSize: 13,
            fontFamily: "var(--dgs-font)",
            maxWidth: 160,
          }}
        />
      </div>
    );
  }

  if (item.item_type === "photo") {
    // Photo capture isn't wired yet (no camera/file-upload bridge exists in
    // this MVP slice) — shown as a read-only note rather than a fake control.
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {label}
        <span style={{ fontSize: 11.5, color: "var(--ds-text-subtle)" }}>
          Photo capture isn't available in this build yet.
        </span>
      </div>
    );
  }

  // text
  const value = pending?.value_text ?? existing?.value_text ?? "";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {label}
      <input
        type="text"
        className="dg-input"
        value={value === false ? "" : value}
        disabled={disabled}
        onChange={(e) => onChange({ value_text: e.target.value })}
        style={{
          padding: "6px 10px",
          borderRadius: "var(--dgs-r-control)",
          border: "1px solid var(--ds-border)",
          fontSize: 13,
          fontFamily: "var(--dgs-font)",
        }}
      />
    </div>
  );
}

function RosterSignoffSection({
  signoffs,
  busyId,
  feedback,
  onSign,
  onReview,
}: {
  signoffs: RosterSignoff[];
  busyId: number | null;
  feedback: { id: number; message: string } | null;
  onSign: (id: number) => void;
  onReview: (signoff: RosterSignoff) => void;
}) {
  if (signoffs.length === 0) return null;
  return (
    <div style={{ marginBottom: 24 }} className="dg-page-enter">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <h2
          style={{
            fontSize: 13,
            fontWeight: 700,
            margin: 0,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "var(--ds-warning)",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <AlertTriangleIcon size={16} /> Roster Approvals Waiting On You
        </h2>
        <span className="dg-chip" style={{ background: "var(--ds-warning-bg)", color: "var(--ds-warning)" }}>
          {signoffs.length} {signoffs.length === 1 ? "batch" : "batches"}
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {signoffs.map((s) => (
          <div
            key={s.id}
            className="dg-card"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              padding: "12px 16px",
              borderColor: "var(--ds-warning-border, var(--ds-border))",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 13.5, color: "var(--ds-text)" }}>
                {s.batch_id[1]}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--ds-text-muted)", marginTop: 3 }}>
                Your Role: <strong style={{ color: "var(--ds-text)" }}>{formatRosterRole(s.role)}</strong>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              {feedback?.id === s.id ? (
                <span
                  style={{
                    fontSize: 12,
                    color: "var(--ds-success)",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <CheckCircleIcon size={14} /> {feedback.message}
                </span>
              ) : (
                <>
                  <button
                    type="button"
                    className="dg-btn dg-btn--secondary"
                    style={{ fontSize: 12, padding: "4px 10px" }}
                    onClick={() => onReview(s)}
                  >
                    Review in ERP
                  </button>
                  <button
                    type="button"
                    className="dg-btn dg-btn--primary"
                    style={{ fontSize: 12, padding: "4px 12px" }}
                    disabled={busyId === s.id}
                    onClick={() => onSign(s.id)}
                  >
                    {busyId === s.id ? "Signing…" : "Sign Off"}
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}