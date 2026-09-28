import { useEffect, useState } from "react";
import { Modal } from "./Modal";
import { EmptyState, ErrorState, Spinner } from "./States";
import { parseOdooDatetime } from "../shell/pages/myWork.logic";

export type EvidenceRow = { id: number; [key: string]: unknown };
type Row = EvidenceRow;

const LABELS: Record<string, string> = {
  name: "Record", display_name: "Record", employee_id: "Who", user_id: "Who", site_id: "Site",
  due_at: "Due", state: "Status", cnc_reason: "Reason", cnc_note: "Details", title: "Issue",
  tier: "Tier", first_seen_at: "Since", course_id: "Course", due_date: "Due", subject: "Summary",
  priority: "Priority", create_date: "Reported",
};

/** Render one Odoo value as text: many2one -> its name, datetimes -> local. */
export function formatCell(value: unknown): string {
  if (value === false || value === null || value === undefined) return "—";
  if (Array.isArray(value) && value.length === 2 && typeof value[1] === "string") return value[1];
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) {
    const d = parseOdooDatetime(value);
    return d ? d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : value;
  }
  return String(value);
}

/**
 * "Show me the records behind this number." Every figure on Team Today and
 * the Owner Overview opens here, and each row can be opened in the ERP.
 */
export function EvidenceModal<R extends { id: number }>({ title, fields, load, onOpenRecord, onClose }: {
  title: string;
  fields: string[];
  load: () => Promise<R[]>;
  onOpenRecord?: (row: R) => void;
  onClose: () => void;
}) {
  const [rows, setRows] = useState<R[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    load().then((r) => { if (!cancelled) setRows(r); }).catch((e) => { if (!cancelled) setError(e); });
    return () => { cancelled = true; };
  }, [load]);

  const columns = fields.filter((f) => f !== "id");

  return (
    <Modal title={title} subtitle={rows ? `${rows.length} record${rows.length === 1 ? "" : "s"}` : undefined} size="lg" onClose={onClose}>
      {!!error && <ErrorState error={error} fallback="These records couldn't be loaded." />}
      {!error && rows === null && <Spinner label="Loading records…" />}
      {rows && rows.length === 0 && <EmptyState title="No records" />}
      {rows && rows.length > 0 && (
        <table className="dg-table">
          <thead>
            <tr>
              {columns.map((c) => <th key={c} scope="col">{LABELS[c] ?? c}</th>)}
              {onOpenRecord && <th scope="col"><span className="dg-sr-only">Open</span></th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                {columns.map((c) => <td key={c}>{formatCell((row as unknown as Row)[c])}</td>)}
                {onOpenRecord && (
                  <td><button type="button" className="dg-btn dg-btn--sm" onClick={() => onOpenRecord(row)}>Open</button></td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Modal>
  );
}
