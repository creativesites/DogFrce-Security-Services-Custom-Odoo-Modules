/** Inline stroke SVG icons, ~1.9px stroke weight — design system §2 rule 7. */

const common = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function HomeIcon() {
  return (
    <svg {...common} aria-hidden="true">
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" />
    </svg>
  );
}

export function OdooIcon() {
  return (
    <svg {...common} aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18" />
      <path d="M8 4v5" />
      <path d="M16 4v5" />
    </svg>
  );
}

export function HelpIcon() {
  return (
    <svg {...common} aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.3a2.5 2.5 0 0 1 4.9.7c0 1.6-2.4 2-2.4 3.5" />
      <path d="M12 17h.01" />
    </svg>
  );
}
