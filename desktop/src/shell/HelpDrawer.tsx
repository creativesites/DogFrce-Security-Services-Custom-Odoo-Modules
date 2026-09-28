import { useEffect, useState } from "react";
import { fetchArticleBody, fetchContextualArticles, searchHelpArticles, type HelpArticle } from "../api/support";
import { Modal } from "../components/Modal";
import { SafeHtml } from "../components/SafeHtml";
import { EmptyState, ErrorState, Spinner } from "../components/States";

interface HelpDrawerProps {
  onClose: () => void;
  currentRoute?: string;
  workflowKey?: string;
  onOpenReportProblem: () => void;
}

/** Contextual help for the screen the employee is on (security_help articles). */
export function HelpDrawer({ onClose, currentRoute = "/home", workflowKey, onOpenReportProblem }: HelpDrawerProps) {
  const [query, setQuery] = useState("");
  const [articles, setArticles] = useState<HelpArticle[]>([]);
  const [selected, setSelected] = useState<HelpArticle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    fetchContextualArticles(currentRoute, workflowKey, 5)
      .then((res) => { if (!cancelled) setArticles(res || []); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [currentRoute, workflowKey]);

  function openArticle(art: HelpArticle) {
    setSelected(art);
    if (art.body) return;
    fetchArticleBody(art.id)
      .then((body) => setSelected((cur) => (cur?.id === art.id ? { ...cur, body } : cur)))
      .catch(setError);
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const request = query.trim()
      ? searchHelpArticles(query.trim())
      : fetchContextualArticles(currentRoute, workflowKey, 5);
    request
      .then((res) => setArticles(res || []))
      .catch(setError)
      .finally(() => setLoading(false));
  }

  return (
    <Modal
      variant="drawer"
      title="Help"
      subtitle="Answers for the screen you're on"
      onClose={onClose}
      footer={
        <>
          <span className="dg-field__hint">Didn't find what you need?</span>
          <button type="button" className="dg-btn dg-btn--primary" onClick={() => { onClose(); onOpenReportProblem(); }}>
            Report a problem
          </button>
        </>
      }
    >
      {selected ? (
        <article>
          <button type="button" className="dg-btn dg-btn--sm" onClick={() => setSelected(null)}>← All articles</button>
          <h3>{selected.title}</h3>
          {selected.summary && <p className="dg-field__hint">{selected.summary}</p>}
          {selected.body ? <SafeHtml className="dg-prose" html={selected.body} /> : <Spinner label="Loading article…" />}
        </article>
      ) : (
        <>
          <form className="dg-searchrow" onSubmit={handleSearch} role="search">
            <label className="dg-sr-only" htmlFor="dg-help-search">Search help</label>
            <input
              id="dg-help-search"
              className="dg-input"
              type="search"
              placeholder="Search help…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" className="dg-btn">Search</button>
          </form>
          {loading && <Spinner label="Loading articles…" />}
          {!!error && <ErrorState error={error} fallback="Help articles couldn't be loaded." />}
          {!loading && !error && articles.length === 0 && (
            <EmptyState title="No matching articles">Try different words, or report the problem and someone will help.</EmptyState>
          )}
          <div className="dg-articles">
            {articles.map((art) => (
              <button key={art.id} type="button" className="dg-article" onClick={() => openArticle(art)}>
                <div className="dg-article__title">{art.title}</div>
                {art.summary && <div className="dg-article__summary">{art.summary}</div>}
              </button>
            ))}
          </div>
        </>
      )}
    </Modal>
  );
}
