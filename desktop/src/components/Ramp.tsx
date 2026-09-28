/**
 * Progress on the shell's metric ramp (--dgs-ramp, the only gradient in the
 * design system). The gradient is laid across the *whole* scale, so a
 * low value shows red-orange and a full bar ends in green. It is not squeezed
 * into whatever width is filled.
 */
export function Ramp({ value, max, label }: { value: number; max: number; label?: string }) {
  const pct = max > 0 ? Math.min(100, Math.max(0, (100 * value) / max)) : 0;
  return (
    <span className="dg-ramp" role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
      <span
        className="dg-ramp__fill"
        style={{ width: `${pct}%`, backgroundSize: pct > 0 ? `${(100 * 100) / pct}% 100%` : undefined }}
      />
    </span>
  );
}
