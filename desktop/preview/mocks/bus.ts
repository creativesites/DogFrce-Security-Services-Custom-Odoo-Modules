type Listener = (e: { payload: unknown }) => void;
export const listeners = new Map<string, Set<Listener>>();
export function emit(name: string, payload: unknown) {
  for (const l of listeners.get(name) ?? []) l({ payload });
}
