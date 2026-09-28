import { listeners } from "./bus";
export async function listen(name: string, cb: (e: { payload: unknown }) => void) {
  if (!listeners.has(name)) listeners.set(name, new Set());
  listeners.get(name)!.add(cb);
  return () => listeners.get(name)?.delete(cb);
}
