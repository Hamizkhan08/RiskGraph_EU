"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { DatasetKey } from "./types";

export type AsyncState<T> = { status: "loading" } | { status: "error"; error: Error } | { status: "success"; data: T };

/** Runs `fn` whenever `key` changes. State is derived so no state is set synchronously in the effect. */
export function useAsync<T>(fn: () => Promise<T>, key: string): AsyncState<T> & { reload: () => void } {
  const [nonce, setNonce] = useState(0);
  const [res, setRes] = useState<{ key: string; base: string; state: AsyncState<T> } | null>(null);
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });
  const fullKey = `${key}#${nonce}`;
  useEffect(() => {
    let alive = true;
    fnRef.current().then(
      (data) => alive && setRes({ key: fullKey, base: key, state: { status: "success", data } }),
      (error: unknown) =>
        alive && setRes({ key: fullKey, base: key, state: { status: "error", error: error instanceof Error ? error : new Error(String(error)) } }),
    );
    return () => {
      alive = false;
    };
  }, [fullKey, key]);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  // Same query, refreshed (reload): keep showing the previous data instead of flashing a skeleton.
  let state: AsyncState<T> = { status: "loading" };
  if (res && res.key === fullKey) state = res.state;
  else if (res && res.base === key && res.state.status === "success") state = res.state;
  return { ...state, reload };
}

const DatasetCtx = createContext<{ dataset: DatasetKey; setDataset: (d: DatasetKey) => void }>({ dataset: "LI", setDataset: () => {} });

export function DatasetProvider({ children, initial = "LI" }: { children: ReactNode; initial?: DatasetKey }) {
  const [dataset, setDs] = useState<DatasetKey>(initial);
  useEffect(() => {
    const s = window.localStorage.getItem("rg:dataset");
    if (s === "LI" || s === "HI") queueMicrotask(() => setDs(s));
  }, []);
  const setDataset = useCallback((d: DatasetKey) => {
    setDs(d);
    window.localStorage.setItem("rg:dataset", d);
  }, []);
  return <DatasetCtx.Provider value={{ dataset, setDataset }}>{children}</DatasetCtx.Provider>;
}
export const useDataset = () => useContext(DatasetCtx);
