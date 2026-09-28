import { useCallback, useState } from "react";
import { startGuidance } from "../api/guidance";
import { useViewMode } from "./viewMode";

/**
 * "Guide me" / "Practice it now": starts a guidance session on the server,
 * then loads the ERP screen with the guide panel beside it. The full page
 * load is what wakes the ERP-side runner. Nothing is injected into Odoo.
 */
export function useStartGuidance() {
  const { openGuide } = useViewMode();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const start = useCallback(async (flowCode: string, opts: { taskId?: number; path?: string | false } = {}) => {
    setStarting(true);
    setError(null);
    try {
      await startGuidance(flowCode, opts.taskId);
      await openGuide(opts.path || "/odoo");
    } catch (err) {
      setError(err);
    } finally {
      setStarting(false);
    }
  }, [openGuide]);

  return { start, starting, error };
}
