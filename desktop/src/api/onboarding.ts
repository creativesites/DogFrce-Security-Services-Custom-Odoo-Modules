import { callKw } from "./odoo";
import { isModuleNotInstalled } from "./capabilities";
import { extractErrorMessage } from "../lib/extractErrorMessage";

/** security_deployguard_bridge's record of who was shown the monitoring notice. */
export const NOTICE_MODEL = "security.deployguard.policy.acknowledgement";

export interface MonitoringNotice {
  version: string;
  title: string;
  body: string[];
  acknowledged: boolean;
  acknowledged_at: string | false;
}

export type NoticeStatus =
  | { kind: "loading" }
  | { kind: "needs_ack"; notice: MonitoringNotice }
  | { kind: "acknowledged"; notice: MonitoringNotice }
  /** The bridge module isn't installed on this server, so there's nowhere to record it. */
  | { kind: "unavailable" }
  | { kind: "error"; message: string };

/** "The server hasn't got the bridge module", as opposed to a network blip or an expired session. */
export function isNoticeModelMissing(err: unknown): boolean {
  return isModuleNotInstalled(err, NOTICE_MODEL);
}

export function noticeStatusFrom(notice: MonitoringNotice): NoticeStatus {
  return notice.acknowledged ? { kind: "acknowledged", notice } : { kind: "needs_ack", notice };
}

export function noticeStatusFromError(err: unknown): NoticeStatus {
  if (isNoticeModelMissing(err)) return { kind: "unavailable" };
  return { kind: "error", message: extractErrorMessage(err, "Couldn't load the monitoring notice.") };
}

/** Adoption figures are only shown to someone who has been told they're collected. */
export function adoptionAllowed(status: NoticeStatus): boolean {
  return status.kind === "acknowledged";
}

/**
 * Whether to put the first-run flow in front of everything else. Someone
 * who hasn't acknowledged the notice always sees it; on a server without the
 * bridge there's nothing to acknowledge, so they get the welcome once per
 * device. A load error shows nothing -- it's retried on the next launch
 * rather than trapping the person in front of a spinner.
 */
export function shouldShowOnboarding(status: NoticeStatus, welcomeSeen: boolean): boolean {
  if (status.kind === "needs_ack") return true;
  if (status.kind === "unavailable") return !welcomeSeen;
  return false;
}

export async function fetchNotice(): Promise<MonitoringNotice> {
  return callKw<MonitoringNotice>(NOTICE_MODEL, "get_notice");
}

export async function acknowledgeNotice(version: string, client: string): Promise<MonitoringNotice> {
  return callKw<MonitoringNotice>(NOTICE_MODEL, "acknowledge", [version], { client });
}

function welcomeKey(db: string, uid: number): string {
  return `dg.welcome.seen.${db}.${uid}`;
}

export function hasSeenWelcome(db: string, uid: number): boolean {
  try {
    return window.localStorage.getItem(welcomeKey(db, uid)) === "1";
  } catch {
    return false;
  }
}

export function markWelcomeSeen(db: string, uid: number): void {
  try {
    window.localStorage.setItem(welcomeKey(db, uid), "1");
  } catch {
    // Storage unavailable: the welcome shows again next launch, which is harmless.
  }
}
