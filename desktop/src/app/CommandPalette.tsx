import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

export interface Command {
  id: string;
  label: string;
  group: string;
  icon: ReactNode;
  run: () => void;
}

/** ⌘K / Ctrl+K quick actions. Only lists commands that actually work: no
 * advertised shortcuts that aren't bound. */
export function CommandPalette({ commands, onClose }: { commands: Command[]; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const id = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? commands.filter((c) => c.label.toLowerCase().includes(q) || c.group.toLowerCase().includes(q)) : commands;
  }, [commands, query]);

  useEffect(() => { setIndex(0); }, [query]);

  function run(c: Command) {
    onClose();
    // Let the palette unmount before any focus-stealing work runs.
    requestAnimationFrame(() => c.run());
  }

  return (
    <div className="dg-palette" role="dialog" aria-modal="true" aria-label="Quick actions">
      <div className="dg-palette__backdrop" onClick={onClose} />
      <div className="dg-palette__panel">
        <div className="dg-palette__inputwrap">
          <svg className="dg-palette__search" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
            <path d="M11.2 10.1a5 5 0 1 0-1.1 1.1l2.8 2.8.9-.9-2.6-3ZM7.5 11a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z" fill="currentColor" />
          </svg>
          <input
            ref={inputRef}
            className="dg-palette__input"
            placeholder="Type a command or search…"
            value={query}
            role="combobox"
            aria-expanded="true"
            aria-controls="dg-palette-list"
            aria-activedescendant={filtered[index] ? `dg-cmd-${filtered[index].id}` : undefined}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setIndex((i) => Math.min(i + 1, Math.max(filtered.length - 1, 0)));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setIndex((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                const c = filtered[index];
                if (c) run(c);
              } else if (e.key === "Escape") {
                e.preventDefault();
                e.stopPropagation();
                onClose();
              }
            }}
          />
          <kbd className="dg-palette__esc">Esc</kbd>
        </div>

        <div className="dg-palette__list" id="dg-palette-list" role="listbox">
          {filtered.length === 0 && <div className="dg-palette__empty">No matching commands</div>}
          {filtered.map((c, i) => (
            <button
              key={c.id}
              id={`dg-cmd-${c.id}`}
              type="button"
              role="option"
              aria-selected={i === index}
              className={`dg-palette__item${i === index ? " is-active" : ""}`}
              onMouseEnter={() => setIndex(i)}
              onClick={() => run(c)}
            >
              <span className="dg-palette__item-icon">{c.icon}</span>
              <span className="dg-palette__item-label">{c.label}</span>
              <span className="dg-palette__item-group">{c.group}</span>
            </button>
          ))}
        </div>

        <div className="dg-palette__footer">
          <span aria-live="polite">{filtered.length} {filtered.length === 1 ? "result" : "results"}</span>
          <span className="dg-palette__legend"><kbd>↑</kbd><kbd>↓</kbd> navigate <kbd>↵</kbd> run</span>
        </div>
      </div>
    </div>
  );
}
