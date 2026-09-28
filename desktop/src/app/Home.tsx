import { useSession } from "../session/SessionContext";
import { PAGES, type AppPage } from "./pages";
import { HelpIcon } from "../shell/icons";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

interface HomeProps {
  reloadSignal: number;
  pageAvailable: (p: AppPage) => boolean;
  onGoTo: (p: AppPage) => void;
  onReportProblem: () => void;
}

export function Home({ pageAvailable, onGoTo, onReportProblem }: HomeProps) {
  const { session, signOut } = useSession();
  if (!session) return null;
  return (
    <div className="dg-page-enter">
      <h1 className="dg-greeting">
        {greeting()}, <span>{session.name.split(" ")[0]}</span>
      </h1>
      <div className="dg-appview__grid">
        {PAGES.filter((p) => p.key !== "home" && pageAvailable(p.key)).map((p, i) => (
          <button key={p.key} type="button" className="dg-tile" style={{ ["--i" as string]: i }} onClick={() => onGoTo(p.key)}>
            <span className="dg-tile__icon">{p.icon(20)}</span>
            <span className="dg-tile__body">
              <span className="dg-tile__title">{p.label}</span>
              <span className="dg-tile__subline">{p.subline}</span>
            </span>
            <span className="dg-tile__arrow" aria-hidden="true">→</span>
          </button>
        ))}
      </div>
      <footer className="dg-appview__footer">
        <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void signOut()}>Sign out</button>
        <button type="button" className="dg-btn dg-btn--ghost" onClick={onReportProblem}>
          <HelpIcon size={16} /> Something not working? Report it
        </button>
      </footer>
    </div>
  );
}
