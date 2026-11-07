// A problem said in place (Phase 25): what went wrong and what to do, in plain words; the
// server's own message stays behind "Detalii tehnice" for whoever needs it.
import type { ReactNode } from "react";

export function Problem({ children, detail, onRetry }: { children: ReactNode; detail?: string | null; onRetry?: () => void }) {
  return (
    <div className="problem" role="alert">
      <p>{children}</p>
      {onRetry && (
        <button className="button" onClick={onRetry}>
          Încearcă din nou
        </button>
      )}
      {detail && (
        <details>
          <summary>Detalii tehnice</summary>
          <code>{detail}</code>
        </details>
      )}
    </div>
  );
}
