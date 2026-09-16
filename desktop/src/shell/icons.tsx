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
