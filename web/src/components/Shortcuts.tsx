// The keyboard shortcuts (Phase 25): one place that lists them (key ?), and the hook that tells
// whether a key press belongs to the page (not typed into a field, not inside an open dialog).
import { useEffect, useRef } from "react";
import { Modal } from "./Modal";

export const SHORTCUTS: [string[], string][] = [
  [["←", "→"], "Ziua precedentă sau următoare (Meciuri)"],
  [["T"], "Azi (Meciuri)"],
  [["1", "–", "5"], "Liga: Premier League, La Liga, Serie A, Bundesliga, Ligue 1"],
  [["M"], "Următorul model (Meciuri, Predicții)"],
  [["/"], "Caută o echipă"],
  [["S"], "Simulează un meci"],
  [["?"], "Scurtăturile"],
  [["Esc"], "Închide fereastra deschisă"],
];

/** A key press meant for the page: no modifier, not in a field, no modal dialog open. */
export function isPageKey(event: KeyboardEvent): boolean {
  if (event.metaKey || event.ctrlKey || event.altKey || event.defaultPrevented) return false;
  const target = event.target as HTMLElement | null;
  if (target && (target.isContentEditable || ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName))) return false;
  return !document.querySelector("dialog[open]");
}

/** Calls ``onKey`` with every page key while the component is shown; the latest callback wins.
 * A key the callback handles (it returns true) goes no further: "/" or "S" must not type
 * themselves into the dialog they open. */
export function usePageKeys(onKey: (key: string, event: KeyboardEvent) => boolean): void {
  const latest = useRef(onKey);
  latest.current = onKey;
  useEffect(() => {
    const listen = (event: KeyboardEvent) => {
      if (isPageKey(event) && latest.current(event.key, event)) event.preventDefault();
    };
    document.addEventListener("keydown", listen);
    return () => document.removeEventListener("keydown", listen);
  }, []);
}

export function ShortcutsDialog({ onClose }: { onClose: () => void }) {
  return (
    <Modal label="Scurtăturile tastaturii" onClose={onClose}>
      <div className="dialog card">
        <div className="dialog-head">
          <h2>Scurtăturile tastaturii</h2>
        </div>
        <dl className="shortcuts">
          {SHORTCUTS.map(([keys, text]) => (
            <div key={text}>
              <dt>
                {keys.map((key) => (key === "–" ? <span key={key}>–</span> : <kbd key={key}>{key}</kbd>))}
              </dt>
              <dd>{text}</dd>
            </div>
          ))}
        </dl>
        <div className="dialog-actions">
          <button type="button" className="button primary" onClick={onClose} autoFocus>
            Am înțeles
          </button>
        </div>
      </div>
    </Modal>
  );
}
