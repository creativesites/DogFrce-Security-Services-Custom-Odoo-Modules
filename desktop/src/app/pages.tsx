import type { Feature } from "../api/capabilities";
import {
  BookIcon, ChartBarIcon, ClipboardListIcon, HomeIcon, InboxIcon, TrendingUpIcon, UsersIcon,
} from "../shell/icons";

/** The DeployGuard app's own pages, reachable from the left nav. */
export type AppPage = "home" | "work" | "training" | "team" | "inbox" | "adoption" | "owner";

export interface PageDef {
  key: AppPage;
  label: string;
  /** Short line for tiles and the command palette. */
  subline: string;
  icon: (size?: number) => JSX.Element;
  /** Server module the page needs. Pages whose module isn't installed are
   * hidden everywhere (nav, palette, onboarding) instead of erroring. */
  feature?: Feature;
}

/**
 * Ordered by what the employee does most. Home and Work first, the manager and
 * owner views after. Visibility of manager/owner pages is decided by the
 * server (capability probe + the page's own API answering "not allowed"),
 * never by matching names in React.
 */
export const PAGES: PageDef[] = [
  { key: "home", label: "Today", subline: "What you need to do now", icon: (s = 18) => <HomeIcon size={s} /> },
  { key: "work", label: "My Work", subline: "Tasks, checklists and sign-offs", icon: (s = 18) => <ClipboardListIcon size={s} />, feature: "work" },
  { key: "training", label: "My Training", subline: "Courses, lessons and assessments", icon: (s = 18) => <BookIcon size={s} />, feature: "training" },
  { key: "team", label: "Team Today", subline: "Who has done what, and where it's stuck", icon: (s = 18) => <UsersIcon size={s} />, feature: "team_today" },
  { key: "inbox", label: "Exceptions", subline: "Operational issues that need attention", icon: (s = 18) => <InboxIcon size={s} />, feature: "inbox" },
  { key: "adoption", label: "Adoption", subline: "Expected work vs. work done", icon: (s = 18) => <TrendingUpIcon size={s} />, feature: "adoption" },
  { key: "owner", label: "Owner Overview", subline: "Company-wide picture, with evidence", icon: (s = 18) => <ChartBarIcon size={s} />, feature: "owner" },
];

export function pageDef(key: AppPage): PageDef {
  return PAGES.find((p) => p.key === key) ?? PAGES[0];
}
