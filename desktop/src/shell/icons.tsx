/** Inline stroke SVG icons, ~1.9px stroke weight — design system §2 rule 7. */

interface IconProps {
  size?: number;
}

function common(size = 20) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 1.9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
}

export function HomeIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" />
    </svg>
  );
}

export function ClipboardListIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <rect x="6" y="4" width="12" height="16" rx="2" />
      <path d="M9 4V3.5A1.5 1.5 0 0 1 10.5 2h3A1.5 1.5 0 0 1 15 3.5V4" />
      <path d="M9 10h.01" />
      <path d="M12 10h3" />
      <path d="M9 14h.01" />
      <path d="M12 14h3" />
    </svg>
  );
}

export function BookIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H12v16.5H6.5A2.5 2.5 0 0 0 4 22z" />
      <path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H12v16.5h5.5a2.5 2.5 0 0 1 2.5 2.5z" />
    </svg>
  );
}

export function CheckCircleIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12.3 2.4 2.4 4.6-5.4" />
    </svg>
  );
}

export function AlertTriangleIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M12 4 3 19h18L12 4Z" />
      <path d="M12 10v4" />
      <path d="M12 17h.01" />
    </svg>
  );
}

export function OdooIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18" />
      <path d="M8 4v5" />
      <path d="M16 4v5" />
    </svg>
  );
}

export function HelpIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.3a2.5 2.5 0 0 1 4.9.7c0 1.6-2.4 2-2.4 3.5" />
      <path d="M12 17h.01" />
    </svg>
  );
}

export function BackIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M15 5 8 12l7 7" />
    </svg>
  );
}

export function ForwardIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M9 5l7 7-7 7" />
    </svg>
  );
}

export function ReloadIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M20 11a8 8 0 1 0-2.3 5.7" />
      <path d="M20 5v6h-6" />
    </svg>
  );
}

export function ChevronDownIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

/** Window controls (decorations are off — see windowing.rs — so the
 * toolbar draws its own, VS Code–style). Intentionally plain strokes,
 * not the OS-native glyphs, matching the rest of the icon set. */
export function WindowMinimizeIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M5 12h14" />
    </svg>
  );
}

export function WindowMaximizeIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <rect x="5" y="5" width="14" height="14" rx="1.5" />
    </svg>
  );
}

export function WindowRestoreIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <rect x="7" y="7" width="12" height="12" rx="1.5" />
      <path d="M17 7V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v9.5A1.5 1.5 0 0 0 6 17h1" />
    </svg>
  );
}

export function WindowCloseIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export function ChartBarIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M3 20h18" />
      <path d="M6 16v4" />
      <path d="M10 10v10" />
      <path d="M14 6v14" />
      <path d="M18 12v8" />
    </svg>
  );
}

export function LifeBuoyIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M4.93 4.93l2.83 2.83" />
      <path d="M16.24 16.24l2.83 2.83" />
      <path d="M4.93 19.07l2.83-2.83" />
      <path d="M16.24 7.76l2.83-2.83" />
    </svg>
  );
}

export function SparklesIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M12 3v3m0 12v3M3 12h3m12 0h3M6.34 6.34l2.12 2.12m7.08 7.08 2.12 2.12M6.34 17.66l2.12-2.12m7.08-7.08 2.12-2.12" />
    </svg>
  );
}

export function TrendingUpIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </svg>
  );
}

export function ShieldCheckIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

export function InboxIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
    </svg>
  );
}

export function AlertOctagonIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

export function CheckCheckIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="m18 6-9.5 9.5-4-4" />
      <path d="m22 10-9.5 9.5-2-2" />
    </svg>
  );
}

export function ClockIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

export function ExternalLinkIcon({ size }: IconProps = {}) {
  return (
    <svg {...common(size)} aria-hidden="true">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}


