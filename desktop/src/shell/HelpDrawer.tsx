import { useEffect, useState } from "react";
import { fetchContextualArticles, searchHelpArticles, type HelpArticle } from "../api/support";
import { extractErrorMessage } from "../lib/extractErrorMessage";

interface HelpDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentRoute?: string;
  workflowKey?: string;
  onOpenReportProblem: () => void;
}

export function HelpDrawer({
  isOpen,
  onClose,
  currentRoute = "/home",
  workflowKey,
  onOpenReportProblem,
}: HelpDrawerProps) {
  const [query, setQuery] = useState("");
  const [articles, setArticles] = useState<HelpArticle[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<HelpArticle | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setSelectedArticle(null);
      setQuery("");
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchContextualArticles(currentRoute, workflowKey, 5)
      .then((res) => {
        if (!cancelled) {
          setArticles(res || []);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(extractErrorMessage(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, currentRoute, workflowKey]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) {
      fetchContextualArticles(currentRoute, workflowKey, 5)
        .then((res) => setArticles(res || []))
        .catch(() => {});
      return;
    }

    setLoading(true);
    searchHelpArticles(query.trim())
      .then((res) => setArticles(res || []))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }

  if (!isOpen) return null;

  return (
    <div className="dg-modal-backdrop" role="dialog" aria-modal="true" aria-label="Knowledge Base & Help">
      <div
        className="dg-help-drawer"
        style={{
          position: "fixed",
          right: 0,
          top: 0,
          bottom: 0,
          width: 480,
          maxWidth: "100vw",
          background: "var(--ds-surface)",
          boxShadow: "-4px 0 24px rgba(0,0,0,0.15)",
          display: "flex",
          flexDirection: "column",
          zIndex: 1050,
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--ds-border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 600 }}>Help Centre & Knowledge</h2>
            <div style={{ fontSize: "0.8rem", color: "var(--ds-text-muted)" }}>
              Context for <strong>{currentRoute}</strong>
            </div>
          </div>
          <button
            type="button"
            className="dg-btn dg-btn--secondary"
            style={{ padding: "4px 8px" }}
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {/* Search bar */}
        <form onSubmit={handleSearch} style={{ padding: "12px 20px", borderBottom: "1px solid var(--ds-border)" }}>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="search"
              placeholder="Search help articles..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: 6,
                border: "1px solid var(--ds-border)",
                fontSize: "0.88rem",
              }}
            />
            <button type="submit" className="dg-btn dg-btn--secondary" style={{ padding: "6px 14px", fontSize: "0.85rem" }}>
              Search
            </button>
          </div>
        </form>

        {/* Content Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {selectedArticle ? (
            <div>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                style={{ marginBottom: 16, fontSize: "0.82rem", padding: "4px 8px" }}
                onClick={() => setSelectedArticle(null)}
              >
                ← Back to articles
              </button>
              <h3 style={{ margin: "0 0 8px 0", fontSize: "1.2rem", fontWeight: 600 }}>{selectedArticle.title}</h3>
              {selectedArticle.summary && (
                <p style={{ color: "var(--ds-text-muted)", fontStyle: "italic", marginBottom: 16 }}>
                  {selectedArticle.summary}
                </p>
              )}
              <div
                style={{ fontSize: "0.9rem", lineHeight: 1.6 }}
                dangerouslySetInnerHTML={{ __html: selectedArticle.body }}
              />
            </div>
          ) : (
            <div>
              {loading && <div style={{ padding: 20, textAlign: "center", color: "var(--ds-text-subtle)" }}>Loading articles...</div>}
              {error && (
                <div style={{ background: "var(--ds-danger-bg)", color: "var(--ds-danger)", padding: 10, borderRadius: 6, marginBottom: 12 }}>
                  {error}
                </div>
              )}
              {!loading && articles.length === 0 && (
                <div style={{ textAlign: "center", padding: "30px 10px", color: "var(--ds-text-subtle)" }}>
                  <p>No matching articles found.</p>
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {articles.map((art) => (
                  <div
                    key={art.id}
                    onClick={() => setSelectedArticle(art)}
                    style={{
                      padding: "12px 14px",
                      borderRadius: 8,
                      border: "1px solid var(--ds-border)",
                      background: "var(--ds-surface)",
                      cursor: "pointer",
                      transition: "border-color 0.15s ease",
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: "0.92rem", marginBottom: 4, color: "var(--ds-accent)" }}>
                      {art.title}
                    </div>
                    {art.summary && (
                      <div style={{ fontSize: "0.82rem", color: "var(--ds-text-muted)", lineHeight: 1.4 }}>
                        {art.summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Drawer Footer */}
        <div
          style={{
            padding: "14px 20px",
            borderTop: "1px solid var(--ds-border)",
            background: "var(--ds-bg)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "0.82rem", color: "var(--ds-text-muted)" }}>
            Didn't find what you need?
          </span>
          <button
            type="button"
            className="dg-btn dg-btn--primary"
            style={{ fontSize: "0.82rem", padding: "6px 12px" }}
            onClick={() => {
              onClose();
              onOpenReportProblem();
            }}
          >
            Report an Issue
          </button>
        </div>
      </div>
    </div>
  );
}
