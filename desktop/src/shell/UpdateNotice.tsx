import { useCallback, useEffect, useState } from "react";
import { check, type Update } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { extractErrorMessage } from "../lib/extractErrorMessage";

const FIRST_CHECK_DELAY_MS = 5_000;
const RECHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;

type State =
  | { kind: "idle" }
  | { kind: "available"; update: Update }
  | { kind: "installing"; update: Update; percent: number | null }
  | { kind: "failed"; update: Update; message: string };

/**
 * Checks for a signed update quietly and offers it; never installs on its
 * own. Restarting uninvited could throw away a half-filled checklist, so
 * the person chooses when. A failed *check* stays silent (offline, or no
 * release published yet) -- only a failed install they asked for is shown.
 */
export function UpdateNotice() {
  const [state, setState] = useState<State>({ kind: "idle" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const update = await check();
        if (!cancelled && update) {
          setState((s) => (s.kind === "idle" ? { kind: "available", update } : s));
        }
      } catch (err) {
        console.warn("Update check failed:", err);
      }
    }
    const first = setTimeout(run, FIRST_CHECK_DELAY_MS);
    const repeat = setInterval(run, RECHECK_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearTimeout(first);
      clearInterval(repeat);
    };
  }, []);

  const install = useCallback(async () => {
    if (state.kind !== "available" && state.kind !== "failed") return;
    const { update } = state;
    let total = 0;
    let received = 0;
    setState({ kind: "installing", update, percent: null });
    try {
      await update.downloadAndInstall((event) => {
        if (event.event === "Started") total = event.data.contentLength ?? 0;
        if (event.event === "Progress") {
          received += event.data.chunkLength;
          if (total > 0) {
            setState({ kind: "installing", update, percent: Math.min(100, Math.round((received / total) * 100)) });
          }
        }
      });
      await relaunch();
    } catch (err) {
      setState({ kind: "failed", update, message: extractErrorMessage(err, "The update couldn't be installed.") });
    }
  }, [state]);

  if (state.kind === "idle") return null;

  if (state.kind === "installing") {
    return (
      <span className="dg-update dg-update--busy" role="status">
        Updating{state.percent !== null ? ` ${state.percent}%` : "…"}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={`dg-update${state.kind === "failed" ? " dg-update--failed" : ""}`}
      onClick={() => void install()}
      title={
        state.kind === "failed"
          ? `${state.message} Click to try again.`
          : `Version ${state.update.version} is ready. The app restarts to finish, so save anything you're working on first.`
      }
    >
      {state.kind === "failed" ? "Update failed, retry" : `Update to ${state.update.version}`}
    </button>
  );
}
