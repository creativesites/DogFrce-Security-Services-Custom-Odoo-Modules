import { useCallback, useEffect, useRef, useState } from "react";
import { useViewMode } from "../../app/viewMode";
import { useStartGuidance } from "../../app/useStartGuidance";
import { SafeHtml } from "../../components/SafeHtml";
import {
  CourseTree, TrainingAssessment, TrainingAssignment, TrainingAttempt, TrainingLesson, TrainingLessonProgress,
  askLessonAi, fetchAssignment, fetchAttempts, fetchCourseTree, fetchLessonProgress, fetchMyAssignments,
  markLessonComplete, resolveEmployeeId, startAttempt, submitAttempt,
} from "../../api/training";
import { extractErrorMessage } from "../../lib/extractErrorMessage";
import { useSession } from "../../session/SessionContext";
import {
  ASSIGNMENT_STATE_LABELS, adjacentLessons, attemptsRemaining, findLessonSection, nextAssessmentToTake, isLessonDone, latestAttemptFor,
  lessonProgressSummary,
} from "./myTraining.logic";
import { CheckCircleIcon, ClipboardListIcon, SparklesIcon } from "../icons";

type LoadState = "loading" | "ready" | "error";

/**
 * My Training: assignment list -> course content (lessons + assessments).
 *
 * "Learn by doing" is implemented as a real deep link into the live Odoo
 * webview (the `navigate_odoo` + `app_view_close` commands already used
 * elsewhere in this app — see Toolbar.tsx), never a coach-mark drawn over
 * Odoo's own DOM: the "odoo" webview deliberately has zero IPC and no
 * injected script (security_deployguard_bridge-era boundary, see
 * capabilities/main.json), and this page respects that rather than
 * quietly punching a hole in it. A lesson with a `deep_link_path` gets a
 * "Try it in DogForce ERP" button that sends the learner to the real
 * screen to do the real thing; they return to this page (via the app
 * view toggle) to mark the lesson done.
 */
interface MyTrainingProps {
  reloadSignal?: number;
  /** Open this assignment straight away (Today's "Learn this first"). */
  focusAssignmentId?: number | null;
  /** The server has guided tasks (security_guidance), so lessons can offer "Practice it now". */
  canGuide?: boolean;
}

