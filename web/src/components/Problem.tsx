// A problem said in place (Phase 25): what went wrong and what to do, in plain words; the
// server's own message stays behind "Detalii tehnice" for whoever needs it.
import type { ReactNode } from "react";

export function Problem({ children, detail }: { children: ReactNode; detail?: string | null }) {
  return (
    <div className="problem" role="alert">
      <p>{children}</p>
      {detail && (
        <details>
          <summary>Detalii tehnice</summary>
          <code>{detail}</code>
        </details>
      )}
    </div>
  );
}
