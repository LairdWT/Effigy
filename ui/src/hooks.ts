import { useEffect, useRef, useState } from "react";

// editors with unsaved work (UX review 2026-10-12, UX-01): a Close, a version switch, a link or a reload asks first
const dirty = new Set<string>();
export const unsaved = () => dirty.size > 0;
/** true when there is nothing to lose, or the user agrees to lose it */
export const leave = () => !unsaved() || window.confirm("Discard the unsaved changes?");
export function useUnsaved(id: string, on: boolean) {
  useEffect(() => {
    if (!on) return;
    dirty.add(id);
    const ask = (e: BeforeUnloadEvent) => (e.preventDefault(), (e.returnValue = ""));
    window.addEventListener("beforeunload", ask);
    return () => {
      dirty.delete(id);
      window.removeEventListener("beforeunload", ask);
    };
  }, [id, on]);
}

/** [busy, run]: run(f) ignores calls while an earlier f is still going (one submission per click burst). */
export function useBusy(): [boolean, (f: () => Promise<unknown>) => Promise<void>] {
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const run = async (f: () => Promise<unknown>) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    try {
      await f();
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return [busy, run];
}

type Hist<T> = { past: T[]; now: T; future: T[] };
// snapshots per finished gesture (capped at 200), for the skeleton and the marker editor; null: not editing
export function useHistory<T>() {
  const [h, set] = useState<Hist<T> | null>(null);
  return {
    h,
    start: (now: T) => set({ past: [], now, future: [] }),
    stop: () => set(null),
    commit: (f: (s: T) => T) => set((h) => h && { past: [...h.past, h.now].slice(-200), now: f(h.now), future: [] }),
    undo: () => set((h) => (h?.past.length ? { past: h.past.slice(0, -1), now: h.past.at(-1)!, future: [h.now, ...h.future] } : h)),
    redo: () => set((h) => (h?.future.length ? { past: [...h.past, h.now], now: h.future[0], future: h.future.slice(1) } : h)),
  };
}