export function MyTraining({ reloadSignal, focusAssignmentId = null, canGuide = false }: MyTrainingProps) {
  const { openInOdoo } = useViewMode();
  const { session } = useSession();
  const [employeeState, setEmployeeState] = useState<LoadState>("loading");
  const [employeeId, setEmployeeId] = useState<number | null>(null);
  const [employeeError, setEmployeeError] = useState<string | null>(null);

  const [listState, setListState] = useState<LoadState>("loading");
  const [assignments, setAssignments] = useState<TrainingAssignment[]>([]);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(focusAssignmentId);

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

  useEffect(() => { void loadEmployee(); }, [loadEmployee]);

  const loadList = useCallback(async () => {
    if (employeeId == null) return;
    setListState("loading");
    setListError(null);
    try {
      const rows = await fetchMyAssignments(employeeId);
      setAssignments(rows);
      setListState("ready");
    } catch (err) {
      setListError(extractErrorMessage(err, "Couldn't load your training."));
      setListState("error");
    }
  }, [employeeId]);

  useEffect(() => { void loadList(); }, [loadList]);

  const isFirstReloadSignal = useRef(true);
  useEffect(() => {
    if (isFirstReloadSignal.current) { isFirstReloadSignal.current = false; return; }
    if (selectedId == null) void loadList();
  }, [reloadSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  if (employeeState === "loading") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div className="dg-skeleton" style={{ height: 56 }} />
        <div className="dg-skeleton" style={{ height: 56 }} />
      </div>
    );
  }

  if (employeeState === "error") {
    return (
      <div className="dg-card dg-page-enter" style={{ maxWidth: 480 }}>
        <p style={{ fontSize: 13, color: "var(--ds-danger)", margin: "0 0 10px" }}>{employeeError}</p>
        <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void loadEmployee()}>Try again</button>
      </div>
    );
  }

  if (employeeId == null) {
    return (
      <div className="dg-card dg-page-enter" style={{ maxWidth: 480 }}>
        <p style={{ fontSize: 13, color: "var(--ds-text-2)", margin: "0 0 14px" }}>
          Your account isn't linked to an employee record yet, so there's no training to show. Ask your
          operations manager to link one.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void loadEmployee()}>
            Check again
          </button>
          <button
            type="button"
            className="dg-btn dg-btn--secondary"
            onClick={() => {
              void openInOdoo("/odoo/action-hr.open_view_employee_list_my");
            }}
          >
            Open Employees in DogForce ERP →
          </button>
        </div>
      </div>
    );
  }

  if (selectedId != null) {
    return (
      <AssignmentDetail
        assignmentId={selectedId}
        canGuide={canGuide}
        onBack={() => setSelectedId(null)}
        onChanged={() => void loadList()}
      />
    );
  }

  return (
    <>
      <header className="dg-hero dg-page-enter">
        <div className="dg-hero__text">
          <p className="dg-eyebrow">Short lessons for the work you do</p>
          <h1 className="dg-display">My training</h1>
          <p className="dg-subline">
            {listState === "ready"
              ? `${assignments.length} ${assignments.length === 1 ? "course" : "courses"} assigned. A few minutes each, then practise on the real screens.`
              : "Loading your courses…"}
          </p>
        </div>
      </header>

      {listState === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="dg-skeleton" style={{ height: 62 }} />
          <div className="dg-skeleton" style={{ height: 62 }} />
        </div>
      )}

      {listState === "error" && (
        <div className="dg-card dg-page-enter" style={{ maxWidth: 480 }}>
          <p style={{ fontSize: 13, color: "var(--ds-danger)", margin: "0 0 10px" }}>{listError}</p>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void loadList()}>Try again</button>
        </div>
      )}

      {listState === "ready" && assignments.length === 0 && (
        <div className="dg-card dg-page-enter" style={{ maxWidth: 480 }}>
          <p className="dg-empty" style={{ padding: "8px 0 14px" }}>
            Nothing assigned to you right now. New courses will show up here.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void loadList()}>
              Refresh
            </button>
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              onClick={() => {
                void openInOdoo("/odoo/action-security_training.action_security_training_assignment_my");
              }}
            >
              Open Training in DogForce ERP →
            </button>
          </div>
        </div>
      )}

      {listState === "ready" && assignments.length > 0 && (
        <div className="dg-tasklist">
          {assignments.map((a, index) => (
            <button
              key={a.id}
              type="button"
              className="dg-tile"
              style={{ alignItems: "flex-start", "--i": index } as React.CSSProperties}
              onClick={() => setSelectedId(a.id)}
            >
              <span className="dg-tile__icon"><ClipboardListIcon size={18} /></span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span className="dg-tile__title">{a.course_id[1]}</span>
                  <span className="dg-chip">{ASSIGNMENT_STATE_LABELS[a.state]}</span>
                </span>
                {a.due_date && (
                  <span style={{ display: "block", fontSize: 11.5, color: "var(--ds-text-subtle)", marginTop: 6 }}>
                    Due {a.due_date}
                  </span>
                )}
              </span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function AssignmentDetail({
  assignmentId, onBack, onChanged, canGuide,
}: { assignmentId: number; onBack: () => void; onChanged: () => void; canGuide: boolean }) {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [assignment, setAssignment] = useState<TrainingAssignment | null>(null);
  const [tree, setTree] = useState<CourseTree | null>(null);
  const [progress, setProgress] = useState<TrainingLessonProgress[]>([]);
  const [attempts, setAttempts] = useState<TrainingAttempt[]>([]);

  const [activeLesson, setActiveLesson] = useState<TrainingLesson | null>(null);
  const [openAssessment, setOpenAssessment] = useState<TrainingAssessment | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const a = await fetchAssignment(assignmentId);
      const [courseTree, lessonProgress, attemptRows] = await Promise.all([
        fetchCourseTree(a.course_version_id[0], { withGuidance: canGuide }),
        fetchLessonProgress(assignmentId),
        fetchAttempts(assignmentId),
      ]);
      setAssignment(a);
      setTree(courseTree);
      setProgress(lessonProgress);
      setAttempts(attemptRows);
      setState("ready");
    } catch (err) {
      setError(extractErrorMessage(err, "Couldn't load this course."));
      setState("error");
    }
  }, [assignmentId, canGuide]);

  useEffect(() => { void load(); }, [load]);

  const refreshAfterAction = useCallback(async () => {
    await load();
    onChanged();
  }, [load, onChanged]);

  if (state === "loading") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 640 }}>
        <div className="dg-skeleton" style={{ height: 28, width: 220 }} />
        <div className="dg-skeleton" style={{ height: 120 }} />
      </div>
    );
  }

  if (state === "error" || !assignment || !tree) {
    return (
      <div className="dg-card dg-detail-enter" style={{ maxWidth: 480 }}>
        <p style={{ fontSize: 13, color: "var(--ds-danger)", margin: "0 0 10px" }}>{error}</p>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void load()}>Try again</button>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={onBack}>Back to My Training</button>
        </div>
      </div>
    );
  }

  if (activeLesson) {
    return (
      <LessonView
        lesson={activeLesson}
        tree={tree}
        progress={progress}
        onBack={() => setActiveLesson(null)}
        onSelectLesson={(lesson) => setActiveLesson(lesson)}
        onMarkedDone={async () => {
          await markLessonComplete(assignmentId, activeLesson.id);
          await refreshAfterAction();
        }}
        nextAssessment={nextAssessmentToTake(tree, attempts)}
        onStartAssessment={(assessment) => {
          setActiveLesson(null);
          setOpenAssessment(assessment);
        }}
      />
    );
  }

  const { done, total } = lessonProgressSummary(tree, progress);
  // Completion is the server's decision (security.training.assignment.state).
  const everythingDone = assignment.state === "completed";

  return (
    <div className="dg-detail-enter">
      <button type="button" className="dg-btn dg-btn--secondary" style={{ marginBottom: 16, fontSize: 12.5, padding: "6px 12px" }} onClick={onBack}>
        ← Back to My Training
      </button>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
        <h1 style={{ fontSize: 19, fontWeight: 700, margin: 0, color: "var(--ds-text)" }}>{assignment.course_id[1]}</h1>
        <span className="dg-chip">{ASSIGNMENT_STATE_LABELS[assignment.state]}</span>
      </div>
      <p style={{ fontSize: 12.5, color: "var(--ds-text-subtle)", margin: "0 0 18px" }}>
        {done} of {total} lessons done{tree.assessments.length > 0 ? ` · ${tree.assessments.length} assessment${tree.assessments.length > 1 ? "s" : ""}` : ""}
      </p>

      {everythingDone && (
        <div className="dg-card dg-pop-in" style={{ marginBottom: 18, display: "flex", gap: 8, alignItems: "center" }}>
          <CheckCircleIcon size={16} />
          <span style={{ fontSize: 12.5, color: "var(--ds-text-2)" }}>Course completed — nice work.</span>
        </div>
      )}

      {tree.sections.map((section) => (
        <div key={section.id} className="dg-card" style={{ marginBottom: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-text)", margin: "0 0 10px" }}>{section.name}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {section.lessons.map((lesson) => {
              const done_ = isLessonDone(lesson.id, progress);
              return (
                <button
                  key={lesson.id}
                  type="button"
                  className="dg-tile"
                  style={{ padding: "10px 12px" }}
                  onClick={() => setActiveLesson(lesson)}
                >
                  <span className="dg-tile__icon">
                    {done_ ? <CheckCircleIcon size={16} /> : <ClipboardListIcon size={16} />}
                  </span>
                  <span style={{ flex: 1, textAlign: "left", fontSize: 13, color: "var(--ds-text)" }}>{lesson.name}</span>
                  {done_ && <span className="dg-chip">Done</span>}
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {tree.assessments.map((assessment) => {
        const latest = latestAttemptFor(assessment.id, attempts);
        const remaining = attemptsRemaining(assessment, attempts);
        return (
          <div key={assessment.id} className="dg-card" style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-text)", margin: "0 0 4px" }}>{assessment.name}</p>
                <p style={{ fontSize: 11.5, color: "var(--ds-text-subtle)", margin: 0 }}>
                  Pass mark {assessment.pass_mark_pct}% · {remaining} attempt{remaining === 1 ? "" : "s"} left
                  {latest && ` · last score ${latest.score_pct.toFixed(0)}% (${latest.state})`}
                </p>
              </div>
              <button
                type="button"
                className="dg-btn dg-btn--primary"
                disabled={remaining <= 0 || latest?.state === "passed"}
                onClick={() => setOpenAssessment(assessment)}
              >
                {latest?.state === "passed" ? "Passed" : remaining <= 0 ? "No attempts left" : latest ? "Retry" : "Start"}
              </button>
            </div>
          </div>
        );
      })}

      {openAssessment && (
        <AssessmentModal
          assignmentId={assignmentId}
          assessment={openAssessment}
          onClose={() => setOpenAssessment(null)}
          onSubmitted={async () => {
            setOpenAssessment(null);
            await refreshAfterAction();
          }}
        />
      )}
    </div>
  );
}

function ModalShell({ title, onClose, children, footer }: { title: string; onClose: () => void; children: React.ReactNode; footer?: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="dg-lesson-modal" role="dialog" aria-modal="true" aria-label={title}>
      <div className="dg-lesson-modal__backdrop" onClick={onClose} />
      <div className="dg-lesson-modal__panel dg-pop-in">
        <div className="dg-lesson-modal__head">
          <h2 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: "var(--ds-text)" }}>{title}</h2>
          <button type="button" className="dg-lesson-modal__close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="dg-lesson-modal__body">{children}</div>
        {footer && <div className="dg-lesson-modal__foot">{footer}</div>}
      </div>
    </div>
  );
}

interface LessonViewProps {
  lesson: TrainingLesson;
  tree: CourseTree;
  progress: TrainingLessonProgress[];
  onBack: () => void;
  onSelectLesson: (lesson: TrainingLesson) => void;
  onMarkedDone: () => Promise<void>;
  onStartAssessment: (assessment: TrainingAssessment) => void;
  /** Which assessment "Take the assessment" opens; null when none is takeable. */
  nextAssessment: TrainingAssessment | null;
}

/** Where a lesson video can play inside the app. Must match the CSP's
 * `frame-src` / `media-src` in tauri.conf.json. Anything else (including the
 * course's `REPLACE_WITH_…` placeholders) falls back to the written walkthrough. */
function embeddableVideo(url: string): "iframe" | "file" | null {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (parsed.protocol !== "https:") return null;
  if (["www.youtube-nocookie.com", "www.youtube.com", "player.vimeo.com"].includes(parsed.hostname)) return "iframe";
  if (/\.(mp4|webm)$/i.test(parsed.pathname)) return "file";
  return null;
}

function LessonView({
  lesson,
  tree,
  progress,
  onBack,
  onSelectLesson,
  onMarkedDone,
  onStartAssessment,
  nextAssessment,
}: LessonViewProps) {
  const done = isLessonDone(lesson.id, progress);
  const { prev, next, index, total } = adjacentLessons(tree, lesson.id);
  const section = findLessonSection(tree, lesson.id);

  const [marking, setMarking] = useState(false);
  const [markError, setMarkError] = useState<string | null>(null);

  const [aiQuestion, setAiQuestion] = useState("");
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // The `dg_tour=` parameters this used to append had no handler anywhere in
  // Odoo. Guided practice is now `security_guidance` (see onPractice).
  const { openInOdoo } = useViewMode();
  const guidance = useStartGuidance();
  const tryItInErp = useCallback(() => {
    if (lesson.deep_link_path) void openInOdoo(lesson.deep_link_path);
  }, [lesson.deep_link_path, openInOdoo]);

  const askAi = useCallback(async (questionText?: string) => {
    const q = (questionText ?? aiQuestion).trim();
    if (!q) return;
    setAiBusy(true);
    setAiError(null);
    setAiAnswer(null);
    try {
      const answer = await askLessonAi(lesson.id, q);
      setAiAnswer(answer);
    } catch (err) {
      setAiError(extractErrorMessage(err, "AI assist isn't available right now."));
    } finally {
      setAiBusy(false);
    }
  }, [lesson.id, aiQuestion]);

  const handleMarkDone = async () => {
    setMarking(true);
    setMarkError(null);
    try {
      await onMarkedDone();
    } catch (err) {
      setMarkError(extractErrorMessage(err, "Couldn't mark this lesson as completed."));
    } finally {
      setMarking(false);
    }
  };

  const suggestedPrompts = [
    "Summarize key workflow steps",
    "What are common pitfalls or mistakes to avoid?",
    "How does this connect to rosters, payroll, & billing?",
  ];

  return (
    <div className="dg-lesson-view">
      {/* Top Navigation */}
      <div className="dg-lesson-view__nav">
        <button
          type="button"
          className="dg-btn dg-btn--secondary"
          style={{ fontSize: 12.5, padding: "6px 14px" }}
          onClick={onBack}
        >
          ← Back to Course Outline
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="dg-chip">Lesson {index + 1} of {total}</span>
          {done ? (
            <span className="dg-chip" style={{ color: "var(--ds-success)", borderColor: "var(--ds-success)" }}>
              <CheckCircleIcon size={13} /> Completed
            </span>
          ) : (
            <span className="dg-chip">In progress</span>
          )}
        </div>
      </div>

      {/* Header */}
      <div className="dg-lesson-view__header">
        {section && (
          <div className="dg-lesson-view__section-label">
            {section.name}
          </div>
        )}
        <h1 className="dg-lesson-view__title">{lesson.name}</h1>
        <div className="dg-lesson-view__meta">
          <span className="dg-chip">
            {lesson.guidance_flow_code
              ? "Guided practice"
              : lesson.content_type === "video_url"
              ? "Video walkthrough"
              : "Step by step"}
          </span>
        </div>
      </div>

      {/* Guided practice: only claimed when a real guided flow exists. */}
      {lesson.guidance_flow_code ? (
        <div className="dg-lesson-view__hero">
          <div className="dg-lesson-view__hero-info">
            <div className="dg-lesson-view__hero-title">Practise it in the real ERP</div>
            <div className="dg-lesson-view__hero-desc">
              DeployGuard opens the ERP with a guide beside it and highlights each control as you reach it. You do every
              step yourself. If you have a real task for this today, the guide uses it, so practising is doing.
            </div>
            {!!guidance.error && <p className="dg-alert dg-alert--danger">{extractErrorMessage(guidance.error, "The guide couldn't start.")}</p>}
          </div>
          <button type="button" className="dg-btn dg-btn--primary" disabled={guidance.starting}
            onClick={() => lesson.guidance_flow_code && void guidance.start(lesson.guidance_flow_code, { path: lesson.deep_link_path })}>
            {guidance.starting ? "Starting…" : "Practice it now"}
          </button>
        </div>
      ) : lesson.deep_link_path ? (
        <div className="dg-lesson-view__hero">
          <div className="dg-lesson-view__hero-info">
            <div className="dg-lesson-view__hero-title">Try it in the ERP</div>
            <div className="dg-lesson-view__hero-desc">Opens the screen this lesson is about. Come back here to mark the lesson done.</div>
          </div>
          <button type="button" className="dg-btn dg-btn--primary" onClick={tryItInErp}>Open the screen →</button>
        </div>
      ) : null}

      {/* Video Section (if applicable) */}
      {lesson.content_type === "video_url" && (
        lesson.video_url && embeddableVideo(lesson.video_url) ? (
          <div className="dg-lesson-video">
            {embeddableVideo(lesson.video_url) === "file" ? (
              <video src={lesson.video_url} controls preload="metadata" />
            ) : (
              <iframe src={lesson.video_url} title={lesson.name} allowFullScreen referrerPolicy="strict-origin" />
            )}
          </div>
        ) : (
          <div className="dg-lesson-video-notice">
            <span style={{ fontSize: 18 }} aria-hidden="true">🎬</span>
            <span>
              <strong>Video walkthrough in production:</strong> Follow the full step-by-step illustrated guide below, then try it in the ERP.
            </span>
          </div>
        )
      )}

      {/* Main Content Card */}
      {lesson.body && (
        <div className="dg-lesson-view__card">
          <SafeHtml className="dg-lesson-body" html={lesson.body} />
        </div>
      )}

      {/* DeployGuard AI Tutor Card */}
      <div className="dg-lesson-ai-card">
        <div className="dg-lesson-ai-card__head">
          <div className="dg-lesson-ai-card__title">
            <SparklesIcon size={16} />
            DeployGuard AI Assistant
          </div>
          <span style={{ fontSize: 11.5, color: "var(--ds-text-subtle)" }}>
            Trained on DogForce operating procedures
          </span>
        </div>

        <div className="dg-lesson-ai-card__suggestions">
          {suggestedPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="dg-lesson-ai-chip"
              onClick={() => {
                setAiQuestion(prompt);
                void askAi(prompt);
              }}
            >
              {prompt}
            </button>
          ))}
        </div>

        <textarea
          className="dg-input"
          rows={2}
          placeholder="Ask a question about this lesson or operational edge cases..."
          value={aiQuestion}
          onChange={(e) => setAiQuestion(e.target.value)}
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: "var(--dgs-r-control)",
            border: "1px solid var(--ds-border)",
            fontSize: 13,
            fontFamily: "var(--dgs-font)",
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />

        <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
          <button
            type="button"
            className="dg-btn dg-btn--primary"
            disabled={aiBusy || !aiQuestion.trim()}
            onClick={() => void askAi()}
          >
            {aiBusy ? "Thinking…" : "Ask AI Assistant"}
          </button>
          {aiAnswer && (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              onClick={() => {
                setAiAnswer(null);
                setAiQuestion("");
              }}
            >
              Clear
            </button>
          )}
        </div>

        {aiError && (
          <p style={{ fontSize: 12.5, color: "var(--ds-danger)", margin: "12px 0 0" }}>{aiError}</p>
        )}

        {aiAnswer && (
          <div className="dg-lesson-ai-card__answer dg-pop-in">
            {aiAnswer}
          </div>
        )}
      </div>

      {markError && (
        <p style={{ fontSize: 13, color: "var(--ds-danger)", margin: "0 0 14px" }}>{markError}</p>
      )}

      {/* Bottom Navigation & Actions */}
      <div className="dg-lesson-view__footer">
        <div>
          {prev ? (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              onClick={() => onSelectLesson(prev)}
            >
              ← Previous: {prev.name}
            </button>
          ) : (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              onClick={onBack}
            >
              ← Course Outline
            </button>
          )}
        </div>

        <div>
          {!done ? (
            <button
              type="button"
              className="dg-btn dg-btn--primary"
              disabled={marking}
              onClick={() => void handleMarkDone()}
            >
              {marking ? "Saving…" : "Mark Lesson Completed ✓"}
            </button>
          ) : (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              disabled
              style={{ color: "var(--ds-success)" }}
            >
              <CheckCircleIcon size={14} /> Completed
            </button>
          )}
        </div>

        <div>
          {next ? (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              onClick={() => onSelectLesson(next)}
            >
              Next: {next.name} →
            </button>
          ) : nextAssessment ? (
            <button
              type="button"
              className="dg-btn dg-btn--primary"
              onClick={() => onStartAssessment(nextAssessment)}
            >
              Proceed to Assessment →
            </button>
          ) : (
            <button
              type="button"
              className="dg-btn dg-btn--secondary"
              onClick={onBack}
            >
              Finish Course Outline →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function AssessmentModal({
  assignmentId, assessment, onClose, onSubmitted,
}: { assignmentId: number; assessment: TrainingAssessment; onClose: () => void; onSubmitted: () => Promise<void> }) {
  // The attempt is created on "Start", not when the modal opens: opening and
  // closing it used to consume one of the employee's limited attempts.
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const [questionIndex, setQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, Set<number>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<{ state: string; score_pct: number } | null>(null);

  const begin = useCallback(async () => {
    setStarting(true);
    setStartError(null);
    try {
      setAttemptId(await startAttempt(assignmentId, assessment.id));
    } catch (err) {
      setStartError(extractErrorMessage(err, "Couldn't start this assessment."));
    } finally {
      setStarting(false);
    }
  }, [assignmentId, assessment.id]);

  const question = assessment.questions[questionIndex];
  const total = assessment.questions.length;

  const toggleOption = useCallback((questionId: number, optionId: number, single: boolean) => {
    setAnswers((prev) => {
      const next = new Set(prev[questionId] ?? []);
      if (single) {
        next.clear();
        next.add(optionId);
      } else if (next.has(optionId)) {
        next.delete(optionId);
      } else {
        next.add(optionId);
      }
      return { ...prev, [questionId]: next };
    });
  }, []);

  const submit = useCallback(async () => {
    if (attemptId == null) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload: Record<number, number[]> = {};
      for (const q of assessment.questions) payload[q.id] = [...(answers[q.id] ?? [])];
      const attempt = await submitAttempt(attemptId, payload);
      setResult({ state: attempt.state, score_pct: attempt.score_pct });
    } catch (err) {
      setSubmitError(extractErrorMessage(err, "Couldn't submit your answers."));
    } finally {
      setSubmitting(false);
    }
  }, [attemptId, answers, assessment.questions]);

  return (
    <ModalShell title={assessment.name} onClose={onClose}>
      {attemptId == null && !result && (
        <div>
          <p>
            {assessment.questions.length} question{assessment.questions.length === 1 ? "" : "s"}. You need{" "}
            {assessment.pass_mark_pct}% to pass. Starting uses one of your attempts.
          </p>
          {startError && <p className="dg-alert dg-alert--danger">{startError}</p>}
          <button type="button" className="dg-btn dg-btn--primary" disabled={starting} onClick={() => void begin()}>
            {starting ? "Starting…" : "Start"}
          </button>
        </div>
      )}

      {result && (
        <div className="dg-pop-in" style={{ textAlign: "center", padding: "12px 0" }}>
          <p style={{ fontSize: 28, fontWeight: 700, color: result.state === "passed" ? "var(--ds-success)" : "var(--ds-danger)", margin: "0 0 6px" }}>
            {result.score_pct.toFixed(0)}%
          </p>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--ds-text)", margin: "0 0 14px" }}>
            {result.state === "passed" ? "Passed 🎉" : "Not this time — you can try again"}
          </p>
          <button type="button" className="dg-btn dg-btn--primary" onClick={() => void onSubmitted()}>Done</button>
        </div>
      )}

      {attemptId != null && !result && question && (
        <>
          <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
            {assessment.questions.map((_, i) => (
              <span
                key={i}
                aria-hidden="true"
                style={{
                  width: 8, height: 8, borderRadius: 999,
                  background: i <= questionIndex ? "var(--ds-accent)" : "var(--ds-border)",
                }}
              />
            ))}
          </div>
          <p style={{ fontSize: 11.5, color: "var(--ds-text-subtle)", margin: "0 0 6px" }}>
            Question {questionIndex + 1} of {total}
          </p>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--ds-text)", margin: "0 0 14px" }}>{question.text}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {question.options.map((opt) => {
              const selected = answers[question.id]?.has(opt.id) ?? false;
              return (
                <label key={opt.id} className={`dg-tile${selected ? " is-active" : ""}`} style={{ cursor: "pointer" }}>
                  <input
                    type={question.question_type === "single" ? "radio" : "checkbox"}
                    name={`q-${question.id}`}
                    className="dg-check-input"
                    checked={selected}
                    onChange={() => toggleOption(question.id, opt.id, question.question_type === "single")}
                  />
                  <span style={{ fontSize: 13, color: "var(--ds-text-2)" }}>{opt.text}</span>
                </label>
              );
            })}
          </div>

          {submitError && <p style={{ fontSize: 12.5, color: "var(--ds-danger)", margin: "12px 0 0" }}>{submitError}</p>}

          <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
            {questionIndex > 0 && (
              <button type="button" className="dg-btn dg-btn--secondary" onClick={() => setQuestionIndex((i) => i - 1)}>
                Back
              </button>
            )}
            {questionIndex < total - 1 ? (
              <button
                type="button"
                className="dg-btn dg-btn--primary"
                disabled={!answers[question.id]?.size}
                onClick={() => setQuestionIndex((i) => i + 1)}
              >
                Next
              </button>
            ) : (
              <button
                type="button"
                className="dg-btn dg-btn--primary"
                disabled={!answers[question.id]?.size || submitting}
                onClick={() => void submit()}
              >
                {submitting ? "Submitting…" : "Submit"}
              </button>
            )}
          </div>
        </>
      )}
    </ModalShell>
  );
}
